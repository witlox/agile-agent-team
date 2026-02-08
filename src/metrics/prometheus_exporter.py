"""Prometheus metrics exporter."""

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
sprint_velocity = Gauge('sprint_velocity', 'Story points per sprint')
test_coverage = Gauge('test_coverage_percent', 'Test coverage')
pairing_sessions = Counter('pairing_sessions_total', 'Total sessions', ['driver', 'navigator'])
consensus_time = Histogram('consensus_seconds', 'Time to consensus')

def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")
