"""Reward signal computation for RL environment integration.

Computes multi-channel reward signals from sprint/phase data.
Dojo implements its own judge for behavioral rewards, but AAT provides
the outcome/efficiency/completion channels.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .phase_runner import PhaseResult


@dataclass
class RewardWeights:
    """Configurable channel weights."""

    outcome: float = 0.40
    behavioral: float = 0.30
    efficiency: float = 0.15
    phase_completion: float = 0.15


@dataclass
class RewardSignal:
    """Multi-channel reward signal for RL."""

    outcome: float
    efficiency: float
    phase_completion: float
    behavioral: float
    total: float
    components: Dict[str, float] = field(default_factory=dict)


class RewardCalculator:
    """Computes reward signals from AAT sprint data.

    Outcome reward:
        - velocity_ratio = actual_velocity / expected_velocity
        - coverage_score = test_coverage (0-1)
        - completion_rate = features_completed / features_planned
        - outcome = 0.4 * velocity_ratio + 0.3 * coverage_score
                    + 0.3 * completion_rate

    Efficiency reward:
        - Based on pairing sessions vs features completed
        - efficiency = 1.0 - (actual_sessions / max_sessions) * penalty

    Phase completion reward:
        - Binary per phase (did it succeed?), averaged.
    """

    def __init__(self, weights: Optional[RewardWeights] = None) -> None:
        self._weights = weights or RewardWeights()

    @property
    def weights(self) -> RewardWeights:
        """Current reward weights."""
        return self._weights

    def compute(
        self,
        sprint_result: Dict[str, Any],
        phase_results: Optional[List["PhaseResult"]] = None,
        expected_velocity: int = 10,
        behavioral_score: float = 0.0,
    ) -> RewardSignal:
        """Compute reward from a full sprint result.

        Args:
            sprint_result: Dict with velocity, features_completed,
                test_coverage, pairing_sessions keys.
            phase_results: Optional list of PhaseResult for completion scoring.
            expected_velocity: Target velocity for ratio calculation.
            behavioral_score: External behavioral score (0-1) from dojo's judge.

        Returns:
            RewardSignal with per-channel and total scores.
        """
        # Outcome
        velocity = sprint_result.get("velocity", 0)
        coverage = sprint_result.get("test_coverage", 0.0)
        features = sprint_result.get("features_completed", 0)
        features_planned = max(sprint_result.get("features_planned", features), 1)

        velocity_ratio = min(velocity / max(expected_velocity, 1), 1.0)
        completion_rate = min(features / max(features_planned, 1), 1.0)
        coverage_score = min(max(coverage, 0.0), 1.0)

        outcome = 0.4 * velocity_ratio + 0.3 * coverage_score + 0.3 * completion_rate

        # Efficiency
        sessions = sprint_result.get("pairing_sessions", 0)
        max_sessions = max(features_planned * 3, 1)  # heuristic cap
        efficiency = max(1.0 - (sessions / max_sessions) * 0.5, 0.0)
        efficiency = min(efficiency, 1.0)

        # Phase completion
        phase_completion = self._compute_phase_completion(phase_results)

        # Total
        w = self._weights
        total = (
            w.outcome * outcome
            + w.behavioral * behavioral_score
            + w.efficiency * efficiency
            + w.phase_completion * phase_completion
        )

        return RewardSignal(
            outcome=round(outcome, 4),
            efficiency=round(efficiency, 4),
            phase_completion=round(phase_completion, 4),
            behavioral=round(behavioral_score, 4),
            total=round(total, 4),
            components={
                "velocity_ratio": round(velocity_ratio, 4),
                "coverage_score": round(coverage_score, 4),
                "completion_rate": round(completion_rate, 4),
                "sessions_ratio": round(sessions / max_sessions, 4),
            },
        )

    def compute_phase_reward(
        self,
        phase_result: "PhaseResult",
        behavioral_score: float = 0.0,
    ) -> RewardSignal:
        """Compute reward for a single phase (episode-level training).

        Args:
            phase_result: Result of a single phase execution.
            behavioral_score: External behavioral score from dojo's judge.

        Returns:
            RewardSignal with phase-level scores.
        """
        # Phase completion: did it finish without error?
        completed = 1.0 if phase_result.error is None else 0.0

        # Outcome: based on artifacts produced
        artifact_count = len(phase_result.artifacts)
        outcome = min(artifact_count / max(1, 1), 1.0) if completed else 0.0

        # Efficiency: based on duration (shorter is better, capped)
        max_duration = 600.0  # 10 minutes
        duration = phase_result.duration_seconds
        efficiency = max(1.0 - (duration / max_duration), 0.0) if completed else 0.0

        w = self._weights
        total = (
            w.outcome * outcome
            + w.behavioral * behavioral_score
            + w.efficiency * efficiency
            + w.phase_completion * completed
        )

        return RewardSignal(
            outcome=round(outcome, 4),
            efficiency=round(efficiency, 4),
            phase_completion=round(completed, 4),
            behavioral=round(behavioral_score, 4),
            total=round(total, 4),
            components={
                "artifact_count": artifact_count,
                "duration_seconds": round(duration, 2),
                "completed": completed,
            },
        )

    def _compute_phase_completion(
        self, phase_results: Optional[List["PhaseResult"]]
    ) -> float:
        """Average phase completion score (0-1)."""
        if not phase_results:
            return 1.0  # No phase data = assume completed
        completed = sum(1 for p in phase_results if p.error is None)
        return completed / len(phase_results)
