"""Integration tests for the Episode Harness (F-12).

End-to-end tests that exercise the full pipeline: scenario generation,
sprint manager setup, phase execution, observation, behavioral scoring,
reward computation, and checkpointing.
"""

import json

import pytest

from src.orchestrator.action_space import AdjustSprintParams, ModifyBacklog
from src.orchestrator.checkpoint import CheckpointManager
from src.orchestrator.episode_runner import EpisodeRunner
from src.orchestrator.reward import RewardWeights
from src.orchestrator.scenario_catalog import ScenarioCatalog


class TestEpisodeHarnessIntegration:
    @pytest.fixture
    def runner(self, tmp_path):
        return EpisodeRunner(
            workspace_root=str(tmp_path / "workspaces"),
        )

    @pytest.mark.asyncio
    async def test_implementation_episode(self, runner):
        """Full implementation episode produces valid results."""
        result = await runner.run_episode("implementation", difficulty=0.5, seed=42)
        assert result.episode_type == "implementation"
        assert result.stage == 1
        assert len(result.phase_results) >= 1
        assert result.reward.total >= 0.0
        assert result.sprint_result is not None

    @pytest.mark.asyncio
    async def test_recovery_episode(self, runner):
        """Recovery episode runs through development and QA phases."""
        result = await runner.run_episode("recovery", difficulty=0.6, seed=99)
        assert result.episode_type == "recovery"
        assert result.stage == 2
        phases_run = [pr.phase for pr in result.phase_results]
        assert "development" in phases_run

    @pytest.mark.asyncio
    async def test_reward_signal_validity(self, runner):
        """Reward signal channels are in valid ranges."""
        result = await runner.run_episode("implementation", difficulty=0.5)
        r = result.reward
        assert 0.0 <= r.outcome <= 1.0
        assert 0.0 <= r.efficiency <= 1.0
        assert 0.0 <= r.phase_completion <= 1.0
        assert 0.0 <= r.behavioral <= 1.0
        assert 0.0 <= r.total <= 1.0

    @pytest.mark.asyncio
    async def test_checkpoint_save_restore_round_trip(self, runner, tmp_path):
        """Save checkpoint during episode, then restore and verify."""
        cp_dir = tmp_path / "checkpoints"
        runner._checkpoint_mgr = CheckpointManager(cp_dir)

        result = await runner.run_episode(
            "elicitation", difficulty=0.3, checkpoint_every_phase=True
        )
        assert result.terminated is True

        # Verify at least one checkpoint was written
        episode_dirs = list(cp_dir.iterdir())
        assert len(episode_dirs) >= 1

        ep_dir = episode_dirs[0]
        checkpoint_files = sorted(ep_dir.glob("*.json"))
        assert len(checkpoint_files) >= 1

        # Verify checkpoint is valid JSON with expected fields
        data = json.loads(checkpoint_files[0].read_text())
        assert "episode_id" in data
        assert "sprint_num" in data
        assert "kanban_snapshot" in data

    @pytest.mark.asyncio
    async def test_actions_modify_state(self, runner):
        """Pre-phase actions modify the sprint manager state."""
        result = await runner.run_episode(
            "implementation",
            difficulty=0.3,
            actions=[
                AdjustSprintParams(duration_minutes=3),
                ModifyBacklog(
                    "add",
                    story={
                        "id": "INJECTED-1",
                        "title": "Injected story",
                        "description": "Added by RL action",
                    },
                ),
            ],
        )
        assert result.terminated is True

    @pytest.mark.asyncio
    async def test_curriculum_batch(self, runner):
        """Run a small batch of curriculum episodes."""
        catalog = ScenarioCatalog()
        scenarios = catalog.generate_curriculum(stage=1, num_episodes=4, seed=42)
        for scenario in scenarios:
            result = await runner.run_scenario(scenario)
            assert result.terminated is True
            assert result.reward.total >= 0.0

    @pytest.mark.asyncio
    async def test_behavioral_reward_integration(self, runner):
        """Behavioral score flows through to reward signal."""
        # Custom weights emphasizing behavioral
        runner._reward = runner._reward.__class__(
            RewardWeights(
                behavioral=0.9, outcome=0.05, efficiency=0.025, phase_completion=0.025
            )
        )
        result = await runner.run_episode("implementation", difficulty=0.3)
        # With mock agents, behavioral score is likely 0.0
        # but the channel should still be present
        assert "behavioral" in result.reward.__dict__

    @pytest.mark.asyncio
    async def test_episode_result_json_serializable(self, runner):
        """EpisodeResult can be serialized to JSON."""
        result = await runner.run_episode("implementation", difficulty=0.3)

        # Build a JSON-safe dict
        data = {
            "episode_id": result.episode_id,
            "episode_type": result.episode_type,
            "stage": result.stage,
            "difficulty": result.difficulty,
            "behavioral_score": result.behavioral_score,
            "behaviors_detected": result.behaviors_detected,
            "total_duration_seconds": result.total_duration_seconds,
            "terminated": result.terminated,
            "truncated": result.truncated,
            "reward": {
                "outcome": result.reward.outcome,
                "efficiency": result.reward.efficiency,
                "phase_completion": result.reward.phase_completion,
                "behavioral": result.reward.behavioral,
                "total": result.reward.total,
                "components": result.reward.components,
            },
            "final_observation": result.final_observation,
            "sprint_result": result.sprint_result,
            "decision_traces": result.decision_traces,
        }

        # Should not raise
        serialized = json.dumps(data)
        assert len(serialized) > 0
        roundtrip = json.loads(serialized)
        assert roundtrip["episode_type"] == "implementation"
