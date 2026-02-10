"""Configuration loading and management."""

import os
import warnings

import yaml
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TeamConfig:
    """Per-team configuration within a multi-team experiment."""

    id: str
    name: str = ""
    team_type: str = ""
    agent_ids: List[str] = field(default_factory=list)
    backlog_path: str = ""
    wip_limits: Optional[Dict[str, int]] = None


@dataclass
class CoordinationConfig:
    """Cross-team coordination settings."""

    enabled: bool = False
    full_loop_cadence: int = 1  # Every N sprints
    mid_sprint_checkin: bool = True
    max_borrows_per_sprint: int = 2
    borrow_duration_sprints: int = 1
    dependency_tracking: bool = True
    portfolio_triage: bool = True
    coordinator_agent_ids: List[str] = field(default_factory=list)


@dataclass
class ExperimentConfig:
    name: str = ""
    sprint_duration_minutes: int = 60  # Wall-clock minutes per sprint (recommended: 60)
    database_url: str = ""
    team_config_dir: str = "team_config"
    vllm_endpoint: str = ""
    agent_configs: Dict[str, Dict] = field(default_factory=dict)
    runtime_configs: Dict[str, Dict] = field(
        default_factory=dict
    )  # NEW: Runtime configurations
    wip_limits: Dict[str, int] = field(
        default_factory=lambda: {"in_progress": 4, "review": 2}
    )
    sprints_per_stakeholder_review: int = 3
    # Stakeholder review configuration
    stakeholder_review_cadence: int = 3  # Every N sprints
    stakeholder_review_timeout_minutes: float = 60.0
    stakeholder_review_timeout_action: str = (
        "auto_approve"  # auto_approve|po_proxy|block
    )
    stakeholder_webhook_enabled: bool = False
    stakeholder_webhook_url: str = ""
    stakeholder_webhook_url_env: str = "STAKEHOLDER_WEBHOOK_URL"
    stakeholder_feedback_mode: str = "file"  # "callback" or "file"
    stakeholder_feedback_callback_port: int = 8081
    stakeholder_feedback_poll_interval: int = 30  # seconds
    disturbances_enabled: bool = False
    disturbance_frequencies: Dict[str, float] = field(default_factory=dict)
    blast_radius_controls: Dict[str, float] = field(default_factory=dict)
    profile_swap_mode: str = "none"
    profile_swap_scenarios: List[str] = field(default_factory=list)
    profile_swap_penalties: Dict[str, float] = field(default_factory=dict)
    tools_workspace_root: str = (
        "/tmp/agent-workspace"  # NEW: Workspace for code generation
    )
    repo_config: Optional[Dict] = None  # NEW: Optional git repo to clone
    workspace_mode: str = "per_story"  # per_story | per_sprint
    persist_across_sprints: bool = False  # Continue from previous sprint
    merge_completed_stories: bool = False  # Auto-merge to main after QA
    # Team constraints and dynamics
    max_engineers: int = 10  # Max engineers (excluding testers)
    max_total_team_size: int = 13  # Total team size including testers/PO/leads
    turnover_enabled: bool = False  # Simulate team member departures
    turnover_starts_after_sprint: int = 10  # When turnover begins (~5 months)
    turnover_probability: float = 0.05  # Per-sprint probability after threshold
    turnover_backfill: bool = True  # Auto-hire replacements
    tester_pairing_enabled: bool = True  # Testers can pair as navigators
    tester_pairing_frequency: float = 0.20  # 20% of sessions include tester
    # Remote git integration (GitHub/GitLab)
    remote_git_enabled: bool = False
    remote_git_provider: str = "github"  # "github" or "gitlab"
    remote_git_config: Dict[str, Dict] = field(default_factory=dict)
    # Sprint time simulation
    num_simulated_days: int = 5  # Simulated working days per sprint
    # Sprint 0 configuration
    sprint_zero_enabled: bool = True  # Run Sprint 0 for infrastructure setup
    # Domain research configuration (PO reads context docs + web search)
    domain_research_enabled: bool = False
    domain_research_config: Dict[str, Any] = field(default_factory=dict)
    # Team Topologies
    team_type: str = ""  # stream_aligned | platform | enabling | complicated_subsystem
    # Messaging / message bus configuration
    messaging_backend: str = "asyncio"  # "asyncio" or "redis"
    messaging_redis_url: str = "redis://localhost:6379"
    messaging_history_size: int = 1000
    messaging_log_messages: bool = False
    # Multi-team configuration
    teams: List[TeamConfig] = field(default_factory=list)
    # Cross-team coordination
    coordination: CoordinationConfig = field(default_factory=CoordinationConfig)


def load_config(
    config_path: str, database_url: Optional[str] = None
) -> ExperimentConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        data = yaml.safe_load(f)

    agent_configs: Dict[str, Dict] = {}
    if "models" in data and "agents" in data["models"]:
        agent_configs = data["models"]["agents"]

    # Load runtime configurations
    runtime_configs: Dict[str, Dict] = {}
    if "runtimes" in data:
        runtime_configs = data["runtimes"]

    wip_limits: Dict[str, int] = {"in_progress": 4, "review": 2}
    if "team" in data and "wip_limits" in data["team"]:
        wip_limits = data["team"]["wip_limits"]

    sprints_per_stakeholder_review = 3
    if "experiment" in data and "sprints_per_stakeholder_review" in data["experiment"]:
        sprints_per_stakeholder_review = data["experiment"][
            "sprints_per_stakeholder_review"
        ]

    # Stakeholder review configuration (new section takes precedence)
    stakeholder_review_cadence = sprints_per_stakeholder_review
    stakeholder_review_timeout_minutes = 60.0
    stakeholder_review_timeout_action = "auto_approve"
    stakeholder_webhook_enabled = False
    stakeholder_webhook_url = ""
    stakeholder_webhook_url_env = "STAKEHOLDER_WEBHOOK_URL"
    stakeholder_feedback_mode = "file"
    stakeholder_feedback_callback_port = 8081
    stakeholder_feedback_poll_interval = 30

    if "stakeholder_review" in data:
        sr = data["stakeholder_review"]
        stakeholder_review_cadence = sr.get("cadence", stakeholder_review_cadence)
        # Keep the alias in sync
        sprints_per_stakeholder_review = stakeholder_review_cadence
        stakeholder_review_timeout_minutes = float(sr.get("timeout_minutes", 60.0))
        stakeholder_review_timeout_action = sr.get("timeout_action", "auto_approve")

        if "webhook" in sr:
            wh = sr["webhook"]
            stakeholder_webhook_enabled = wh.get("enabled", False)
            stakeholder_webhook_url = wh.get("url", "")
            stakeholder_webhook_url_env = wh.get("url_env", "STAKEHOLDER_WEBHOOK_URL")
            # Resolve URL from env if direct URL not provided
            if not stakeholder_webhook_url and stakeholder_webhook_url_env:
                stakeholder_webhook_url = os.environ.get(
                    stakeholder_webhook_url_env, ""
                )

        if "feedback" in sr:
            fb = sr["feedback"]
            stakeholder_feedback_mode = fb.get("mode", "file")
            stakeholder_feedback_callback_port = int(fb.get("callback_port", 8081))
            stakeholder_feedback_poll_interval = int(fb.get("poll_interval", 30))

    # Disturbance config
    disturbances_enabled = False
    disturbance_frequencies: Dict[str, float] = {}
    blast_radius_controls: Dict[str, float] = {}
    if "disturbances" in data:
        d = data["disturbances"]
        disturbances_enabled = bool(d.get("enabled", False))
        disturbance_frequencies = dict(d.get("frequencies", {}))
        blast_radius_controls = dict(d.get("blast_radius_controls", {}))

    # Profile swapping config
    profile_swap_mode = "none"
    profile_swap_scenarios: List[str] = []
    profile_swap_penalties: Dict[str, float] = {}
    if "profile_swapping" in data:
        ps = data["profile_swapping"]
        profile_swap_mode = ps.get("mode", "none")
        profile_swap_scenarios = list(ps.get("allowed_scenarios", []))
        profile_swap_penalties = dict(ps.get("penalties", {}))

    # Tools and workspace config
    tools_workspace_root = "/tmp/agent-workspace"
    repo_config = None
    workspace_mode = "per_story"
    persist_across_sprints = False
    merge_completed_stories = False

    if "runtimes" in data and "tools" in data["runtimes"]:
        tools_workspace_root = data["runtimes"]["tools"].get(
            "workspace_root", tools_workspace_root
        )

    if "code_generation" in data:
        cg = data["code_generation"]
        repo_config = cg.get("repo_config")
        workspace_mode = cg.get("workspace_mode", "per_story")
        persist_across_sprints = cg.get("persist_across_sprints", False)
        merge_completed_stories = cg.get("merge_completed_stories", False)

    # Team constraints and dynamics
    max_engineers = 10
    max_total_team_size = 13
    turnover_enabled = False
    turnover_starts_after_sprint = 10
    turnover_probability = 0.05
    turnover_backfill = True
    tester_pairing_enabled = True
    tester_pairing_frequency = 0.20

    if "team" in data:
        max_engineers = data["team"].get("max_engineers", 10)
        max_total_team_size = data["team"].get("max_total_team_size", 13)

        if "turnover" in data["team"]:
            turnover = data["team"]["turnover"]
            turnover_enabled = turnover.get("enabled", False)
            turnover_starts_after_sprint = turnover.get("starts_after_sprint", 10)
            turnover_probability = turnover.get("probability_per_sprint", 0.05)
            turnover_backfill = turnover.get("backfill_enabled", True)

        if "tester_pairing" in data["team"]:
            tester_pairing = data["team"]["tester_pairing"]
            tester_pairing_enabled = tester_pairing.get("enabled", True)
            tester_pairing_frequency = tester_pairing.get("frequency", 0.20)

    # Team Topologies
    team_type = ""
    if "team" in data:
        team_type = data["team"].get("team_type", "")

    # Remote git configuration
    remote_git_enabled = False
    remote_git_provider = "github"
    remote_git_config: Dict[str, Dict] = {}

    if "remote_git" in data:
        rg = data["remote_git"]
        remote_git_enabled = rg.get("enabled", False)
        remote_git_provider = rg.get("provider", "github")
        remote_git_config = {
            "github": rg.get("github", {}),
            "gitlab": rg.get("gitlab", {}),
            "author_email_domain": rg.get("author_email_domain", "agent.local"),
        }

    # Sprint time simulation
    num_simulated_days = 5
    if "experiment" in data:
        num_simulated_days = data["experiment"].get("num_simulated_days", 5)

    # Sprint 0 configuration
    sprint_zero_enabled = True
    if "sprint_zero" in data:
        sprint_zero_enabled = data["sprint_zero"].get("enabled", True)

    # Domain research configuration
    domain_research_enabled = False
    domain_research_config: Dict[str, Any] = {}
    if "domain_research" in data:
        dr = data["domain_research"]
        domain_research_enabled = dr.get("enabled", False)
        domain_research_config = {
            "context_documents": dr.get("context_documents", []),
            "web_search": dr.get("web_search", {}),
        }

    # Messaging configuration
    messaging_backend = "asyncio"
    messaging_redis_url = "redis://localhost:6379"
    messaging_history_size = 1000
    messaging_log_messages = False
    if "messaging" in data:
        msg = data["messaging"]
        messaging_backend = msg.get("backend", "asyncio")
        messaging_redis_url = msg.get("redis_url", "redis://localhost:6379")
        messaging_history_size = int(msg.get("history_size", 1000))
        messaging_log_messages = bool(msg.get("log_messages", False))

    # Inject domain_research into runtime_configs so AgentFactory can see it
    if domain_research_enabled:
        runtime_configs["domain_research"] = {
            "enabled": True,
            **domain_research_config,
        }

    # Multi-team configuration
    teams: List[TeamConfig] = []
    if "teams" in data:
        for td in data["teams"]:
            teams.append(
                TeamConfig(
                    id=td["id"],
                    name=td.get("name", td["id"]),
                    team_type=td.get("team_type", team_type),
                    agent_ids=list(td.get("agents", [])),
                    backlog_path=td.get("backlog", ""),
                    wip_limits=td.get("wip_limits"),
                )
            )

        # Deprecation warning: backlog_path in multi-team mode
        for tc in teams:
            if tc.backlog_path:
                warnings.warn(
                    f"Team '{tc.id}' has backlog_path set. In multi-team mode, "
                    "portfolio stories are distributed intelligently from the "
                    "shared backlog. Per-team backlog_path is deprecated and "
                    "will be removed in a future version.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Validation: all agent_ids must exist in models.agents
        for tc in teams:
            for aid in tc.agent_ids:
                if aid not in agent_configs:
                    raise ValueError(
                        f"Team '{tc.id}' references unknown agent '{aid}'. "
                        f"Available agents: {sorted(agent_configs.keys())}"
                    )

        # Validation: no agent in more than one team
        seen_agents: Dict[str, str] = {}
        for tc in teams:
            for aid in tc.agent_ids:
                if aid in seen_agents:
                    raise ValueError(
                        f"Agent '{aid}' is assigned to both team "
                        f"'{seen_agents[aid]}' and '{tc.id}'. "
                        "Each agent can belong to at most one team."
                    )
                seen_agents[aid] = tc.id

        # Validation: 2-7 teams
        if len(teams) < 2:
            raise ValueError(f"Multi-team mode requires 2-7 teams, got {len(teams)}.")
        if len(teams) > 7:
            raise ValueError(
                f"Multi-team mode supports at most 7 teams, got {len(teams)}."
            )

    # Cross-team coordination configuration
    coordination = CoordinationConfig()
    if "coordination" in data:
        cc = data["coordination"]
        coordination = CoordinationConfig(
            enabled=cc.get("enabled", False),
            full_loop_cadence=int(cc.get("full_loop_cadence", 1)),
            mid_sprint_checkin=cc.get("mid_sprint_checkin", True),
            max_borrows_per_sprint=int(cc.get("max_borrows_per_sprint", 2)),
            borrow_duration_sprints=int(cc.get("borrow_duration_sprints", 1)),
            dependency_tracking=cc.get("dependency_tracking", True),
            portfolio_triage=cc.get("portfolio_triage", True),
            coordinator_agent_ids=list(cc.get("coordinators", [])),
        )

        # Validation: all coordinator agent_ids must exist in models.agents
        for cid in coordination.coordinator_agent_ids:
            if cid not in agent_configs:
                raise ValueError(
                    f"Coordinator '{cid}' not found in models.agents. "
                    f"Available agents: {sorted(agent_configs.keys())}"
                )

        # Validation: coordinators must NOT be assigned to any team
        team_agent_ids: set = set()
        for tc in teams:
            team_agent_ids.update(tc.agent_ids)
        for cid in coordination.coordinator_agent_ids:
            if cid in team_agent_ids:
                raise ValueError(
                    f"Coordinator '{cid}' is assigned to a team. "
                    "Coordinators must not belong to any team."
                )

    # Allow DATABASE_URL env var to override config (useful for local dev / mock mode)
    resolved_db_url = (
        database_url or os.environ.get("DATABASE_URL") or data["database"]["url"]
    )

    return ExperimentConfig(
        name=data["experiment"]["name"],
        sprint_duration_minutes=data["experiment"].get("sprint_duration_minutes", 60),
        database_url=resolved_db_url,
        team_config_dir=data["team"]["config_dir"],
        vllm_endpoint=data["models"]["vllm_endpoint"],
        agent_configs=agent_configs,
        runtime_configs=runtime_configs,
        wip_limits=wip_limits,
        sprints_per_stakeholder_review=sprints_per_stakeholder_review,
        stakeholder_review_cadence=stakeholder_review_cadence,
        stakeholder_review_timeout_minutes=stakeholder_review_timeout_minutes,
        stakeholder_review_timeout_action=stakeholder_review_timeout_action,
        stakeholder_webhook_enabled=stakeholder_webhook_enabled,
        stakeholder_webhook_url=stakeholder_webhook_url,
        stakeholder_webhook_url_env=stakeholder_webhook_url_env,
        stakeholder_feedback_mode=stakeholder_feedback_mode,
        stakeholder_feedback_callback_port=stakeholder_feedback_callback_port,
        stakeholder_feedback_poll_interval=stakeholder_feedback_poll_interval,
        disturbances_enabled=disturbances_enabled,
        disturbance_frequencies=disturbance_frequencies,
        blast_radius_controls=blast_radius_controls,
        profile_swap_mode=profile_swap_mode,
        profile_swap_scenarios=profile_swap_scenarios,
        profile_swap_penalties=profile_swap_penalties,
        tools_workspace_root=tools_workspace_root,
        repo_config=repo_config,
        workspace_mode=workspace_mode,
        persist_across_sprints=persist_across_sprints,
        merge_completed_stories=merge_completed_stories,
        max_engineers=max_engineers,
        max_total_team_size=max_total_team_size,
        turnover_enabled=turnover_enabled,
        turnover_starts_after_sprint=turnover_starts_after_sprint,
        turnover_probability=turnover_probability,
        turnover_backfill=turnover_backfill,
        tester_pairing_enabled=tester_pairing_enabled,
        tester_pairing_frequency=tester_pairing_frequency,
        remote_git_enabled=remote_git_enabled,
        remote_git_provider=remote_git_provider,
        remote_git_config=remote_git_config,
        num_simulated_days=num_simulated_days,
        sprint_zero_enabled=sprint_zero_enabled,
        domain_research_enabled=domain_research_enabled,
        domain_research_config=domain_research_config,
        team_type=team_type,
        messaging_backend=messaging_backend,
        messaging_redis_url=messaging_redis_url,
        messaging_history_size=messaging_history_size,
        messaging_log_messages=messaging_log_messages,
        teams=teams,
        coordination=coordination,
    )
