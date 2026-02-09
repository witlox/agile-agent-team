"""Prometheus metrics exporter."""

from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram, Gauge, start_http_server

if TYPE_CHECKING:
    from ..metrics.sprint_metrics import SprintResult

# Define metrics
sprint_velocity = Gauge('sprint_velocity', 'Story points per sprint')
test_coverage = Gauge('test_coverage_percent', 'Real line coverage from pytest-cov')
process_coverage = Gauge('process_coverage_percent', 'Process-based coverage (TDD protocol adherence)')
branch_coverage = Gauge('branch_coverage_percent', 'Real branch coverage from pytest-cov')
pairing_sessions = Counter('pairing_sessions_total', 'Total sessions', ['driver', 'navigator'])
consensus_time = Histogram('consensus_seconds', 'Time to consensus')


def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")


def update_sprint_metrics(result: "SprintResult", session_details=None):
    """Update Prometheus gauges/counters after each sprint.

    Args:
        result: SprintResult with velocity and coverage metrics.
        session_details: Optional list of session dicts with driver_id/navigator_id.
    """
    sprint_velocity.set(result.velocity)
    test_coverage.set(result.test_coverage)  # Real line coverage from pytest-cov
    process_coverage.set(result.process_coverage)  # TDD protocol adherence
    branch_coverage.set(result.branch_coverage)  # Real branch coverage from pytest-cov
    if session_details:
        for session in session_details:
            driver = session.get("driver_id", "unknown")
            navigator = session.get("navigator_id", "unknown")
            pairing_sessions.labels(driver=driver, navigator=navigator).inc()
