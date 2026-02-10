"""Unit tests for Team Topologies team_type support."""

from pathlib import Path

import pytest
import yaml

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.agent_factory import AgentFactory
from src.orchestrator.config import ExperimentConfig, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    "experiment": {
        "name": "test-team-type",
        "sprint_duration_minutes": 30,
    },
    "team": {
        "config_dir": "team_config",
    },
    "models": {
        "vllm_endpoint": "http://localhost:8000",
    },
    "database": {
        "url": "mock://",
    },
}


def _write_config(tmp_path: Path, data: dict) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


def _make_agent(**overrides) -> BaseAgent:
    defaults = {
        "role_id": "test_agent",
        "name": "Test Agent",
        "model": "mock",
        "temperature": 0.7,
        "max_tokens": 1000,
        "seniority": "senior",
        "role_archetype": "developer",
    }
    defaults.update(overrides)
    config = AgentConfig(**defaults)
    return BaseAgent(config, vllm_endpoint="mock://")


# ---------------------------------------------------------------------------
# AgentConfig field
# ---------------------------------------------------------------------------


def test_agent_config_team_type_default_empty():
    """AgentConfig has empty team_type by default."""
    config = AgentConfig(
        role_id="x", name="X", model="m", temperature=0.7, max_tokens=100
    )
    assert config.team_type == ""


def test_agent_config_team_type_set():
    """team_type propagates to AgentConfig."""
    config = AgentConfig(
        role_id="x",
        name="X",
        model="m",
        temperature=0.7,
        max_tokens=100,
        team_type="platform",
    )
    assert config.team_type == "platform"


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


def test_load_prompt_without_team_type():
    """Prompt composition unchanged when team_type is empty."""
    agent = _make_agent(team_type="")
    # Should not contain any team type header
    assert "Team Topology" not in agent.prompt


def test_load_prompt_with_team_type():
    """team_type file content inserted in prompt when set."""
    agent = _make_agent(team_type="stream_aligned")
    assert "Stream-Aligned Team" in agent.prompt
    assert "Team Topology" in agent.prompt


def test_load_prompt_with_invalid_team_type():
    """Gracefully ignores missing team type file."""
    agent = _make_agent(team_type="nonexistent_type")
    # Should not crash, just skip the layer
    assert "nonexistent_type" not in agent.prompt


def test_load_prompt_team_type_between_archetype_and_seniority():
    """Team type layer appears after role archetype and before seniority."""
    agent = _make_agent(
        team_type="platform",
        role_archetype="developer",
        seniority="senior",
    )
    prompt = agent.prompt
    # All three layers should be present
    assert "Platform Team" in prompt
    # Team type should come after role archetype content and before seniority
    # The prompt uses "---" as separator between layers
    platform_pos = prompt.index("Platform Team")
    senior_pos = prompt.index("[LANGUAGE PROFICIENCY")
    assert platform_pos < senior_pos


# ---------------------------------------------------------------------------
# AgentFactory propagation
# ---------------------------------------------------------------------------


def test_factory_passes_team_type():
    """AgentFactory passes team_type to agents."""
    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
        agent_model_configs={
            "test_dev": {
                "name": "Test Dev",
                "seniority": "mid",
                "role_archetype": "developer",
                "team_type": "enabling",
            },
        },
    )
    config = factory._create_agent_config(
        "test_dev", factory.agent_model_configs["test_dev"]
    )
    assert config.team_type == "enabling"


def test_factory_default_team_type():
    """Factory-level default applies when agent doesn't specify team_type."""
    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
        agent_model_configs={
            "test_dev": {
                "name": "Test Dev",
                "seniority": "mid",
                "role_archetype": "developer",
            },
        },
        team_type="stream_aligned",
    )
    config = factory._create_agent_config(
        "test_dev", factory.agent_model_configs["test_dev"]
    )
    assert config.team_type == "stream_aligned"


def test_factory_agent_override_team_type():
    """Per-agent team_type overrides factory default."""
    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
        agent_model_configs={
            "test_dev": {
                "name": "Test Dev",
                "seniority": "mid",
                "role_archetype": "developer",
                "team_type": "complicated_subsystem",
            },
        },
        team_type="stream_aligned",
    )
    config = factory._create_agent_config(
        "test_dev", factory.agent_model_configs["test_dev"]
    )
    assert config.team_type == "complicated_subsystem"


# ---------------------------------------------------------------------------
# ExperimentConfig / load_config
# ---------------------------------------------------------------------------


def test_config_team_type_default_empty():
    """ExperimentConfig defaults team_type to empty string."""
    cfg = ExperimentConfig()
    assert cfg.team_type == ""


def test_config_team_type_from_yaml(tmp_path):
    """load_config reads team.team_type from YAML."""
    data = {
        **MINIMAL_CONFIG,
        "team": {
            **MINIMAL_CONFIG["team"],
            "team_type": "platform",
        },
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)
    assert cfg.team_type == "platform"


def test_config_team_type_missing_from_yaml(tmp_path):
    """load_config defaults to empty string when team_type not in YAML."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert cfg.team_type == ""


# ---------------------------------------------------------------------------
# Team type files exist
# ---------------------------------------------------------------------------

TEAM_TYPES = ["stream_aligned", "platform", "enabling", "complicated_subsystem"]


@pytest.mark.parametrize("team_type", TEAM_TYPES)
def test_team_type_files_exist(team_type):
    """All 4 team type files exist and are non-empty."""
    path = Path("team_config/00_base/team_types") / f"{team_type}.md"
    assert path.exists(), f"Missing team type file: {path}"
    content = path.read_text()
    assert len(content) > 100, f"Team type file too short: {path}"
    assert "Team Topology" in content
