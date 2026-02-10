"""Unit tests for OverheadBudgetTracker and StepTiming."""

from datetime import datetime, timedelta

from src.orchestrator.config import OverheadBudgetConfig
from src.orchestrator.overhead_budget import OverheadBudgetTracker, StepTiming


# ---------------------------------------------------------------------------
# StepTiming
# ---------------------------------------------------------------------------


def test_step_timing_elapsed():
    """elapsed_seconds returns wall-clock seconds consumed."""
    started = datetime(2026, 1, 1, 12, 0, 0)
    ended = datetime(2026, 1, 1, 12, 0, 45)
    timing = StepTiming(
        step_name="coordination",
        sprint_num=1,
        started=started,
        ended=ended,
        timeout_seconds=60.0,
    )
    assert timing.elapsed_seconds == 45.0


def test_step_timing_elapsed_none():
    """elapsed_seconds is 0 when ended is None."""
    timing = StepTiming(
        step_name="coordination",
        sprint_num=1,
        started=datetime.now(),
        timeout_seconds=60.0,
    )
    assert timing.elapsed_seconds == 0.0


# ---------------------------------------------------------------------------
# OverheadBudgetTracker — budget calculations
# ---------------------------------------------------------------------------


def test_budget_tracker_total_calculation():
    """Total budget is total_budget_minutes * 60."""
    # 3 sprints × 60 min = 180 min total; 20% = 36 min
    tracker = OverheadBudgetTracker(
        total_budget_minutes=36.0,
        num_sprints=3,
    )
    assert tracker._total_budget_seconds == 36.0 * 60.0
    assert tracker.remaining_seconds == 36.0 * 60.0


def test_budget_tracker_iteration_zero_timeout():
    """Iteration 0 gets iteration_zero_share of total budget."""
    tracker = OverheadBudgetTracker(
        total_budget_minutes=36.0,
        iteration_zero_share=0.40,
        num_sprints=3,
    )
    timeout = tracker.get_iteration_zero_timeout()
    expected = 36.0 * 60.0 * 0.40  # 864 seconds
    assert abs(timeout - expected) < 0.01


def test_budget_tracker_step_timeout_coordination():
    """Coordination step gets its weight of per-sprint budget."""
    # Total = 36 min; iter-0 share = 40% = 14.4 min
    # Per-sprint = 36 * 0.60 / 3 = 7.2 min = 432 seconds
    # Coordination = 432 * 0.50 = 216 seconds
    tracker = OverheadBudgetTracker(
        total_budget_minutes=36.0,
        iteration_zero_share=0.40,
        step_weights={"coordination": 0.50, "distribution": 0.30, "checkin": 0.20},
        num_sprints=3,
    )
    timeout = tracker.get_step_timeout("coordination", 1)
    expected = 36.0 * 60.0 * 0.60 / 3.0 * 0.50
    assert abs(timeout - expected) < 0.01


def test_budget_tracker_step_timeout_distribution():
    """Distribution step gets its weight of per-sprint budget."""
    tracker = OverheadBudgetTracker(
        total_budget_minutes=36.0,
        iteration_zero_share=0.40,
        step_weights={"coordination": 0.50, "distribution": 0.30, "checkin": 0.20},
        num_sprints=3,
    )
    timeout = tracker.get_step_timeout("distribution", 1)
    expected = 36.0 * 60.0 * 0.60 / 3.0 * 0.30
    assert abs(timeout - expected) < 0.01


def test_budget_tracker_clamped_to_remaining():
    """Step timeout is clamped when budget is nearly spent."""
    tracker = OverheadBudgetTracker(
        total_budget_minutes=1.0,  # 60 seconds total
        iteration_zero_share=0.0,  # no iter-0 share
        num_sprints=1,
        min_step_timeout_seconds=5.0,
    )
    # Consume most of the budget
    tracker._spent_seconds = 55.0
    timeout = tracker.get_step_timeout("coordination", 1)
    # Remaining = 5 seconds, ideal = 60 * 0.50 = 30, clamped to 5
    assert timeout == 5.0


def test_budget_tracker_min_floor():
    """Step timeout never goes below min_step_timeout_seconds."""
    tracker = OverheadBudgetTracker(
        total_budget_minutes=0.5,  # 30 seconds total
        iteration_zero_share=0.0,
        num_sprints=1,
        min_step_timeout_seconds=15.0,
    )
    # Consume entire budget
    tracker._spent_seconds = 30.0
    timeout = tracker.get_step_timeout("coordination", 1)
    # remaining=0 → max(0, 15) = 15
    assert timeout == 15.0


def test_budget_tracker_record_step_debits():
    """Recording a step debits its elapsed time from remaining."""
    tracker = OverheadBudgetTracker(total_budget_minutes=10.0, num_sprints=1)
    initial = tracker.remaining_seconds

    timing = StepTiming(
        step_name="coordination",
        sprint_num=1,
        started=datetime(2026, 1, 1, 12, 0, 0),
        ended=datetime(2026, 1, 1, 12, 1, 0),
        timeout_seconds=120.0,
    )
    tracker.record_step(timing)

    assert tracker.remaining_seconds == initial - 60.0
    assert len(tracker._history) == 1


def test_budget_tracker_to_report():
    """to_report returns a dict with expected structure."""
    tracker = OverheadBudgetTracker(total_budget_minutes=10.0, num_sprints=2)

    timing = StepTiming(
        step_name="coordination",
        sprint_num=1,
        started=datetime(2026, 1, 1, 12, 0, 0),
        ended=datetime(2026, 1, 1, 12, 0, 30),
        timeout_seconds=60.0,
        timed_out=True,
    )
    tracker.record_step(timing)

    report = tracker.to_report()
    assert report["total_budget_seconds"] == 600.0
    assert report["spent_seconds"] == 30.0
    assert report["remaining_seconds"] == 570.0
    assert report["num_steps"] == 1
    assert report["timeouts"] == 1
    assert len(report["steps"]) == 1
    assert report["steps"][0]["step"] == "coordination"
    assert report["steps"][0]["timed_out"] is True


def test_budget_tracker_get_deadline():
    """get_deadline returns a datetime in the future."""
    tracker = OverheadBudgetTracker(total_budget_minutes=10.0, num_sprints=1)
    before = datetime.now()
    deadline = tracker.get_deadline(30.0)
    after = datetime.now()

    assert deadline >= before + timedelta(seconds=30.0)
    assert deadline <= after + timedelta(seconds=30.0)


# ---------------------------------------------------------------------------
# OverheadBudgetConfig
# ---------------------------------------------------------------------------


def test_overhead_budget_config_defaults():
    """OverheadBudgetConfig has expected defaults."""
    cfg = OverheadBudgetConfig()
    assert cfg.overhead_budget_pct == 0.20
    assert cfg.iteration_zero_share == 0.40
    assert cfg.coordination_step_weight == 0.50
    assert cfg.distribution_step_weight == 0.30
    assert cfg.checkin_step_weight == 0.20
    assert cfg.min_step_timeout_seconds == 10.0
