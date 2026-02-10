"""Outer-loop wallclock management for multi-team orchestration.

Provides an overhead budget tracker that timeboxes coordination,
distribution, and mid-sprint checkin steps so they don't consume
unbounded experiment time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# Default step weights — must sum to 1.0
DEFAULT_STEP_WEIGHTS: Dict[str, float] = {
    "coordination": 0.50,
    "distribution": 0.30,
    "checkin": 0.20,
}


@dataclass
class StepTiming:
    """Record of a single timed step execution."""

    step_name: str
    sprint_num: int
    started: datetime
    ended: Optional[datetime] = None
    timeout_seconds: float = 0.0
    timed_out: bool = False

    @property
    def elapsed_seconds(self) -> float:
        """Wall-clock seconds consumed by this step."""
        if self.ended is None:
            return 0.0
        return (self.ended - self.started).total_seconds()


class OverheadBudgetTracker:
    """Tracks and enforces time budgets for multi-team overhead steps.

    Budget math (example: 3 sprints x 60 min, 20% overhead):
      Total overhead = 36 min
      Iteration 0   = 36 x 0.40 = 14.4 min
      Per sprint     = 36 x 0.60 / 3 = 7.2 min
      Coordination   = 7.2 x 0.50 = 3.6 min
      Distribution   = 7.2 x 0.30 = 2.16 min
      Checkin        = 7.2 x 0.20 = 1.44 min
    """

    def __init__(
        self,
        total_budget_minutes: float,
        iteration_zero_share: float = 0.40,
        step_weights: Optional[Dict[str, float]] = None,
        num_sprints: int = 1,
        min_step_timeout_seconds: float = 10.0,
    ):
        self._total_budget_seconds = total_budget_minutes * 60.0
        self._iteration_zero_share = iteration_zero_share
        self._step_weights = step_weights or dict(DEFAULT_STEP_WEIGHTS)
        self._num_sprints = max(num_sprints, 1)
        self._min_step_timeout_seconds = min_step_timeout_seconds

        # Derived budgets
        self._iteration_zero_budget = (
            self._total_budget_seconds * self._iteration_zero_share
        )
        remaining_after_iter0 = self._total_budget_seconds * (
            1.0 - self._iteration_zero_share
        )
        self._per_sprint_budget = remaining_after_iter0 / self._num_sprints

        # Tracking
        self._spent_seconds: float = 0.0
        self._history: List[StepTiming] = []

    def get_iteration_zero_timeout(self) -> float:
        """Seconds available for iteration 0 setup."""
        return max(
            min(self._iteration_zero_budget, self.remaining_seconds),
            self._min_step_timeout_seconds,
        )

    def get_step_timeout(self, step_name: str, sprint_num: int) -> float:
        """Seconds available for *step_name* in the given sprint."""
        weight = self._step_weights.get(step_name, 0.0)
        ideal = self._per_sprint_budget * weight
        clamped = min(ideal, self.remaining_seconds)
        return max(clamped, self._min_step_timeout_seconds)

    def get_deadline(self, timeout_seconds: float) -> datetime:
        """Return an absolute deadline *timeout_seconds* from now."""
        return datetime.now() + timedelta(seconds=timeout_seconds)

    def record_step(self, timing: StepTiming) -> None:
        """Record a completed step and debit its time from the budget."""
        self._history.append(timing)
        self._spent_seconds += timing.elapsed_seconds

    @property
    def remaining_seconds(self) -> float:
        """Seconds left in the total overhead budget."""
        return max(self._total_budget_seconds - self._spent_seconds, 0.0)

    def to_report(self) -> Dict[str, Any]:
        """Return a summary dict for inclusion in the final experiment report."""
        return {
            "total_budget_seconds": self._total_budget_seconds,
            "spent_seconds": self._spent_seconds,
            "remaining_seconds": self.remaining_seconds,
            "num_steps": len(self._history),
            "timeouts": sum(1 for s in self._history if s.timed_out),
            "steps": [
                {
                    "step": s.step_name,
                    "sprint": s.sprint_num,
                    "elapsed": round(s.elapsed_seconds, 2),
                    "timed_out": s.timed_out,
                }
                for s in self._history
            ],
        }
