"""Unit tests for Backlog class."""

import pytest
import yaml

from src.orchestrator.backlog import Backlog, ProductMetadata


SAMPLE_BACKLOG = {
    "product": {
        "name": "TestApp",
        "description": "A test application",
        "languages": ["python", "typescript"],
        "tech_stack": ["docker", "pytest"],
        "repository": {
            "type": "greenfield",
            "url": "",
        },
        "mission": "Help developers ship faster",
        "vision": "Best testing tool ever",
        "goals": ["Launch MVP", "100 users"],
        "target_audience": "Small teams",
        "success_metrics": ["WAU", "NPS"],
    },
    "stories": [
        {"id": "US-001", "title": "User login", "priority": 2, "points": 3},
        {"id": "US-002", "title": "User signup", "priority": 1, "points": 5},
        {"id": "US-003", "title": "Dashboard", "priority": 3, "points": 8},
        {"id": "US-004", "title": "Settings", "priority": 4, "points": 2},
        {"id": "US-005", "title": "Profile", "priority": 5, "points": 3},
    ],
}


@pytest.fixture
def backlog_file(tmp_path):
    """Write sample backlog YAML and return path."""
    path = tmp_path / "backlog.yaml"
    path.write_text(yaml.dump(SAMPLE_BACKLOG, default_flow_style=False))
    return str(path)


@pytest.fixture
def backlog(backlog_file):
    return Backlog(backlog_file)


# ---------------------------------------------------------------------------
# next_stories
# ---------------------------------------------------------------------------


def test_next_stories(backlog):
    """Request 3 stories, get 3 highest-priority (sorted by priority)."""
    stories = backlog.next_stories(3)
    assert len(stories) == 3
    # Priority 1 should come first
    assert stories[0]["id"] == "US-002"
    assert stories[1]["id"] == "US-001"
    assert stories[2]["id"] == "US-003"


def test_next_stories_exhaustion(backlog):
    """Requesting more stories than available returns what's left."""
    stories = backlog.next_stories(10)
    assert len(stories) == 5


def test_next_stories_no_repeat(backlog):
    """Selected stories are not offered again."""
    first = backlog.next_stories(2)
    second = backlog.next_stories(2)
    first_ids = {s["id"] for s in first}
    second_ids = {s["id"] for s in second}
    assert first_ids.isdisjoint(second_ids)


# ---------------------------------------------------------------------------
# mark_returned
# ---------------------------------------------------------------------------


def test_mark_returned(backlog):
    """Returned story appears in next call."""
    backlog.next_stories(5)
    assert backlog.remaining == 0

    backlog.mark_returned("US-005")
    assert backlog.remaining == 1

    returned = backlog.next_stories(1)
    assert returned[0]["id"] == "US-005"


# ---------------------------------------------------------------------------
# remaining
# ---------------------------------------------------------------------------


def test_remaining(backlog):
    """Remaining count decreases after next_stories."""
    assert backlog.remaining == 5
    backlog.next_stories(2)
    assert backlog.remaining == 3


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def test_summary(backlog):
    """Summary includes product name and description."""
    s = backlog.summary()
    assert "TestApp" in s
    assert "test application" in s


# ---------------------------------------------------------------------------
# get_product_metadata
# ---------------------------------------------------------------------------


def test_get_product_metadata(backlog):
    """Metadata reflects product section of YAML."""
    meta = backlog.get_product_metadata()
    assert isinstance(meta, ProductMetadata)
    assert meta.name == "TestApp"
    assert meta.languages == ["python", "typescript"]
    assert meta.repository_type == "greenfield"
    assert meta.mission == "Help developers ship faster"


# ---------------------------------------------------------------------------
# get_project_context
# ---------------------------------------------------------------------------


def test_get_project_context(backlog):
    """Project context includes mission, vision, goals."""
    ctx = backlog.get_project_context()
    assert "TestApp" in ctx
    assert "Mission" in ctx
    assert "Vision" in ctx
    assert "Launch MVP" in ctx


def test_get_project_context_empty(tmp_path):
    """Minimal backlog with no context fields returns empty string."""
    minimal = {
        "product": {"name": "X", "description": "desc"},
        "stories": [],
    }
    path = tmp_path / "minimal.yaml"
    path.write_text(yaml.dump(minimal))
    bl = Backlog(str(path))
    assert bl.get_project_context() == ""
