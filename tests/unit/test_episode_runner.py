"""Unit tests for Episode Runner (F-12)."""


import pytest

from src.orchestrator.episode_runner import EpisodeResult, EpisodeRunner
from src.orchestrator.reward import RewardSignal
from src.orchestrator.scenario_catalog import (
    EPISODE_TYPES,
    ScenarioCatalog,
)


class TestEpisodeResult:
    def test_dataclass_fields(self):
        result = EpisodeResult(
            episode_id="ep-001",
            episode_type="implementation",
            stage=1,
            difficulty=0.5,
            phase_results=[],
            final_observation={},
            reward=RewardSignal(
                outcome=0.5,
                efficiency=0.5,
                phase_completion=1.0,
                behavioral=0.5,
                total=0.5,
            ),
            behavioral_score=0.5,
            behaviors_detected=["B-07"],
            decision_traces={},
        )
        assert result.episode_id == "ep-001"
        assert result.episode_type == "implementation"
        assert result.terminated is True
        assert result.truncated is False
        assert result.total_duration_seconds == 0.0

    def test_optional_sprint_result(self):
        result = EpisodeResult(
            episode_id="ep-002",
            episode_type="recovery",
            stage=2,
            difficulty=0.8,
            phase_results=[],
            final_observation={},
            reward=RewardSignal(
                outcome=0.0,
                efficiency=0.0,
                phase_completion=0.0,
                behavioral=0.0,
                total=0.0,
            ),
            behavioral_score=0.0,
            behaviors_detected=[],
            decision_traces={},
            sprint_result={"sprint": 1, "velocity": 5},
        )
        assert result.sprint_result is not None


class TestEpisodeRunner:
    @pytest.fixture
    def runner(self, tmp_path):
        return EpisodeRunner(
            workspace_root=str(tmp_path / "episodes"),
        )

    @pytest.mark.asyncio
    async def test_run_episode_basic(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        assert result.episode_type == "implementation"
        assert result.stage == 1
        assert result.difficulty == 0.5
        assert result.episode_id.startswith("ep-")
        assert result.total_duration_seconds > 0

    @pytest.mark.asyncio
    async def test_run_episode_has_phase_results(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        assert len(result.phase_results) >= 1
        assert result.phase_results[0].phase == "development"

    @pytest.mark.asyncio
    async def test_run_episode_observation_extracted(self, runner):
        result = await runner.run_episode("elicitation", difficulty=0.3)
        assert "sprint_num" in result.final_observation
        assert "agents" in result.final_observation

    @pytest.mark.asyncio
    async def test_run_episode_reward_computed(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        reward = result.reward
        assert isinstance(reward, RewardSignal)
        assert 0.0 <= reward.total <= 1.0
        assert "velocity_ratio" in reward.components

    @pytest.mark.asyncio
    async def test_run_episode_behavioral_score_present(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        assert isinstance(result.behavioral_score, float)
        assert 0.0 <= result.behavioral_score <= 1.0

    @pytest.mark.asyncio
    async def test_run_episode_decision_traces_present(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        assert isinstance(result.decision_traces, dict)

    @pytest.mark.asyncio
    async def test_run_episode_sprint_result(self, runner):
        result = await runner.run_episode("implementation", difficulty=0.5)
        sr = result.sprint_result
        assert sr is not None
        assert "velocity" in sr
        assert "features_planned" in sr

    @pytest.mark.asyncio
    async def test_seed_determinism(self, runner):
        r1 = await runner.run_episode("implementation", difficulty=0.5, seed=42)
        r2 = await runner.run_episode("implementation", difficulty=0.5, seed=42)
        assert r1.episode_type == r2.episode_type
        assert r1.stage == r2.stage
        # Phase count should match
        assert len(r1.phase_results) == len(r2.phase_results)

    @pytest.mark.asyncio
    async def test_run_from_catalog(self, runner):
        catalog = ScenarioCatalog()
        scenario = catalog.generate("recovery", difficulty=0.6, seed=123)
        result = await runner.run_scenario(scenario)
        assert result.episode_type == "recovery"
        assert result.stage == 2

    @pytest.mark.asyncio
    async def test_run_with_actions(self, runner):
        from src.orchestrator.action_space import AdjustSprintParams

        result = await runner.run_episode(
            "implementation",
            difficulty=0.3,
            actions=[AdjustSprintParams(duration_minutes=5)],
        )
        assert result.terminated is True

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, runner, tmp_path):
        from src.orchestrator.checkpoint import CheckpointManager

        cp_dir = tmp_path / "checkpoints"
        runner._checkpoint_mgr = CheckpointManager(cp_dir)
        result = await runner.run_episode(
            "implementation",
            difficulty=0.3,
            checkpoint_every_phase=True,
        )
        # Checkpoints should exist
        assert result.terminated is True
        episode_dirs = list(cp_dir.iterdir())
        assert len(episode_dirs) >= 1

    @pytest.mark.asyncio
    async def test_all_episode_types_runnable(self, runner):
        """All 13 episode types can be run without error."""
        for ep_type in EPISODE_TYPES:
            result = await runner.run_episode(ep_type, difficulty=0.3)
            assert result.episode_type == ep_type
            assert result.terminated is True
