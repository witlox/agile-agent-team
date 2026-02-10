"""Unit tests for ExperimentConfig and load_config."""

import pytest
import yaml

from src.orchestrator.config import ExperimentConfig, load_config


MINIMAL_CONFIG = {
    "experiment": {
        "name": "test-experiment",
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


FULL_CONFIG = {
    **MINIMAL_CONFIG,
    "experiment": {
        **MINIMAL_CONFIG["experiment"],
        "sprints_per_stakeholder_review": 3,
    },
    "disturbances": {
        "enabled": True,
        "frequencies": {"flaky_test": 0.25, "scope_creep": 0.20},
        "blast_radius_controls": {"max_velocity_impact": 0.30},
    },
    "profile_swapping": {
        "mode": "constrained",
        "allowed_scenarios": ["critical_production_incident"],
        "penalties": {"context_switch_slowdown": 1.20},
    },
    "runtimes": {
        "anthropic": {"enabled": True, "api_key_env": "ANTHROPIC_API_KEY"},
    },
    "remote_git": {
        "enabled": True,
        "provider": "github",
        "github": {"token_env": "GITHUB_TOKEN"},
    },
    "sprint_zero": {
        "enabled": False,
    },
}


def _write_config(tmp_path, data):
    """Write a YAML config dict to a temp file and return its path."""
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------


def test_load_config_minimal(tmp_path):
    """Minimal YAML produces ExperimentConfig with defaults."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert isinstance(cfg, ExperimentConfig)
    assert cfg.name == "test-experiment"
    assert cfg.sprint_duration_minutes == 30
    assert cfg.database_url == "mock://"
    # Defaults
    assert cfg.disturbances_enabled is False
    assert cfg.profile_swap_mode == "none"
    assert cfg.sprint_zero_enabled is True


def test_load_config_full(tmp_path):
    """Full YAML with all sections populates every field."""
    path = _write_config(tmp_path, FULL_CONFIG)
    cfg = load_config(path)
    assert cfg.disturbances_enabled is True
    assert cfg.disturbance_frequencies["flaky_test"] == 0.25
    assert cfg.blast_radius_controls["max_velocity_impact"] == 0.30
    assert cfg.profile_swap_mode == "constrained"
    assert "critical_production_incident" in cfg.profile_swap_scenarios
    assert cfg.profile_swap_penalties["context_switch_slowdown"] == 1.20
    assert cfg.remote_git_enabled is True
    assert cfg.remote_git_provider == "github"
    assert cfg.sprint_zero_enabled is False


def test_load_config_missing_file(tmp_path):
    """Nonexistent path raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nonexistent.yaml"))


def test_load_config_disturbances(tmp_path):
    """Disturbance settings are correctly parsed."""
    path = _write_config(tmp_path, FULL_CONFIG)
    cfg = load_config(path)
    assert cfg.disturbances_enabled is True
    assert "scope_creep" in cfg.disturbance_frequencies
    assert cfg.disturbance_frequencies["scope_creep"] == 0.20


def test_load_config_runtimes(tmp_path):
    """Runtime config is correctly parsed."""
    path = _write_config(tmp_path, FULL_CONFIG)
    cfg = load_config(path)
    assert "anthropic" in cfg.runtime_configs
    assert cfg.runtime_configs["anthropic"]["enabled"] is True


def test_load_config_database_url_override(tmp_path):
    """database_url argument overrides YAML value."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path, database_url="postgresql://override:5432/db")
    assert cfg.database_url == "postgresql://override:5432/db"
