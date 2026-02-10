"""Specialist consultant on-boarding system.

Allows team to bring in external specialists for 1 day when lacking expertise.
Max 3 consultations per sprint with velocity penalty.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
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
            # Original 10
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
            # Infrastructure & operations
            "backend": "Backend Development / APIs / Data Persistence",
            "devops": "DevOps / CI/CD / Infrastructure as Code",
            "networking": "Network Architecture / Protocols / Security",
            "embedded": "Embedded Systems / Real-Time / Firmware",
            "systems": "Systems Programming / Low-Level Performance",
            "observability": "Monitoring / Logging / Tracing / Alerting",
            "sre": "Site Reliability / SLOs / Incident Management",
            "platform": "Platform Engineering / Developer Experience",
            "admin": "System Administration / OS / Backup / Recovery",
            # Development specializations
            "api_design": "API Design / REST / GraphQL / gRPC",
            "ui_ux": "UI/UX Design / Interaction Patterns",
            "test_automation": "Test Automation / Frameworks / CI Integration",
            "quality": "Quality Engineering / Test Strategy / Risk-Based Testing",
            "accessibility": "Accessibility / WCAG / Assistive Technologies",
            "blockchain": "Blockchain / Smart Contracts / Web3",
            "event_driven": "Event-Driven Architecture / Messaging / CQRS",
            "search": "Search Engineering / Relevance / Information Retrieval",
            "i18n": "Internationalization / Localization / Unicode",
            "business_processes": "Business Process Modeling / DDD / Workflow Engines",
            "iam": "Identity & Access Management / AuthZ / Zero Trust",
            "mlops": "MLOps / Model Deployment / ML Pipelines",
            "data_science": "Data Science / Statistics / Experimentation",
            # Language specialists
            "python": "Python / Type Hints / Async / Ecosystem",
            "golang": "Go / Concurrency / Performance / Ecosystem",
            "rust": "Rust / Ownership / Safety / Performance",
            "typescript": "TypeScript / Type System / React / Node.js",
            "cpp": "C++ / Modern C++ / Memory Safety / Build Systems",
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

        # Domain keyword mapping — checked in order of specificity
        # (more specific domains first to avoid false matches)
        domain_keywords: Dict[str, List[str]] = {
            "mlops": [
                "mlops",
                "model deployment",
                "model serving",
                "feature store",
                "model registry",
                "model drift",
            ],
            "ml": [
                "machine learning",
                "neural",
                "training loss",
                "deep learning",
                "inference",
                "transformer model",
            ],
            "data_science": [
                "a/b test",
                "experiment design",
                "statistical",
                "hypothesis test",
                "data analysis",
                "analytics",
            ],
            "sre": [
                "slo ",
                "slos",
                "sli ",
                "slis",
                "error budget",
                "incident management",
                "postmortem",
                "on-call",
                "site reliability",
            ],
            "observability": [
                "monitoring",
                "tracing",
                "alerting",
                "opentelemetry",
                "prometheus",
                "grafana",
                "logging pipeline",
            ],
            "event_driven": [
                "kafka",
                "rabbitmq",
                "event sourcing",
                "cqrs",
                "message queue",
                "pub/sub",
                "saga pattern",
            ],
            "iam": [
                "identity",
                "access management",
                "rbac",
                "abac",
                "scim",
                "sso",
                "saml",
                "openid connect",
                "zero trust",
            ],
            "security": [
                "security",
                "authentication",
                "oauth",
                "encryption",
                "vulnerability",
                "penetration test",
            ],
            "search": [
                "elasticsearch",
                "search relevance",
                "full-text search",
                "indexing",
                "solr",
                "search engine",
            ],
            "blockchain": [
                "blockchain",
                "smart contract",
                "solidity",
                "web3",
                "decentralized",
            ],
            "embedded": [
                "embedded",
                "firmware",
                "microcontroller",
                "rtos",
                "real-time os",
                "gpio",
                "sensor",
            ],
            "systems": [
                "systems programming",
                "memory management",
                "lock-free",
                "cache line",
                "simd",
                "unsafe code",
            ],
            "platform": [
                "developer platform",
                "backstage",
                "golden path",
                "internal tooling",
                "developer experience",
            ],
            "business_processes": [
                "business process",
                "bpmn",
                "workflow engine",
                "temporal",
                "camunda",
                "domain-driven",
            ],
            "i18n": [
                "internationalization",
                "localization",
                "i18n",
                "l10n",
                "unicode",
                "translation",
                "rtl layout",
            ],
            "accessibility": [
                "accessibility",
                "wcag",
                "screen reader",
                "aria",
                "a11y",
                "assistive technology",
            ],
            "quality": [
                "test strategy",
                "test pyramid",
                "mutation testing",
                "quality gate",
                "test coverage strategy",
            ],
            "test_automation": [
                "test automation",
                "selenium",
                "playwright",
                "cypress",
                "flaky test",
                "test framework",
            ],
            "performance": [
                "performance",
                "slow",
                "optimize",
                "profiling",
                "memory leak",
                "latency",
            ],
            "cloud": [
                "kubernetes",
                "k8s",
                "docker",
                "aws",
                "cloud",
                "terraform",
                "infrastructure as code",
            ],
            "devops": [
                "ci/cd",
                "pipeline",
                "deployment",
                "jenkins",
                "github actions",
                "gitops",
            ],
            "networking": [
                "networking",
                "dns",
                "firewall",
                "load balancer",
                "tcp",
                "vpn",
                "proxy",
                "subnet",
            ],
            "distributed": [
                "distributed",
                "microservices",
                "consistency",
                "eventual",
                "circuit breaker",
            ],
            "database": [
                "database",
                "sql",
                "postgres",
                "mongodb",
                "redis",
                "query optimization",
                "migration",
            ],
            "backend": ["backend", "api design", "rest api", "graphql", "server-side"],
            "frontend": ["frontend", "react", "css", "component", "webpack", "browser"],
            "mobile": [
                "mobile",
                "ios",
                "android",
                "swift",
                "kotlin",
                "react native",
                "flutter",
            ],
            "api_design": [
                "api versioning",
                "openapi",
                "swagger",
                "grpc",
                "api contract",
            ],
            "ui_ux": [
                "user experience",
                "ux",
                "usability",
                "wireframe",
                "design system",
                "interaction design",
            ],
            "admin": [
                "system administration",
                "sysadmin",
                "active directory",
                "ldap",
                "backup recovery",
                "patch management",
            ],
            "data": [
                "data pipeline",
                "etl",
                "airflow",
                "spark",
                "dbt",
                "data warehouse",
            ],
            "architecture": [
                "architecture",
                "design pattern",
                "scalability",
                "system design",
            ],
            # Language specialists
            "python": ["python", "django", "fastapi", "pytest", "mypy"],
            "golang": ["golang", "go module", "goroutine"],
            "rust": ["rust", "borrow checker", "cargo", "ownership model"],
            "typescript": ["typescript", "type system", "tsconfig"],
            "cpp": ["c++", "cmake", "memory safety c", "raii"],
        }

        # Check each domain — return first match not in team skills
        for domain, keywords in domain_keywords.items():
            if any(kw in blocker_lower for kw in keywords):
                if domain not in team_skills:
                    return domain

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
        outcome = await self._conduct_consultation(specialist, trainee, request)

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
        # Try to load from team_config/08_specialists/
        specialist_file = (
            self.team_config_dir / "08_specialists" / f"{domain}_specialist.md"
        )

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
            a
            for a in team
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
            c
            for c in self.consultation_history
            if any(
                sprint_num == getattr(r, "sprint_num", 0) for r in [c]
            )  # Match by sprint
        ]

        return {
            "consultations_used": self.consultations_used.get(sprint_num, 0),
            "consultations_remaining": self.get_remaining_consultations(sprint_num),
            "total_velocity_penalty": len(sprint_consultations) * self.velocity_penalty,
            "domains_consulted": [c.specialist_domain for c in sprint_consultations],
            "issues_resolved": sum(1 for c in sprint_consultations if c.issue_resolved),
        }
