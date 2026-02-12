"""State checkpointing for curriculum replay.

Serialize and restore mid-episode AAT state so dojo can replay
episodes from saved checkpoints during curriculum training.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sprint_manager import SprintManager

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Serializable snapshot of mid-episode state."""

    episode_id: str
    sprint_num: int
    phase: str
    timestamp: str
    kanban_snapshot: Dict[str, Any] = field(default_factory=dict)
    agent_states: List[Dict[str, Any]] = field(default_factory=list)
    sprint_results: List[Dict[str, Any]] = field(default_factory=list)
    meta_learnings: List[Dict[str, Any]] = field(default_factory=list)
    tracer_states: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    backlog_state: Dict[str, Any] = field(default_factory=dict)
    config_hash: str = ""


class CheckpointManager:
    """Manage save/restore of mid-episode checkpoints.

    Storage format: ``{checkpoint_dir}/{episode_id}/s{sprint:02d}-{phase}.json``

    Usage::

        mgr = CheckpointManager(Path("/tmp/checkpoints"))
        path = await mgr.save("ep-001", sprint_manager, sprint_num=1, phase="dev")
        checkpoint = await mgr.restore(path, sprint_manager)
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        self._dir = checkpoint_dir or Path("/tmp/aat-checkpoints")

    @property
    def checkpoint_dir(self) -> Path:
        """Root directory for checkpoint storage."""
        return self._dir

    async def save(
        self,
        episode_id: str,
        sprint_manager: "SprintManager",
        sprint_num: int,
        phase: str,
    ) -> Path:
        """Save a checkpoint of the current SprintManager state.

        Args:
            episode_id: Unique episode identifier.
            sprint_manager: The SprintManager to snapshot.
            sprint_num: Current sprint number.
            phase: Current phase name.

        Returns:
            Path to the written checkpoint file.
        """
        sm = sprint_manager

        # Kanban snapshot
        kanban_snapshot = await sm.kanban.get_snapshot()

        # Agent states
        agent_states: List[Dict[str, Any]] = []
        for agent in sm.agents:
            state: Dict[str, Any] = {
                "agent_id": agent.agent_id,
                "role_id": agent.config.role_id,
                "name": agent.config.name,
                "seniority": getattr(agent.config, "seniority", "mid"),
                "conversation_history": list(agent.conversation_history),
                "is_swapped": agent.is_swapped,
            }
            # Capture swap state if present
            if agent.is_swapped and hasattr(agent, "_swap_state"):
                swap = agent._swap_state
                if swap:
                    state["swap_state"] = {
                        "target_role_id": swap.get("target_role_id", ""),
                        "proficiency": swap.get("proficiency", 1.0),
                        "sprint": swap.get("sprint", 0),
                    }
            agent_states.append(state)

        # Sprint results
        sprint_results = list(sm._sprint_results)

        # Meta-learnings (from DB if mock)
        meta_learnings: List[Dict[str, Any]] = []
        if hasattr(sm.db, "_meta_learnings"):
            meta_learnings = list(sm.db._meta_learnings)

        # Tracer states
        tracer_states: Dict[str, List[Dict[str, Any]]] = {}
        for agent in sm.agents:
            if agent._tracer is not None:
                tracer_states[agent.agent_id] = [
                    {
                        "decision_id": d.decision_id,
                        "timestamp": d.timestamp,
                        "phase": d.phase,
                        "context": d.context,
                        "action_type": d.action_type,
                        "action_content": d.action_content,
                        "reasoning_trace": d.reasoning_trace,
                        "outcome": d.outcome,
                        "metadata": d.metadata,
                    }
                    for d in agent._tracer.decisions
                ]

        # Backlog state
        backlog_state: Dict[str, Any] = {}
        if sm.backlog is not None:
            backlog_state = {
                "remaining": sm.backlog.remaining,
                "selected": list(sm.backlog._selected_ids),
            }

        # Config hash for compatibility check
        config_hash = self._hash_config(sm.config)

        checkpoint = Checkpoint(
            episode_id=episode_id,
            sprint_num=sprint_num,
            phase=phase,
            timestamp=datetime.now(timezone.utc).isoformat(),
            kanban_snapshot=kanban_snapshot,
            agent_states=agent_states,
            sprint_results=sprint_results,
            meta_learnings=meta_learnings,
            tracer_states=tracer_states,
            backlog_state=backlog_state,
            config_hash=config_hash,
        )

        # Write to disk
        ep_dir = self._dir / episode_id
        ep_dir.mkdir(parents=True, exist_ok=True)
        filename = f"s{sprint_num:02d}-{phase}.json"
        path = ep_dir / filename
        path.write_text(json.dumps(asdict(checkpoint), indent=2, default=str))

        return path

    async def restore(
        self,
        checkpoint_path: Path,
        sprint_manager: "SprintManager",
    ) -> Checkpoint:
        """Restore SprintManager state from a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint JSON file.
            sprint_manager: The SprintManager to restore into.

        Returns:
            The loaded Checkpoint dataclass.

        Raises:
            FileNotFoundError: If checkpoint file doesn't exist.
        """
        data = json.loads(checkpoint_path.read_text())
        checkpoint = Checkpoint(
            **{k: v for k, v in data.items() if k in Checkpoint.__dataclass_fields__}
        )

        sm = sprint_manager

        # Warn on config hash mismatch
        current_hash = self._hash_config(sm.config)
        if checkpoint.config_hash and checkpoint.config_hash != current_hash:
            logger.warning(
                "Config hash mismatch: checkpoint=%s current=%s. "
                "State may not restore correctly.",
                checkpoint.config_hash,
                current_hash,
            )

        # Restore kanban cards (mock mode)
        if hasattr(sm.db, "_cards"):
            sm.db._cards.clear()
            for status, cards in checkpoint.kanban_snapshot.items():
                for card in cards:
                    sm.db._cards.append(card)

        # Restore agent conversation history and swap state
        agent_map = {a.agent_id: a for a in sm.agents}
        for state in checkpoint.agent_states:
            agent = agent_map.get(state["agent_id"])
            if agent is None:
                continue
            agent.conversation_history = list(state.get("conversation_history", []))
            swap_state = state.get("swap_state")
            if swap_state:
                agent._swap_state = swap_state

        # Restore sprint results
        sm._sprint_results = list(checkpoint.sprint_results)

        # Restore meta-learnings (mock mode)
        if hasattr(sm.db, "_meta_learnings"):
            sm.db._meta_learnings = list(checkpoint.meta_learnings)

        # Restore tracer decisions
        for agent in sm.agents:
            if agent._tracer is not None and agent.agent_id in checkpoint.tracer_states:
                from ..agents.decision_tracer import Decision

                agent._tracer._decisions.clear()
                for d_data in checkpoint.tracer_states[agent.agent_id]:
                    decision = Decision(
                        decision_id=d_data["decision_id"],
                        timestamp=d_data["timestamp"],
                        phase=d_data["phase"],
                        context=d_data["context"],
                        action_type=d_data["action_type"],
                        action_content=d_data["action_content"],
                        reasoning_trace=d_data["reasoning_trace"],
                        outcome=d_data.get("outcome"),
                        metadata=d_data.get("metadata", {}),
                    )
                    agent._tracer.record(decision)

        # Restore backlog selected set
        if sm.backlog is not None and checkpoint.backlog_state:
            selected = checkpoint.backlog_state.get("selected", [])
            sm.backlog._selected_ids = set(selected)

        return checkpoint

    def list_checkpoints(self, episode_id: str) -> List[Path]:
        """List all checkpoint files for an episode, sorted by name.

        Args:
            episode_id: Episode identifier.

        Returns:
            Sorted list of checkpoint file paths.
        """
        ep_dir = self._dir / episode_id
        if not ep_dir.exists():
            return []
        return sorted(ep_dir.glob("s*-*.json"))

    @staticmethod
    def _hash_config(config: Any) -> str:
        """Compute a short hash of the config for compatibility checking."""
        try:
            config_str = json.dumps(config.__dict__, sort_keys=True, default=str)
        except (TypeError, AttributeError):
            config_str = str(config)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
