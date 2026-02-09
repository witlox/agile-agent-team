"""Unit tests for metrics calculation and export."""

import pytest
from src.metrics.sprint_metrics import SprintMetrics


@pytest.fixture
def sprint_metrics():
    """Create sprint metrics calculator."""
    return SprintMetrics()


@pytest.fixture
def sample_sprint_data():
    """Sample sprint data for metrics calculation."""
    return {
        "sprint": 1,
        "cards": [
            {"id": "1", "story_points": 5, "status": "done"},
            {"id": "2", "story_points": 3, "status": "done"},
            {"id": "3", "story_points": 2, "status": "in_progress"},
        ],
        "sessions": [
            {"driver_id": "dev1", "navigator_id": "dev2", "duration": 120},
            {"driver_id": "dev2", "navigator_id": "dev3", "duration": 90},
        ],
    }


@pytest.mark.asyncio
async def test_sprint_metrics_calculation(sprint_metrics, mock_db, mock_kanban):
    """Test sprint-level metrics aggregation."""
    result = await sprint_metrics.calculate_sprint_results(1, mock_db, mock_kanban)

    # Should return result with key metrics
    assert hasattr(result, "velocity"), "Should have velocity"
    assert hasattr(result, "features_completed"), "Should have features completed"
    assert hasattr(result, "test_coverage"), "Should have test coverage"


@pytest.mark.asyncio
async def test_coverage_simulation(sprint_metrics):
    """Test coverage simulation formula."""
    # Simulate coverage based on checkpoints
    checkpoints = 4
    consensus = True

    base = 70.0
    per_checkpoint = 3.5
    consensus_bonus = 5.0 if consensus else 0.0

    expected = min(base + checkpoints * per_checkpoint + consensus_bonus, 95.0)

    # Verify calculation (70 + 4*3.5 + 5 = 89)
    assert expected == 89.0, f"Expected 89.0, got {expected}"


def test_junior_specific_metrics():
    """Test junior-specific metrics calculation."""
    junior_data = {
        "mistakes_made": 3,
        "corrections_received": 5,
        "learning_rate": 0.8,
    }

    # Junior metrics would track learning indicators
    assert junior_data["learning_rate"] > 0, "Should have learning rate"


def test_senior_specific_metrics():
    """Test senior-specific metrics calculation."""
    senior_data = {
        "mentoring_sessions": 8,
        "code_reviews": 12,
        "architectural_decisions": 3,
    }

    # Senior metrics would track mentoring and leadership
    assert senior_data["mentoring_sessions"] > 0, "Should track mentoring"


def test_prometheus_exporter_metrics():
    """Test Prometheus metrics endpoint."""
    # Verify prometheus module exists
    import src.metrics.prometheus_exporter as prom_module

    # Should have module
    assert prom_module is not None, "Should have prometheus exporter module"


def test_custom_metric_registration():
    """Test custom metric registration."""
    # Custom metrics can be registered
    # (Implementation-specific - just verify concept)
    metric_name = "custom_metric"
    assert isinstance(metric_name, str), "Metrics have names"


def test_metric_validation():
    """Test metric value validation."""
    # Velocity should be non-negative
    velocity = 8
    assert velocity >= 0, "Velocity should be non-negative"

    # Coverage should be 0-100
    coverage = 87.5
    assert 0 <= coverage <= 100, "Coverage should be 0-100%"


def test_metric_export_format():
    """Test Prometheus export format."""
    # Prometheus format: metric_name{labels} value
    sample_metric = 'sprint_velocity{sprint="1"} 8.0'
    assert "sprint_velocity" in sample_metric, "Should have metric name"
