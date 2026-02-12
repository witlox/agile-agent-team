"""Agent attrition engine — mid-experiment agent removal with knowledge gap tracking.

Supports configurable departure probability, role protection, backfill delay,
and replacement agent creation following the hiring protocol.
"""

import json
import random as _random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.agent_factory import AgentFactory
    from ..agents.base_agent import BaseAgent


@dataclass
class DepartureEvent:
    """Record of an agent leaving the team."""

    sprint: int
    agent_id: str
    agent_name: str
    seniority: str
    specializations_lost: List[str]
    stories_contributed: List[str]
    meta_learnings_count: int
    backfill_sprint: Optional[int] = None


@dataclass
class AttritionConfig:
    """Configuration for the attrition engine."""

    enabled: bool = False
    starts_after_sprint: int = 10
    probability_per_sprint: float = 0.05
    backfill_enabled: bool = True
    backfill_delay_sprints: int = 1
    protect_roles: List[str] = field(
        default_factory=lambda: ["dev_lead", "qa_lead", "po"]
    )
    max_departures_per_sprint: int = 1


class AttritionEngine:
    """Manages agent departures and backfill following hiring_protocol.md."""

    def __init__(
        self,
        config: AttritionConfig,
        rng: Optional[_random.Random] = None,
    ) -> None:
        self._config = config
        self._rng = rng or _random.Random()
        self._departure_history: List[DepartureEvent] = []

    @property
    def config(self) -> AttritionConfig:
        return self._config

    @property
    def departure_history(self) -> List[DepartureEvent]:
        return list(self._departure_history)

    def _is_protected(self, agent: "BaseAgent") -> bool:
        """Return True if the agent's role is in the protect list."""
        role_id = agent.config.role_id
        for protected in self._config.protect_roles:
            if protected in role_id:
                return True
        return False

    def _count_meta_learnings(self, agent: "BaseAgent") -> int:
        """Count meta-learnings this agent has contributed."""
        team_config_dir = Path("team_config")
        jsonl_path = team_config_dir / "07_meta" / "meta_learnings.jsonl"
        if not jsonl_path.exists():
            return 0
        count = 0
        try:
            with open(jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("agent_id") == agent.config.role_id:
                            count += 1
                    except json.JSONDecodeError:
                        continue
        except IOError:
            return 0
        return count

    def _get_contributed_stories(self, agent: "BaseAgent") -> List[str]:
        """Get story IDs this agent has driven (from conversation history)."""
        stories: List[str] = []
        for entry in agent.conversation_history:
            meta = entry.get("metadata", {})
            if isinstance(meta, dict):
                files = meta.get("files_changed", [])
                if files:
                    # Agent contributed code
                    task_id = entry.get("content", "")[:20]
                    stories.append(task_id)
        return stories[:20]  # Cap for storage

    def roll_for_departures(
        self,
        sprint_num: int,
        agents: List["BaseAgent"],
    ) -> List[DepartureEvent]:
        """Bernoulli trial per eligible agent. Returns list of departures."""
        if not self._config.enabled:
            return []
        if sprint_num < self._config.starts_after_sprint:
            return []

        eligible = [a for a in agents if not self._is_protected(a)]
        if not eligible:
            return []

        departures: List[DepartureEvent] = []
        for agent in eligible:
            if len(departures) >= self._config.max_departures_per_sprint:
                break
            if self._rng.random() < self._config.probability_per_sprint:
                backfill_sprint: Optional[int] = None
                if self._config.backfill_enabled:
                    backfill_sprint = sprint_num + self._config.backfill_delay_sprints

                event = DepartureEvent(
                    sprint=sprint_num,
                    agent_id=agent.config.role_id,
                    agent_name=agent.config.name,
                    seniority=agent.config.seniority,
                    specializations_lost=list(agent.config.specializations),
                    stories_contributed=self._get_contributed_stories(agent),
                    meta_learnings_count=self._count_meta_learnings(agent),
                    backfill_sprint=backfill_sprint,
                )
                departures.append(event)
                self._departure_history.append(event)

        return departures

    def generate_departure_report(
        self,
        events: List[DepartureEvent],
        output_dir: Path,
    ) -> None:
        """Write departure_report.json to sprint artifacts."""
        output_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "departures": [
                {
                    "sprint": e.sprint,
                    "agent_id": e.agent_id,
                    "agent_name": e.agent_name,
                    "seniority": e.seniority,
                    "specializations_lost": e.specializations_lost,
                    "stories_contributed": e.stories_contributed,
                    "meta_learnings_count": e.meta_learnings_count,
                    "backfill_sprint": e.backfill_sprint,
                }
                for e in events
            ]
        }
        path = output_dir / "departure_report.json"
        path.write_text(json.dumps(report, indent=2))

    async def create_replacement(
        self,
        departed: DepartureEvent,
        factory: "AgentFactory",
        team_agents: List["BaseAgent"],
    ) -> Optional["BaseAgent"]:
        """Create a fresh agent following hiring protocol.

        The replacement:
        - Gets a new individual personality (picks from available pool)
        - Has the same or adjacent specialization to departed agent
        - Has no conversation history, no meta-learnings
        - Gets the A-candidate baseline descriptor applied
        """
        # Build a new agent config dict that mirrors the departed agent
        # but with a fresh personality
        available_individuals = self._get_available_individuals(team_agents)
        individual = (
            self._rng.choice(available_individuals) if available_individuals else ""
        )

        new_role_id = f"backfill_{departed.agent_id}"
        agent_cfg: Dict[str, Any] = {
            "name": f"Backfill for {departed.agent_name}",
            "individual": individual,
            "seniority": departed.seniority,
            "specializations": departed.specializations_lost,
            "role_archetype": "developer",
            "model": "mock-model",
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        config = factory._create_agent_config(new_role_id, agent_cfg)

        # Create runtime if the factory has runtime configs
        runtime = None
        if "tools" in agent_cfg and agent_cfg["tools"]:
            workspace_root = factory.runtime_configs.get("tools", {}).get(
                "workspace_root", "/tmp/agent-workspace"
            )
            runtime = factory._create_agent_runtime(
                new_role_id, agent_cfg, workspace_root
            )

        from ..agents.base_agent import BaseAgent

        return BaseAgent(config, factory.vllm_endpoint, runtime=runtime)

    def _get_available_individuals(
        self, current_agents: List["BaseAgent"]
    ) -> List[str]:
        """Get individual personality files not currently in use."""
        used = {a.config.individual for a in current_agents if a.config.individual}
        individuals_dir = Path("team_config") / "05_individuals"
        if not individuals_dir.exists():
            return []
        available = []
        for p in individuals_dir.glob("*.md"):
            name = p.stem
            if name not in used:
                available.append(name)
        return available
