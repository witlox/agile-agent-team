"""Configuration loading and management."""

import os

import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExperimentConfig:
    name: str
    sprint_duration_minutes: int
    database_url: str
    team_config_dir: str
    vllm_endpoint: str
    agent_configs: Dict[str, Dict] = field(default_factory=dict)
    runtime_configs: Dict[str, Dict] = field(
        default_factory=dict
    )  # NEW: Runtime configurations
    wip_limits: Dict[str, int] = field(
        default_factory=lambda: {"in_progress": 4, "review": 2}
    )
    sprints_per_stakeholder_review: int = 5
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
    # Sprint 0 configuration
    sprint_zero_enabled: bool = True  # Run Sprint 0 for infrastructure setup


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

    sprints_per_stakeholder_review = 5
    if "experiment" in data and "sprints_per_stakeholder_review" in data["experiment"]:
        sprints_per_stakeholder_review = data["experiment"][
            "sprints_per_stakeholder_review"
        ]

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

    # Sprint 0 configuration
    sprint_zero_enabled = True
    if "sprint_zero" in data:
        sprint_zero_enabled = data["sprint_zero"].get("enabled", True)

    # Allow DATABASE_URL env var to override config (useful for local dev / mock mode)
    resolved_db_url = (
        database_url or os.environ.get("DATABASE_URL") or data["database"]["url"]
    )

    return ExperimentConfig(
        name=data["experiment"]["name"],
        sprint_duration_minutes=data["experiment"]["sprint_duration_minutes"],
        database_url=resolved_db_url,
        team_config_dir=data["team"]["config_dir"],
        vllm_endpoint=data["models"]["vllm_endpoint"],
        agent_configs=agent_configs,
        runtime_configs=runtime_configs,
        wip_limits=wip_limits,
        sprints_per_stakeholder_review=sprints_per_stakeholder_review,
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
        sprint_zero_enabled=sprint_zero_enabled,
    )
