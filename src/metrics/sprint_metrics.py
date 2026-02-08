"""Sprint metrics calculation."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tools.shared_context import SharedContextDB
    from ..tools.kanban import KanbanBoard


@dataclass
class SprintResult:
    velocity: int
    features_completed: int
    test_coverage: float
    pairing_sessions: int
    cycle_time_avg: float


class SprintMetrics:
    """Calculates per-sprint metrics from the shared database."""

    async def calculate_sprint_results(
        self, sprint_num: int, db: "SharedContextDB", kanban: "KanbanBoard"
    ) -> SprintResult:
        """Calculate all metrics for a sprint.

        Queries the database for completed cards (velocity),
        pairing session count, and average cycle time.
        """
        # Completed cards this sprint
        all_done = await db.get_cards_by_status("done")
        sprint_done = [c for c in all_done if c.get("sprint") == sprint_num]
        velocity = sum(c.get("story_points", 1) for c in sprint_done)
        features_completed = len(sprint_done)

        # Pairing sessions
        sessions = await db.get_pairing_sessions_for_sprint(sprint_num)
        pairing_sessions = len(sessions)

        # Average cycle time (seconds) — placeholder since timestamps may vary
        cycle_time_avg = 0.0
        if sessions:
            durations = []
            for s in sessions:
                start = s.get("start_time")
                end = s.get("end_time")
                if start and end:
                    try:
                        from datetime import datetime
                        fmt = "%Y-%m-%dT%H:%M:%S.%f"
                        t_start = datetime.fromisoformat(start)
                        t_end = datetime.fromisoformat(end)
                        durations.append((t_end - t_start).total_seconds())
                    except Exception:
                        pass
            if durations:
                cycle_time_avg = sum(durations) / len(durations)

        # Test coverage is not tracked in DB yet; default to 0.0
        test_coverage = 0.0

        return SprintResult(
            velocity=velocity,
            features_completed=features_completed,
            test_coverage=test_coverage,
            pairing_sessions=pairing_sessions,
            cycle_time_avg=cycle_time_avg,
        )
