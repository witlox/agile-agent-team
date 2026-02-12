"""Unit tests for ScenarioCatalog (F-10)."""

import pytest

from src.orchestrator.scenario_catalog import (
    EPISODE_TYPES,
    ScenarioCatalog,
    ScenarioConfig,
)


class TestEpisodeTypes:
    def test_thirteen_types_defined(self):
        assert len(EPISODE_TYPES) == 13

    def test_all_types_have_required_fields(self):
        required = {
            "stage",
            "phases",
            "target_behaviors",
            "duration_minutes",
            "description",
        }
        for name, info in EPISODE_TYPES.items():
            missing = required - set(info.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_stages_1_through_4(self):
        stages = {info["stage"] for info in EPISODE_TYPES.values()}
        assert stages == {1, 2, 3, 4}


class TestScenarioCatalog:
    def test_list_all_episode_types(self):
        catalog = ScenarioCatalog()
        types = catalog.list_episode_types()
        assert len(types) == 13
        assert "implementation" in types
        assert "recovery" in types

    def test_list_episode_types_by_stage(self):
        catalog = ScenarioCatalog()
        stage1 = catalog.list_episode_types(stage=1)
        assert "elicitation" in stage1
        assert "decomposition" in stage1
        assert "implementation" in stage1
        assert "self_monitoring" in stage1
        # Stage 2 types should not be in stage 1
        assert "recovery" not in stage1

    def test_list_stage_4(self):
        catalog = ScenarioCatalog()
        stage4 = catalog.list_episode_types(stage=4)
        assert "onboarding_support" in stage4
        assert "compensation" in stage4
        assert len(stage4) == 2

    def test_generate_basic(self):
        catalog = ScenarioCatalog()
        scenario = catalog.generate("implementation", difficulty=0.5)
        assert isinstance(scenario, ScenarioConfig)
        assert scenario.episode_type == "implementation"
        assert scenario.stage == 1
        assert scenario.difficulty == 0.5
        assert "development" in scenario.phases
        assert len(scenario.expected_behaviors) > 0

    def test_generate_unknown_type_raises(self):
        catalog = ScenarioCatalog()
        with pytest.raises(ValueError, match="Unknown episode type"):
            catalog.generate("nonexistent_episode")

    def test_difficulty_affects_stories(self):
        catalog = ScenarioCatalog()
        easy = catalog.generate("implementation", difficulty=0.0, seed=42)
        hard = catalog.generate("implementation", difficulty=1.0, seed=42)
        # Higher difficulty should produce more stories
        assert len(hard.backlog_stories) >= len(easy.backlog_stories)

    def test_seed_deterministic(self):
        catalog = ScenarioCatalog()
        s1 = catalog.generate("implementation", difficulty=0.5, seed=123)
        s2 = catalog.generate("implementation", difficulty=0.5, seed=123)
        assert s1.backlog_stories == s2.backlog_stories

    def test_target_slot_in_overrides(self):
        catalog = ScenarioCatalog()
        scenario = catalog.generate(
            "implementation",
            target_slot="dev_mid_backend",
        )
        assert "dev_mid_backend" in scenario.agent_overrides
        assert scenario.target_agent_slot == "dev_mid_backend"

    def test_generate_curriculum(self):
        catalog = ScenarioCatalog()
        scenarios = catalog.generate_curriculum(stage=1, num_episodes=10, seed=42)
        assert len(scenarios) == 10
        for s in scenarios:
            assert s.stage == 1

    def test_generate_curriculum_empty_stage(self):
        catalog = ScenarioCatalog()
        scenarios = catalog.generate_curriculum(stage=99, num_episodes=5)
        assert scenarios == []

    def test_disturbances_at_high_difficulty(self):
        catalog = ScenarioCatalog()
        scenario = catalog.generate("recovery", difficulty=0.9, seed=42)
        assert scenario.disturbance_overrides.get("enabled") is True
        assert len(scenario.disturbance_overrides.get("frequencies", {})) > 0

    def test_disturbances_at_low_difficulty(self):
        catalog = ScenarioCatalog()
        scenario = catalog.generate("implementation", difficulty=0.1, seed=42)
        assert scenario.disturbance_overrides.get("enabled") is False

    def test_stories_from_pool(self, tmp_path):
        """When a backlog_path is provided, stories come from the pool."""
        backlog = tmp_path / "backlog.yaml"
        backlog.write_text(
            "stories:\n"
            "  - id: US-01\n"
            "    title: Pool Story 1\n"
            "    description: From pool\n"
            "    story_points: 3\n"
            "  - id: US-02\n"
            "    title: Pool Story 2\n"
            "    description: From pool\n"
            "    story_points: 5\n"
        )
        catalog = ScenarioCatalog(backlog_path=str(backlog))
        scenario = catalog.generate("implementation", difficulty=0.3, seed=42)
        assert any(s["id"] in ("US-01", "US-02") for s in scenario.backlog_stories)
