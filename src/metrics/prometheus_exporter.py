"""Prometheus metrics exporter."""

from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram, Gauge, start_http_server

if TYPE_CHECKING:
    from ..metrics.sprint_metrics import SprintResult

# Define metrics (with team label for multi-team support)
sprint_velocity = Gauge("sprint_velocity", "Story points per sprint", ["team"])
test_coverage = Gauge(
    "test_coverage_percent", "Real line coverage from pytest-cov", ["team"]
)
process_coverage = Gauge(
    "process_coverage_percent",
    "Process-based coverage (TDD protocol adherence)",
    ["team"],
)
branch_coverage = Gauge(
    "branch_coverage_percent", "Real branch coverage from pytest-cov", ["team"]
)
pairing_sessions = Counter(
    "pairing_sessions_total", "Total sessions", ["driver", "navigator"]
)
consensus_time = Histogram("consensus_seconds", "Time to consensus")


def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")


def update_sprint_metrics(
    result: "SprintResult", session_details=None, team_id: str = ""
):
    """Update Prometheus gauges/counters after each sprint.

    Args:
        result: SprintResult with velocity and coverage metrics.
        session_details: Optional list of session dicts with driver_id/navigator_id.
        team_id: Team identifier for multi-team mode (defaults to "default").
    """
    label = team_id or "default"
    sprint_velocity.labels(team=label).set(result.velocity)
    test_coverage.labels(team=label).set(result.test_coverage)
    process_coverage.labels(team=label).set(result.process_coverage)
    branch_coverage.labels(team=label).set(result.branch_coverage)
    if session_details:
        for session in session_details:
            driver = session.get("driver_id", "unknown")
            navigator = session.get("navigator_id", "unknown")
            pairing_sessions.labels(driver=driver, navigator=navigator).inc()
