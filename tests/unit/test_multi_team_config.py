"""Unit tests for multi-team configuration and data models."""

from pathlib import Path

import pytest
import yaml

from src.agents.base_agent import AgentConfig
from src.agents.agent_factory import AgentFactory
from src.orchestrator.backlog import Backlog
from src.orchestrator.config import ExperimentConfig, TeamConfig, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    "experiment": {
        "name": "test-multi-team",
        "sprint_duration_minutes": 30,
    },
    "team": {
        "config_dir": "team_config",
    },
    "models": {
        "vllm_endpoint": "http://localhost:8000",
        "agents": {
            "agent_a": {
                "name": "Agent A",
                "seniority": "senior",
                "role_archetype": "developer",
            },
            "agent_b": {
                "name": "Agent B",
                "seniority": "mid",
                "role_archetype": "developer",
            },
            "agent_c": {
                "name": "Agent C",
                "seniority": "junior",
                "role_archetype": "developer",
            },
            "agent_d": {
                "name": "Agent D",
                "seniority": "senior",
                "role_archetype": "tester",
            },
        },
    },
    "database": {
        "url": "mock://",
    },
}


def _write_config(tmp_path: Path, data: dict) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


# ---------------------------------------------------------------------------
# TeamConfig dataclass
# ---------------------------------------------------------------------------


def test_team_config_defaults():
    """TeamConfig has sane defaults."""
    tc = TeamConfig(id="my-team")
    assert tc.id == "my-team"
    assert tc.name == ""
    assert tc.team_type == ""
    assert tc.agent_ids == []
    assert tc.backlog_path == ""
    assert tc.wip_limits is None


def test_team_config_full():
    """TeamConfig stores all fields."""
    tc = TeamConfig(
        id="stream-a",
        name="Stream A",
        team_type="stream_aligned",
        agent_ids=["a1", "a2"],
        backlog_path="backlogs/a.yaml",
        wip_limits={"in_progress": 3},
    )
    assert tc.id == "stream-a"
    assert tc.name == "Stream A"
    assert tc.team_type == "stream_aligned"
    assert tc.agent_ids == ["a1", "a2"]
    assert tc.backlog_path == "backlogs/a.yaml"
    assert tc.wip_limits == {"in_progress": 3}


# ---------------------------------------------------------------------------
# ExperimentConfig.teams
# ---------------------------------------------------------------------------


def test_experiment_config_teams_default_empty():
    """ExperimentConfig.teams defaults to empty list."""
    cfg = ExperimentConfig()
    assert cfg.teams == []


# ---------------------------------------------------------------------------
# load_config — without teams
# ---------------------------------------------------------------------------


def test_load_config_without_teams(tmp_path):
    """Existing configs without teams: section work unchanged."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert cfg.teams == []


# ---------------------------------------------------------------------------
# load_config — with teams
# ---------------------------------------------------------------------------


def test_load_config_with_teams(tmp_path):
    """Parses teams: section correctly."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {
                "id": "team-alpha",
                "name": "Alpha",
                "team_type": "stream_aligned",
                "agents": ["agent_a", "agent_b"],
            },
            {
                "id": "team-beta",
                "name": "Beta",
                "team_type": "platform",
                "agents": ["agent_c", "agent_d"],
                "backlog": "backlogs/beta.yaml",
                "wip_limits": {"in_progress": 2, "review": 1},
            },
        ],
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)

    assert len(cfg.teams) == 2
    assert cfg.teams[0].id == "team-alpha"
    assert cfg.teams[0].agent_ids == ["agent_a", "agent_b"]
    assert cfg.teams[1].wip_limits == {"in_progress": 2, "review": 1}


def test_load_config_team_inherits_global_team_type(tmp_path):
    """Team without team_type falls back to global team.team_type."""
    data = {
        **MINIMAL_CONFIG,
        "team": {
            **MINIMAL_CONFIG["team"],
            "team_type": "enabling",
        },
        "teams": [
            {"id": "t1", "agents": ["agent_a", "agent_b"]},
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)
    assert cfg.teams[0].team_type == "enabling"
    assert cfg.teams[1].team_type == "enabling"


def test_load_config_team_overrides_team_type(tmp_path):
    """Per-team team_type overrides global default."""
    data = {
        **MINIMAL_CONFIG,
        "team": {
            **MINIMAL_CONFIG["team"],
            "team_type": "stream_aligned",
        },
        "teams": [
            {
                "id": "t1",
                "team_type": "platform",
                "agents": ["agent_a", "agent_b"],
            },
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)
    assert cfg.teams[0].team_type == "platform"
    assert cfg.teams[1].team_type == "stream_aligned"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_load_config_validates_agent_ids(tmp_path):
    """Unknown agent_ids are rejected."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a", "nonexistent_agent"]},
            {"id": "t2", "agents": ["agent_c", "agent_d"]},
        ],
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="nonexistent_agent"):
        load_config(path)


def test_load_config_validates_no_duplicate_agents(tmp_path):
    """Agent assigned to two teams is rejected."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a", "agent_b"]},
            {"id": "t2", "agents": ["agent_b", "agent_c"]},
        ],
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="agent_b"):
        load_config(path)


def test_load_config_validates_team_count_too_few(tmp_path):
    """Single team raises (minimum is 2)."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [
            {"id": "t1", "agents": ["agent_a"]},
        ],
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="2-7 teams"):
        load_config(path)


def test_load_config_validates_team_count_too_many(tmp_path):
    """More than 7 teams raises."""
    data = {
        **MINIMAL_CONFIG,
        "teams": [{"id": f"t{i}", "agents": []} for i in range(8)],
    }
    path = _write_config(tmp_path, data)
    with pytest.raises(ValueError, match="at most 7"):
        load_config(path)


# ---------------------------------------------------------------------------
# AgentConfig.team_id
# ---------------------------------------------------------------------------


def test_agent_config_team_id_default():
    """AgentConfig.team_id defaults to empty string."""
    cfg = AgentConfig(role_id="x", name="X", model="m", temperature=0.7, max_tokens=100)
    assert cfg.team_id == ""


def test_agent_config_team_id_set():
    """team_id propagates through AgentConfig."""
    cfg = AgentConfig(
        role_id="x",
        name="X",
        model="m",
        temperature=0.7,
        max_tokens=100,
        team_id="checkout-stream",
    )
    assert cfg.team_id == "checkout-stream"


def test_factory_passes_team_id():
    """AgentFactory passes team_id to AgentConfig."""
    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
        agent_model_configs={
            "test_dev": {
                "name": "Test Dev",
                "seniority": "mid",
                "role_archetype": "developer",
                "team_id": "platform-team",
            },
        },
    )
    config = factory._create_agent_config(
        "test_dev", factory.agent_model_configs["test_dev"]
    )
    assert config.team_id == "platform-team"


# ---------------------------------------------------------------------------
# Backlog.from_stories
# ---------------------------------------------------------------------------


def test_backlog_from_stories():
    """Backlog.from_stories creates a valid Backlog without a file."""
    stories = [
        {"id": "US-001", "title": "Story 1", "priority": 1, "story_points": 3},
        {"id": "US-002", "title": "Story 2", "priority": 2, "story_points": 5},
    ]
    bl = Backlog.from_stories(stories, product_name="Test", product_description="Desc")
    assert bl.product_name == "Test"
    assert bl.product_description == "Desc"
    assert bl.remaining == 2

    selected = bl.next_stories(1)
    assert len(selected) == 1
    assert selected[0]["id"] == "US-001"
    assert bl.remaining == 1


def test_backlog_from_stories_empty():
    """Backlog.from_stories with empty list."""
    bl = Backlog.from_stories([])
    assert bl.remaining == 0
    assert bl.next_stories(5) == []
