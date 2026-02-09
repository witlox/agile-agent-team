"""Specialist consultant on-boarding system.

Allows team to bring in external specialists for 1 day when lacking expertise.
Max 3 consultations per sprint with velocity penalty.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent
    from ..tools.shared_context import SharedContextDB

from ..agents.base_agent import BaseAgent, AgentConfig


@dataclass
class SpecialistRequest:
    """Request for specialist consultation."""

    reason: str  # Why specialist is needed
    domain: str  # Domain expertise required (ml, security, performance, etc.)
    requesting_agent_id: str  # Who requested
    blocked_task_id: Optional[str] = None  # Task that's blocked (if applicable)
    sprint_num: int = 0
    day_num: int = 0


@dataclass
class ConsultationOutcome:
    """Result of specialist consultation."""

    specialist_domain: str
    trainee_id: str  # Team member who paired with specialist
    duration_hours: int  # Simulated hours (typically 8 for 1 day)
    knowledge_transferred: str  # What was learned
    issue_resolved: bool
    velocity_penalty: float  # Story points lost to consultation
    learnings: List[str]  # Key takeaways


class SpecialistConsultantSystem:
    """Manages specialist consultant on-boarding and tracking."""

    def __init__(
        self,
        team_config_dir: str,
        db: Optional["SharedContextDB"] = None,
        max_per_sprint: int = 3,
        velocity_penalty_per_consultation: float = 2.0,
    ):
        """Initialize specialist consultant system.

        Args:
            team_config_dir: Path to team_config directory
            db: Optional database for tracking
            max_per_sprint: Maximum consultations per sprint (default: 3)
            velocity_penalty_per_consultation: Story points penalty per consultation
        """
        self.team_config_dir = Path(team_config_dir)
        self.db = db
        self.max_per_sprint = max_per_sprint
        self.velocity_penalty = velocity_penalty_per_consultation

        # Track usage per sprint
        self.consultations_used: Dict[int, int] = {}  # {sprint_num: count}
        self.consultation_history: List[ConsultationOutcome] = []

        # Available specialist domains
        self.specialist_domains = {
            "ml": "Machine Learning / AI",
            "security": "Security / Authentication / Authorization",
            "performance": "Performance Optimization / Profiling",
            "cloud": "Cloud / DevOps / Infrastructure",
            "architecture": "Software Architecture / Design Patterns",
            "database": "Database Design / Optimization",
            "frontend": "Advanced Frontend / React / TypeScript",
            "distributed": "Distributed Systems / Microservices",
            "data": "Data Engineering / Pipelines",
            "mobile": "Mobile Development (iOS/Android)",
        }

    def can_request_specialist(self, sprint_num: int) -> bool:
        """Check if team can request specialist consultation.

        Args:
            sprint_num: Current sprint number

        Returns:
            True if consultation available, False if limit reached
        """
        used = self.consultations_used.get(sprint_num, 0)
        return used < self.max_per_sprint

    def get_remaining_consultations(self, sprint_num: int) -> int:
        """Get remaining consultations for sprint.

        Args:
            sprint_num: Current sprint number

        Returns:
            Number of consultations remaining
        """
        used = self.consultations_used.get(sprint_num, 0)
        return max(0, self.max_per_sprint - used)

    def should_request_specialist(
        self, blocker_description: str, team_skills: List[str]
    ) -> Optional[str]:
        """Determine if specialist is needed based on blocker.

        Args:
            blocker_description: Description of blocker/issue
            team_skills: List of team's existing skills/specializations

        Returns:
            Domain of specialist needed, or None if team can handle it
        """
        blocker_lower = blocker_description.lower()

        # Check for expertise gaps
        needs_ml = any(
            kw in blocker_lower
            for kw in ["machine learning", "ml", "neural", "model", "training", "inference"]
        )
        needs_security = any(
            kw in blocker_lower
            for kw in ["security", "authentication", "oauth", "encryption", "vulnerability"]
        )
        needs_performance = any(
            kw in blocker_lower
            for kw in ["performance", "slow", "optimize", "profiling", "memory leak"]
        )
        needs_cloud = any(
            kw in blocker_lower
            for kw in ["kubernetes", "k8s", "docker", "aws", "cloud", "deployment"]
        )
        needs_distributed = any(
            kw in blocker_lower
            for kw in ["distributed", "microservices", "consistency", "eventual", "saga"]
        )

        # Check if team already has this expertise
        if needs_ml and "ml" not in team_skills:
            return "ml"
        if needs_security and "security" not in team_skills:
            return "security"
        if needs_performance and "performance" not in team_skills:
            return "performance"
        if needs_cloud and "cloud" not in team_skills:
            return "cloud"
        if needs_distributed and "distributed" not in team_skills:
            return "distributed"

        return None

    async def request_specialist(
        self,
        request: SpecialistRequest,
        team: List["BaseAgent"],
    ) -> Optional[ConsultationOutcome]:
        """Request specialist consultation.

        Args:
            request: Specialist request details
            team: Current team members

        Returns:
            ConsultationOutcome if successful, None if limit reached
        """
        # Check limit
        if not self.can_request_specialist(request.sprint_num):
            return None

        # Track usage
        used = self.consultations_used.get(request.sprint_num, 0)
        self.consultations_used[request.sprint_num] = used + 1

        # Create temporary specialist agent
        specialist = self._create_specialist(request.domain)

        # Find best trainee (prefer junior/mid for learning opportunity)
        trainee = self._select_trainee(team, request.domain)

        # Simulate consultation (1 day pairing)
        outcome = await self._conduct_consultation(
            specialist, trainee, request
        )

        # Record outcome
        self.consultation_history.append(outcome)

        return outcome

    def _create_specialist(self, domain: str) -> BaseAgent:
        """Create temporary specialist agent.

        Args:
            domain: Specialist domain

        Returns:
            BaseAgent configured as specialist
        """
        # Load specialist profile
        specialist_profile = self._load_specialist_profile(domain)

        # Create agent config
        config = AgentConfig(
            role_id=f"specialist_{domain}",
            name=f"External {domain.upper()} Specialist",
            role_archetype="developer",
            seniority="senior",
            specializations=[domain],
            model="mock-model",  # Will use configured runtime
            temperature=0.7,
            max_tokens=2000,
        )

        # Create agent with specialist profile
        agent = BaseAgent(config, vllm_endpoint="mock://")
        # Append specialist expertise to existing prompt
        agent.prompt = agent.prompt + "\n\n---\n\n" + specialist_profile

        return agent

    def _load_specialist_profile(self, domain: str) -> str:
        """Load specialist profile from team_config.

        Args:
            domain: Specialist domain

        Returns:
            Profile text with specialist expertise
        """
        # Try to load from team_config/07_specialists/
        specialist_file = self.team_config_dir / "07_specialists" / f"{domain}_specialist.md"

        if specialist_file.exists():
            return specialist_file.read_text()

        # Fallback to generic specialist profile
        return f"""# {domain.upper()} Specialist

You are an external consultant with deep expertise in {self.specialist_domains.get(domain, domain)}.

**Your Role:**
- Provide expert guidance on {domain}-related challenges
- Teach best practices and patterns
- Help team overcome technical blockers
- Transfer knowledge efficiently (you're here for 1 day only)

**Your Approach:**
- Ask clarifying questions to understand the problem
- Explain concepts clearly with examples
- Suggest practical, actionable solutions
- Teach "why" not just "how"
- Leave team better prepared for similar problems

**Remember:** You're a temporary consultant. Your goal is to unblock the team and transfer knowledge, not to do the work for them.
"""

    def _select_trainee(self, team: List["BaseAgent"], domain: str) -> "BaseAgent":
        """Select team member to pair with specialist.

        Prefers junior/mid developers for learning opportunity.

        Args:
            team: Current team members
            domain: Specialist domain

        Returns:
            Selected team member
        """
        developers = [
            a for a in team
            if "developer" in a.config.role_archetype
            and not any(d in getattr(a.config, "specializations", []) for d in [domain])
        ]

        # Prefer junior/mid for learning
        juniors = [a for a in developers if a.config.seniority == "junior"]
        if juniors:
            return juniors[0]

        mids = [a for a in developers if a.config.seniority == "mid"]
        if mids:
            return mids[0]

        # Fallback to any developer
        return developers[0] if developers else team[0]

    async def _conduct_consultation(
        self,
        specialist: BaseAgent,
        trainee: BaseAgent,
        request: SpecialistRequest,
    ) -> ConsultationOutcome:
        """Conduct specialist consultation (simulated).

        Args:
            specialist: Specialist agent
            trainee: Team member learning
            request: Original request

        Returns:
            ConsultationOutcome with results
        """
        # Simulate 1 day consultation
        knowledge_transferred = f"Expert {request.domain} patterns and best practices"
        issue_resolved = True  # Assume specialist helps resolve the blocker

        # Generate learnings
        learnings = [
            f"{request.domain.upper()} expertise gained by {trainee.config.name}",
            f"Blocker resolved with specialist guidance: {request.reason}",
            f"Team now better equipped for {request.domain} challenges",
        ]

        return ConsultationOutcome(
            specialist_domain=request.domain,
            trainee_id=trainee.config.role_id,
            duration_hours=8,  # 1 day
            knowledge_transferred=knowledge_transferred,
            issue_resolved=issue_resolved,
            velocity_penalty=self.velocity_penalty,
            learnings=learnings,
        )

    def get_sprint_summary(self, sprint_num: int) -> Dict:
        """Get specialist consultation summary for sprint.

        Args:
            sprint_num: Sprint number

        Returns:
            Summary dict with usage and outcomes
        """
        sprint_consultations = [
            c for c in self.consultation_history
            if any(sprint_num == getattr(r, 'sprint_num', 0)
                   for r in [c])  # Match by sprint
        ]

        return {
            "consultations_used": self.consultations_used.get(sprint_num, 0),
            "consultations_remaining": self.get_remaining_consultations(sprint_num),
            "total_velocity_penalty": len(sprint_consultations) * self.velocity_penalty,
            "domains_consulted": [c.specialist_domain for c in sprint_consultations],
            "issues_resolved": sum(1 for c in sprint_consultations if c.issue_resolved),
        }
