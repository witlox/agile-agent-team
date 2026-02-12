"""Unit tests for ExperimentConfigBuilder and ExperimentConfig.from_dict (F-05)."""


from src.orchestrator.config import ExperimentConfig, load_config
from src.orchestrator.config_builder import ExperimentConfigBuilder


class TestExperimentConfigBuilder:
    """Tests for the fluent config builder."""

    def test_minimal_build(self):
        """Minimal config (just name + database_url) builds without error."""
        config = (
            ExperimentConfigBuilder()
            .name("test-experiment")
            .database_url("mock://")
            .build()
        )
        assert isinstance(config, ExperimentConfig)
        assert config.name == "test-experiment"
        assert config.database_url == "mock://"

    def test_defaults_filled(self):
        """Missing values get sensible defaults."""
        config = ExperimentConfigBuilder().database_url("mock://").build()
        assert config.sprint_duration_minutes == 60
        assert config.wip_limits == {"in_progress": 4, "review": 2}
        assert config.disturbances_enabled is False
        assert config.tracing_enabled is False
        assert config.profile_swap_mode == "none"

    def test_sprint_duration(self):
        config = (
            ExperimentConfigBuilder()
            .name("fast")
            .sprint_duration(5)
            .database_url("mock://")
            .build()
        )
        assert config.sprint_duration_minutes == 5

    def test_agents_config(self):
        agents = {
            "dev_lead": {"name": "Lead", "model": "mock", "runtime": "mock"},
            "dev_mid": {"name": "Mid Dev", "model": "mock", "runtime": "mock"},
        }
        config = (
            ExperimentConfigBuilder()
            .name("agents-test")
            .database_url("mock://")
            .agents(agents)
            .build()
        )
        assert "dev_lead" in config.agent_configs
        assert "dev_mid" in config.agent_configs
        assert config.agent_configs["dev_lead"]["name"] == "Lead"

    def test_tracing_enabled(self):
        config = (
            ExperimentConfigBuilder()
            .name("traced")
            .database_url("mock://")
            .tracing(True)
            .build()
        )
        assert config.tracing_enabled is True

    def test_disturbances(self):
        config = (
            ExperimentConfigBuilder()
            .name("disturbed")
            .database_url("mock://")
            .disturbances(
                enabled=True,
                frequencies={"flaky_test": 0.3, "scope_creep": 0.1},
            )
            .build()
        )
        assert config.disturbances_enabled is True
        assert config.disturbance_frequencies["flaky_test"] == 0.3

    def test_attrition(self):
        config = (
            ExperimentConfigBuilder()
            .name("attrition-test")
            .database_url("mock://")
            .attrition(enabled=True, probability_per_sprint=0.1)
            .build()
        )
        assert config.attrition.enabled is True
        assert config.attrition.probability_per_sprint == 0.1

    def test_onboarding(self):
        config = (
            ExperimentConfigBuilder()
            .name("onboarding-test")
            .database_url("mock://")
            .onboarding(duration_sprints=3, max_story_points_first_sprint=2)
            .build()
        )
        assert config.onboarding.onboarding_duration_sprints == 3
        assert config.onboarding.max_story_points_first_sprint == 2

    def test_profile_swapping(self):
        config = (
            ExperimentConfigBuilder()
            .name("swap-test")
            .database_url("mock://")
            .profile_swapping(
                mode="constrained",
                allowed_scenarios=["production_incident"],
                penalties={"proficiency_reduction": 0.7},
            )
            .build()
        )
        assert config.profile_swap_mode == "constrained"
        assert "production_incident" in config.profile_swap_scenarios
        assert config.profile_swap_penalties["proficiency_reduction"] == 0.7

    def test_workspace(self):
        config = (
            ExperimentConfigBuilder()
            .name("ws-test")
            .database_url("mock://")
            .workspace(root="/tmp/custom-workspace", mode="per_sprint")
            .build()
        )
        assert config.tools_workspace_root == "/tmp/custom-workspace"
        assert config.workspace_mode == "per_sprint"

    def test_chaining(self):
        """All builder methods return self for chaining."""
        builder = ExperimentConfigBuilder()
        result = (
            builder.name("chain")
            .sprint_duration(10)
            .database_url("mock://")
            .tracing(True)
            .disturbances(enabled=True)
            .attrition(enabled=False)
            .onboarding(duration_sprints=1)
            .profile_swapping(mode="free")
            .workspace(root="/tmp/ws")
            .num_simulated_days(3)
        )
        assert result is builder


class TestFromDict:
    """Tests for ExperimentConfig.from_dict classmethod."""

    def test_minimal_dict(self):
        data = {
            "database": {"url": "mock://"},
        }
        config = ExperimentConfig.from_dict(data)
        assert config.database_url == "mock://"
        assert config.name == ""
        assert config.sprint_duration_minutes == 60

    def test_database_url_override(self):
        data = {"database": {"url": "postgresql://host/db"}}
        config = ExperimentConfig.from_dict(data, database_url="mock://")
        assert config.database_url == "mock://"

    def test_full_dict(self):
        data = {
            "experiment": {"name": "full-test", "sprint_duration_minutes": 30},
            "database": {"url": "mock://"},
            "team": {"config_dir": "team_config"},
            "models": {
                "vllm_endpoint": "http://localhost:8000",
                "agents": {
                    "dev_a": {"name": "Dev A", "model": "mock", "runtime": "mock"},
                },
            },
            "disturbances": {"enabled": True, "frequencies": {"flaky_test": 0.5}},
        }
        config = ExperimentConfig.from_dict(data)
        assert config.name == "full-test"
        assert config.sprint_duration_minutes == 30
        assert config.disturbances_enabled is True
        assert config.disturbance_frequencies["flaky_test"] == 0.5
        assert "dev_a" in config.agent_configs

    def test_from_dict_matches_load_config(self, tmp_path):
        """from_dict produces equivalent config to load_config for same input."""
        yaml_content = """\
experiment:
  name: roundtrip
  sprint_duration_minutes: 45
database:
  url: mock://
team:
  config_dir: team_config
models:
  vllm_endpoint: ""
  agents:
    dev_a:
      name: Dev A
      model: mock
      runtime: mock
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        loaded = load_config(str(config_file))
        import yaml

        with open(config_file) as f:
            data = yaml.safe_load(f)
        from_dict = ExperimentConfig.from_dict(data)

        assert loaded.name == from_dict.name
        assert loaded.sprint_duration_minutes == from_dict.sprint_duration_minutes
        assert loaded.database_url == from_dict.database_url
        assert loaded.agent_configs == from_dict.agent_configs
