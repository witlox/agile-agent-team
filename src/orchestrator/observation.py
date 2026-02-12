"""Structured observation extraction for RL environment integration.

Extracts structured observations from AAT state so dojo's Gym wrapper
can consume them as the observation space.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sprint_manager import SprintManager


@dataclass
class AgentObservation:
    """Observable state of a single agent."""

    agent_id: str
    role_id: str
    seniority: str
    specializations: List[str]
    is_swapped: bool
    is_onboarding: bool
    recent_decisions: List[Dict[str, Any]] = field(default_factory=list)
    conversation_length: int = 0


@dataclass
class Observation:
    """Complete observation of AAT state for RL."""

    sprint_num: int
    phase: str
    kanban: Dict[str, Any] = field(default_factory=dict)
    agents: List[AgentObservation] = field(default_factory=list)
    sprint_metrics: Optional[Dict[str, Any]] = None
    disturbances_active: List[str] = field(default_factory=list)
    meta_learnings_count: int = 0
    departure_events: List[Dict[str, Any]] = field(default_factory=list)
    backfill_events: List[Dict[str, Any]] = field(default_factory=list)
    team_composition: Dict[str, int] = field(default_factory=dict)


class ObservationExtractor:
    """Extracts structured observations from SprintManager state.

    Usage::

        extractor = ObservationExtractor(sprint_manager)
        obs = await extractor.extract(sprint_num=3, phase="development")
        obs_dict = extractor.to_dict(obs)
    """

    def __init__(self, sprint_manager: "SprintManager") -> None:
        self._sm = sprint_manager

    async def extract(
        self,
        sprint_num: int,
        phase: str = "unknown",
        max_recent_decisions: int = 10,
    ) -> Observation:
        """Extract a full observation from current SprintManager state.

        Args:
            sprint_num: Current sprint number.
            phase: Current phase name.
            max_recent_decisions: Max recent decisions per agent to include.

        Returns:
            Observation dataclass with all observable state.
        """
        # Kanban snapshot
        kanban = await self._sm.kanban.get_snapshot()

        # Agent observations
        agents: List[AgentObservation] = []
        for agent in self._sm.agents:
            # Recent decisions from tracer
            recent_decisions: List[Dict[str, Any]] = []
            if agent._tracer is not None:
                for d in agent._tracer.decisions[-max_recent_decisions:]:
                    recent_decisions.append(
                        {
                            "decision_id": d.decision_id,
                            "phase": d.phase,
                            "action_type": d.action_type,
                            "timestamp": d.timestamp,
                        }
                    )

            # Onboarding status
            is_onboarding = False
            if hasattr(self._sm, "_onboarding_manager"):
                is_onboarding = self._sm._onboarding_manager.is_onboarding(
                    agent.agent_id
                )

            agents.append(
                AgentObservation(
                    agent_id=agent.agent_id,
                    role_id=agent.config.role_id,
                    seniority=getattr(agent.config, "seniority", "mid"),
                    specializations=list(getattr(agent.config, "specializations", [])),
                    is_swapped=agent.is_swapped,
                    is_onboarding=is_onboarding,
                    recent_decisions=recent_decisions,
                    conversation_length=len(agent.conversation_history),
                )
            )

        # Sprint metrics from results
        sprint_metrics: Optional[Dict[str, Any]] = None
        for r in self._sm._sprint_results:
            if r.get("sprint") == sprint_num:
                sprint_metrics = r
                break

        # Active disturbances
        disturbances_active: List[str] = []
        if self._sm.disturbance_engine is not None:
            disturbances_active = list(
                getattr(self._sm.disturbance_engine, "_last_fired", [])
            )

        # Meta-learnings count
        meta_learnings_count = 0
        try:
            from pathlib import Path

            jsonl_path = (
                Path(self._sm.config.team_config_dir)
                / "07_meta"
                / "meta_learnings.jsonl"
            )
            if jsonl_path.exists():
                with open(jsonl_path) as f:
                    meta_learnings_count = sum(1 for _ in f)
        except Exception:
            pass

        # Departure / backfill events from sprint results
        departure_events: List[Dict[str, Any]] = []
        backfill_events: List[Dict[str, Any]] = []
        if sprint_metrics:
            for dep_id in sprint_metrics.get("departure_events", []):
                departure_events.append({"agent_id": dep_id, "sprint": sprint_num})
            for bf_id in sprint_metrics.get("backfill_events", []):
                backfill_events.append({"agent_id": bf_id, "sprint": sprint_num})

        # Team composition
        team_composition: Dict[str, int] = {}
        for agent in self._sm.agents:
            seniority = getattr(agent.config, "seniority", "mid")
            team_composition[seniority] = team_composition.get(seniority, 0) + 1
        for agent in self._sm.agents:
            role = getattr(agent.config, "role_archetype", "unknown")
            key = f"role_{role}"
            team_composition[key] = team_composition.get(key, 0) + 1

        return Observation(
            sprint_num=sprint_num,
            phase=phase,
            kanban=kanban,
            agents=agents,
            sprint_metrics=sprint_metrics,
            disturbances_active=disturbances_active,
            meta_learnings_count=meta_learnings_count,
            departure_events=departure_events,
            backfill_events=backfill_events,
            team_composition=team_composition,
        )

    def to_dict(self, obs: Observation) -> Dict[str, Any]:
        """Serialize Observation to plain dict (JSON-safe)."""
        return asdict(obs)
