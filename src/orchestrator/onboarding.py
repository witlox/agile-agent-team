"""New agent onboarding protocol — buddy system and ramp-up.

Implements the Post-Hire section of ``hiring_protocol.md``:
- Buddy system: paired with senior for first N sprints
- Slow ramp-up: lower story point tasks, no solo driving
- Culture immersion: standup team update announcement
- Feedback loops: lead dev check-in after each onboarding sprint
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent


@dataclass
class OnboardingConfig:
    """Configuration for the onboarding protocol."""

    onboarding_duration_sprints: int = 2
    max_story_points_first_sprint: int = 3
    velocity_penalty_first_sprint: float = 0.5


@dataclass
class OnboardingState:
    """Tracks onboarding progress for a single agent."""

    agent_id: str
    hire_sprint: int
    buddy_id: str
    sprints_completed: int = 0
    first_contribution_sprint: Optional[int] = None
    first_contribution_action: Optional[int] = None
    convention_violations: int = 0
    is_complete: bool = False


class OnboardingManager:
    """Manages new agent onboarding per hiring_protocol.md Post-Hire section."""

    def __init__(
        self,
        config: OnboardingConfig,
        agents: Optional[List["BaseAgent"]] = None,
    ) -> None:
        self._config = config
        self._agents: List["BaseAgent"] = list(agents) if agents else []
        self._states: Dict[str, OnboardingState] = {}

    @property
    def config(self) -> OnboardingConfig:
        return self._config

    @property
    def active_onboardings(self) -> Dict[str, OnboardingState]:
        """Return all active (not complete) onboarding states."""
        return {aid: s for aid, s in self._states.items() if not s.is_complete}

    def update_agents(self, agents: List["BaseAgent"]) -> None:
        """Update the list of current team agents."""
        self._agents = list(agents)

    def _select_buddy(self, agent: "BaseAgent") -> str:
        """Select a buddy for the new agent.

        Priority:
        1. Dev lead (if available)
        2. Senior with matching specialization
        3. Any senior
        4. Any mid-level developer
        5. First available agent
        """
        # Prefer dev_lead
        for a in self._agents:
            if "dev_lead" in a.config.role_id or "lead" in a.config.role_archetype:
                if a.agent_id != agent.agent_id:
                    return a.agent_id

        # Senior with matching specialization
        new_specs = set(agent.config.specializations)
        for a in self._agents:
            if a.config.seniority == "senior" and a.agent_id != agent.agent_id:
                if new_specs & set(a.config.specializations):
                    return a.agent_id

        # Any senior
        for a in self._agents:
            if a.config.seniority == "senior" and a.agent_id != agent.agent_id:
                return a.agent_id

        # Any mid-level developer
        for a in self._agents:
            if a.config.seniority == "mid" and a.agent_id != agent.agent_id:
                return a.agent_id

        # Fallback: first available
        for a in self._agents:
            if a.agent_id != agent.agent_id:
                return a.agent_id

        return ""

    def start_onboarding(self, agent: "BaseAgent", sprint_num: int) -> None:
        """Initialize onboarding state and inject prompt context."""
        buddy_id = self._select_buddy(agent)
        state = OnboardingState(
            agent_id=agent.agent_id,
            hire_sprint=sprint_num,
            buddy_id=buddy_id,
        )
        self._states[agent.agent_id] = state

        # Find buddy name for the prompt
        buddy_name = buddy_id
        for a in self._agents:
            if a.agent_id == buddy_id:
                buddy_name = a.config.name
                break

        # Inject onboarding prompt into agent
        onboarding_notice = (
            f"\n\n[NEW TEAM MEMBER — Onboarding Sprint 1]\n"
            f"You just joined this team through the hiring process.\n"
            f"Your buddy is {buddy_name} ({buddy_id}). Pair with them first.\n"
            f"Start with smaller tasks. Ask questions freely.\n"
            f"Attend all ceremonies (standup, retro, planning).\n"
        )
        agent.prompt = agent.prompt + onboarding_notice

    def get_buddy_pairing_constraint(self, agent_id: str) -> Optional[str]:
        """Return buddy_id if agent is onboarding, None otherwise."""
        state = self._states.get(agent_id)
        if state is None or state.is_complete:
            return None
        return state.buddy_id

    def get_standup_announcement(self, agent_id: str) -> Optional[str]:
        """Return team update text for standup if agent just joined."""
        state = self._states.get(agent_id)
        if state is None or state.is_complete:
            return None
        if state.sprints_completed > 0:
            return None  # Only announce on first sprint
        # Find agent name
        agent_name = agent_id
        for a in self._agents:
            if a.agent_id == agent_id:
                agent_name = a.config.name
                break
        buddy_name = state.buddy_id
        for a in self._agents:
            if a.agent_id == state.buddy_id:
                buddy_name = a.config.name
                break
        return (
            f"New team member {agent_name} has joined! "
            f"Their buddy is {buddy_name}. "
            f"Please welcome them and help them get up to speed."
        )

    def record_contribution(
        self, agent_id: str, sprint_num: int, action_count: int
    ) -> None:
        """Record first contribution for metrics."""
        state = self._states.get(agent_id)
        if state is None:
            return
        if state.first_contribution_sprint is None:
            state.first_contribution_sprint = sprint_num
            state.first_contribution_action = action_count

    def advance_sprint(self, agent_id: str) -> None:
        """Increment sprints_completed; mark complete if past duration."""
        state = self._states.get(agent_id)
        if state is None:
            return
        state.sprints_completed += 1
        if state.sprints_completed >= self._config.onboarding_duration_sprints:
            state.is_complete = True

    def is_onboarding(self, agent_id: str) -> bool:
        """Return True if the agent is currently in onboarding."""
        state = self._states.get(agent_id)
        if state is None:
            return False
        return not state.is_complete

    def get_onboarding_metrics(self, agent_id: str) -> Dict:
        """Return onboarding metrics for the given agent."""
        state = self._states.get(agent_id)
        if state is None:
            return {}
        return {
            "agent_id": state.agent_id,
            "hire_sprint": state.hire_sprint,
            "buddy_id": state.buddy_id,
            "sprints_completed": state.sprints_completed,
            "first_contribution_sprint": state.first_contribution_sprint,
            "first_contribution_action": state.first_contribution_action,
            "convention_violations": state.convention_violations,
            "is_complete": state.is_complete,
        }
