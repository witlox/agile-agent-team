"""Configuration loading and management."""

import os

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ExperimentConfig:
    name: str
    sprint_duration_minutes: int
    database_url: str
    team_config_dir: str
    vllm_endpoint: str
    agent_configs: Dict[str, Dict] = field(default_factory=dict)
    wip_limits: Dict[str, int] = field(default_factory=lambda: {"in_progress": 4, "review": 2})
    sprints_per_stakeholder_review: int = 5


def load_config(config_path: str, database_url: Optional[str] = None) -> ExperimentConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        data = yaml.safe_load(f)

    agent_configs: Dict[str, Dict] = {}
    if "models" in data and "agents" in data["models"]:
        agent_configs = data["models"]["agents"]

    wip_limits: Dict[str, int] = {"in_progress": 4, "review": 2}
    if "team" in data and "wip_limits" in data["team"]:
        wip_limits = data["team"]["wip_limits"]

    sprints_per_stakeholder_review = 5
    if "experiment" in data and "sprints_per_stakeholder_review" in data["experiment"]:
        sprints_per_stakeholder_review = data["experiment"]["sprints_per_stakeholder_review"]

    # Allow DATABASE_URL env var to override config (useful for local dev / mock mode)
    resolved_db_url = (
        database_url
        or os.environ.get("DATABASE_URL")
        or data["database"]["url"]
    )

    return ExperimentConfig(
        name=data["experiment"]["name"],
        sprint_duration_minutes=data["experiment"]["sprint_duration_minutes"],
        database_url=resolved_db_url,
        team_config_dir=data["team"]["config_dir"],
        vllm_endpoint=data["models"]["vllm_endpoint"],
        agent_configs=agent_configs,
        wip_limits=wip_limits,
        sprints_per_stakeholder_review=sprints_per_stakeholder_review,
    )
