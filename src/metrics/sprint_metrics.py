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
    test_coverage: float  # Real line coverage from pytest-cov
    process_coverage: float  # Process-based coverage (TDD protocol adherence)
    branch_coverage: float  # Real branch coverage from pytest-cov
    pairing_sessions: int
    cycle_time_avg: float


class SprintMetrics:
    """Calculates per-sprint metrics from the shared database."""

    async def calculate_sprint_results(
        self,
        sprint_num: int,
        db: "SharedContextDB",
        kanban: "KanbanBoard",
        team_id: str = "",
    ) -> SprintResult:
        """Calculate all metrics for a sprint.

        Queries the database for completed cards (velocity),
        pairing session count, and average cycle time.
        """
        # Completed cards this sprint (team-scoped when applicable)
        if team_id:
            all_done = await db.get_cards_by_status_for_team("done", team_id)
        else:
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

                        t_start = datetime.fromisoformat(start)
                        t_end = datetime.fromisoformat(end)
                        durations.append((t_end - t_start).total_seconds())
                    except Exception:
                        pass
            if durations:
                cycle_time_avg = sum(durations) / len(durations)

        # Coverage metrics: weighted average across pairing sessions
        test_coverage = 0.0  # Real line coverage
        process_coverage = 0.0  # Process-based (TDD adherence)
        branch_coverage = 0.0  # Real branch coverage

        if sessions:
            # Build a map of task_id -> story_points from done cards
            sp_map = {c.get("id"): c.get("story_points", 1) for c in sprint_done}
            total_weight = 0.0
            line_cov_sum = 0.0
            process_cov_sum = 0.0
            branch_cov_sum = 0.0

            for s in sessions:
                weight = float(sp_map.get(s.get("task_id"), 1))

                # Real line coverage (from pytest-cov)
                if s.get("line_coverage") is not None:
                    line_cov_sum += s["line_coverage"] * weight

                # Process coverage (TDD protocol adherence)
                if s.get("process_coverage") is not None:
                    process_cov_sum += s["process_coverage"] * weight

                # Real branch coverage (from pytest-cov)
                if s.get("branch_coverage") is not None:
                    branch_cov_sum += s["branch_coverage"] * weight

                total_weight += weight

            if total_weight > 0:
                test_coverage = line_cov_sum / total_weight
                process_coverage = process_cov_sum / total_weight
                branch_coverage = branch_cov_sum / total_weight

        return SprintResult(
            velocity=velocity,
            features_completed=features_completed,
            test_coverage=test_coverage,
            process_coverage=process_coverage,
            branch_coverage=branch_coverage,
            pairing_sessions=pairing_sessions,
            cycle_time_avg=cycle_time_avg,
        )
