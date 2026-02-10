"""Unit tests for CoordinationConfig and YAML parsing."""

from pathlib import Path

import pytest
import yaml

from src.agents.base_agent import AgentConfig
from src.orchestrator.config import (
    CoordinationConfig,
    ExperimentConfig,
    load_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    "experiment": {
        "name": "test-coordination",
        "sprint_duration_minutes": 30,
    },
    "team": {
        "config_dir": "team_config",
    },
    "models": {
        "vllm_endpoint": "http://localhost:8000",
        "agents": {
            "agent_a": {
                "name": "A",
                "seniority": "senior",
                "role_archetype": "developer",
            },
            "agent_b": {"name": "B", "seniority": "mid", "role_archetype": "developer"},
            "agent_c": {
                "name": "C",
                "seniority": "junior",
                "role_archetype": "developer",
            },
            "agent_d": {"name": "D", "seniority": "senior", "role_archetype": "tester"},
            "coord_se": {
                "name": "SE",
                "seniority": "senior",
                "role_archetype": "staff_engineer",
            },
            "coord_el": {
                "name": "EL",
                "seniority": "senior",
                "role_archetype": "enablement_lead",
            },
        },
    },
    "database": {"url": "mock://"},
}


def _write_config(tmp_path: Path, data: dict) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


# ---------------------------------------------------------------------------
# CoordinationConfig dataclass defaults
# ---------------------------------------------------------------------------


def test_coordination_config_defaults():
    """CoordinationConfig is disabled by default with sane defaults."""
    cc = CoordinationConfig()
    assert cc.enabled is False
    assert cc.full_loop_cadence == 1
    assert cc.mid_sprint_checkin is True
    assert cc.max_borrows_per_sprint == 2
    assert cc.borrow_duration_sprints == 1
    assert cc.dependency_tracking is True
    assert cc.coordinator_agent_ids == []


def test_experiment_config_coordination_default():
    """ExperimentConfig.coordination defaults to a disabled CoordinationConfig."""
    cfg = ExperimentConfig()
    assert isinstance(cfg.coordination, CoordinationConfig)
    assert cfg.coordination.enabled is False


# ---------------------------------------------------------------------------
# load_config — without coordination
# ---------------------------------------------------------------------------


def test_load_config_without_coordination(tmp_path):
    """Existing configs without coordination: section work unchanged."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert cfg.coordination.enabled is False
    assert cfg.coordination.coordinator_agent_ids == []


# ---------------------------------------------------------------------------
# load_config — with coordination
# ---------------------------------------------------------------------------


def test_load_config_with_coordination(tmp_path):
    """Parses coordination: section correctly."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a", "agent_b"]},
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
        "coordination": {
            "enabled": True,
            "full_loop_cadence": 2,
            "mid_sprint_checkin": False,
            "max_borrows_per_sprint": 3,
            "borrow_duration_sprints": 2,
            "dependency_tracking": False,
            "coordinators": ["coord_se", "coord_el"],
        },
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)

    assert cfg.coordination.enabled is True
    assert cfg.coordination.full_loop_cadence == 2
    assert cfg.coordination.mid_sprint_checkin is False
    assert cfg.coordination.max_borrows_per_sprint == 3
    assert cfg.coordination.borrow_duration_sprints == 2
    assert cfg.coordination.dependency_tracking is False
    assert cfg.coordination.coordinator_agent_ids == ["coord_se", "coord_el"]


def test_coordination_config_custom_values():
    """All CoordinationConfig fields accept custom values."""
    cc = CoordinationConfig(
        enabled=True,
        full_loop_cadence=3,
        mid_sprint_checkin=False,
        max_borrows_per_sprint=5,
        borrow_duration_sprints=2,
        dependency_tracking=False,
        coordinator_agent_ids=["x", "y"],
    )
    assert cc.enabled is True
    assert cc.full_loop_cadence == 3
    assert cc.max_borrows_per_sprint == 5
    assert cc.coordinator_agent_ids == ["x", "y"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_coordination_validates_coordinator_ids(tmp_path):
    """Unknown coordinator agent IDs are rejected."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a", "agent_b"]},
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
        "coordination": {
            "enabled": True,
            "coordinators": ["nonexistent_coordinator"],
        },
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="nonexistent_coordinator"):
        load_config(path)


def test_coordination_validates_coordinators_not_in_teams(tmp_path):
    """Coordinator assigned to a team is rejected."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a", "coord_se"]},
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
        "coordination": {
            "enabled": True,
            "coordinators": ["coord_se"],
        },
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="coord_se"):
        load_config(path)


# ---------------------------------------------------------------------------
# AgentConfig.original_team_id
# ---------------------------------------------------------------------------


def test_agent_config_original_team_id_default():
    """AgentConfig.original_team_id defaults to empty string."""
    cfg = AgentConfig(role_id="x", name="X", model="m", temperature=0.7, max_tokens=100)
    assert cfg.original_team_id == ""


def test_agent_config_original_team_id_set():
    """original_team_id can be set explicitly."""
    cfg = AgentConfig(
        role_id="x",
        name="X",
        model="m",
        temperature=0.7,
        max_tokens=100,
        original_team_id="team-alpha",
    )
    assert cfg.original_team_id == "team-alpha"
