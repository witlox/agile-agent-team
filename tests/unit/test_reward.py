"""Unit tests for RewardCalculator (F-09)."""

import pytest

from src.orchestrator.reward import RewardCalculator, RewardSignal, RewardWeights
from src.orchestrator.phase_runner import PhaseResult


class TestRewardWeights:
    def test_defaults_sum_to_one(self):
        w = RewardWeights()
        total = w.outcome + w.behavioral + w.efficiency + w.phase_completion
        assert abs(total - 1.0) < 1e-9


class TestRewardCalculator:
    def test_perfect_sprint(self):
        calc = RewardCalculator()
        result = calc.compute(
            sprint_result={
                "velocity": 10,
                "test_coverage": 1.0,
                "features_completed": 5,
                "features_planned": 5,
                "pairing_sessions": 3,
            },
            expected_velocity=10,
        )
        assert isinstance(result, RewardSignal)
        assert result.outcome == pytest.approx(1.0, abs=0.01)
        assert result.total > 0.5

    def test_zero_velocity(self):
        calc = RewardCalculator()
        result = calc.compute(
            sprint_result={
                "velocity": 0,
                "test_coverage": 0.0,
                "features_completed": 0,
                "features_planned": 5,
                "pairing_sessions": 0,
            },
            expected_velocity=10,
        )
        assert result.outcome == pytest.approx(0.0, abs=0.01)

    def test_efficiency_penalizes_excessive_sessions(self):
        calc = RewardCalculator()
        # Few sessions = high efficiency
        r_few = calc.compute(
            sprint_result={
                "velocity": 5,
                "test_coverage": 0.5,
                "features_completed": 3,
                "features_planned": 5,
                "pairing_sessions": 2,
            },
            expected_velocity=10,
        )
        # Many sessions = lower efficiency
        r_many = calc.compute(
            sprint_result={
                "velocity": 5,
                "test_coverage": 0.5,
                "features_completed": 3,
                "features_planned": 5,
                "pairing_sessions": 20,
            },
            expected_velocity=10,
        )
        assert r_few.efficiency >= r_many.efficiency

    def test_phase_completion_all_succeed(self):
        calc = RewardCalculator()
        phases = [
            PhaseResult(phase="planning", sprint_num=1, duration_seconds=1.0),
            PhaseResult(phase="development", sprint_num=1, duration_seconds=5.0),
            PhaseResult(phase="qa_review", sprint_num=1, duration_seconds=1.0),
        ]
        result = calc.compute(
            sprint_result={"velocity": 5, "features_completed": 3},
            phase_results=phases,
        )
        assert result.phase_completion == pytest.approx(1.0)

    def test_phase_completion_with_failures(self):
        calc = RewardCalculator()
        phases = [
            PhaseResult(phase="planning", sprint_num=1, duration_seconds=1.0),
            PhaseResult(
                phase="development",
                sprint_num=1,
                duration_seconds=5.0,
                error="timeout",
            ),
        ]
        result = calc.compute(
            sprint_result={"velocity": 5, "features_completed": 3},
            phase_results=phases,
        )
        assert result.phase_completion == pytest.approx(0.5)

    def test_custom_weights(self):
        weights = RewardWeights(
            outcome=0.70,
            behavioral=0.10,
            efficiency=0.10,
            phase_completion=0.10,
        )
        calc = RewardCalculator(weights=weights)
        assert calc.weights.outcome == 0.70

        result = calc.compute(
            sprint_result={
                "velocity": 10,
                "test_coverage": 1.0,
                "features_completed": 5,
                "features_planned": 5,
                "pairing_sessions": 3,
            },
            expected_velocity=10,
        )
        # Higher outcome weight → total dominated by outcome
        assert result.total > 0.5

    def test_behavioral_score_passthrough(self):
        calc = RewardCalculator()
        result = calc.compute(
            sprint_result={"velocity": 5, "features_completed": 3},
            behavioral_score=0.85,
        )
        assert result.behavioral == 0.85
        assert result.total > 0

    def test_compute_phase_reward(self):
        calc = RewardCalculator()
        phase = PhaseResult(
            phase="development",
            sprint_num=1,
            duration_seconds=30.0,
            artifacts={"pairing_sessions": 2},
        )
        result = calc.compute_phase_reward(phase, behavioral_score=0.5)

        assert result.phase_completion == 1.0  # no error
        assert result.behavioral == 0.5
        assert result.total > 0

    def test_compute_phase_reward_with_error(self):
        calc = RewardCalculator()
        phase = PhaseResult(
            phase="development",
            sprint_num=1,
            duration_seconds=30.0,
            error="crash",
        )
        result = calc.compute_phase_reward(phase)

        assert result.phase_completion == 0.0
        assert result.outcome == 0.0
        assert result.efficiency == 0.0

    def test_components_dict(self):
        calc = RewardCalculator()
        result = calc.compute(
            sprint_result={
                "velocity": 8,
                "test_coverage": 0.7,
                "features_completed": 4,
                "features_planned": 5,
                "pairing_sessions": 5,
            },
            expected_velocity=10,
        )
        assert "velocity_ratio" in result.components
        assert "coverage_score" in result.components
        assert "completion_rate" in result.components
