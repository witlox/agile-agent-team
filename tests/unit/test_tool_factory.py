"""Unit tests for tool factory (create_tools, set expansion, dedup)."""

import pytest

from src.tools.agent_tools.factory import (
    TOOL_REGISTRY,
    TOOL_SETS,
    create_tools,
    get_tool_names,
    get_tool_set_names,
)


@pytest.fixture
def workspace(tmp_path):
    return str(tmp_path)


# ---------------------------------------------------------------------------
# create_tools
# ---------------------------------------------------------------------------


def test_create_tools_by_name(workspace):
    """Create tools by individual names."""
    tools = create_tools(["read_file", "bash"], workspace)
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert names == {"read_file", "bash"}


def test_create_tools_by_set(workspace):
    """Create tools using a set name."""
    tools = create_tools(["filesystem"], workspace)
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "search_code",
    }


def test_create_tools_set_expansion_git(workspace):
    """Git set expands to 6 tools."""
    tools = create_tools(["git"], workspace)
    assert len(tools) == 6


def test_create_tools_deduplication(workspace):
    """Duplicate tools from set + individual are deduplicated."""
    tools = create_tools(["read_file", "filesystem"], workspace)
    # filesystem has 5 tools; read_file is already in filesystem → still 5
    assert len(tools) == 5
    names = [t.name for t in tools]
    assert names.count("read_file") == 1


def test_create_tools_unknown_raises(workspace):
    """Unknown tool name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown tool: nonexistent"):
        create_tools(["nonexistent"], workspace)


def test_create_tools_empty(workspace):
    """Empty list returns empty list."""
    assert create_tools([], workspace) == []


# ---------------------------------------------------------------------------
# Registry / set queries
# ---------------------------------------------------------------------------


def test_get_tool_names():
    """get_tool_names returns all registry keys."""
    names = get_tool_names()
    assert len(names) == len(TOOL_REGISTRY)
    assert "read_file" in names
    assert "bash" in names
    assert "run_tests" in names


def test_get_tool_set_names():
    """get_tool_set_names returns all set keys."""
    names = get_tool_set_names()
    assert len(names) == len(TOOL_SETS)
    assert "filesystem" in names
    assert "git" in names
    assert "full" in names


def test_full_set_contains_all_tools():
    """The 'full' set contains every tool in the registry."""
    assert set(TOOL_SETS["full"]) == set(TOOL_REGISTRY.keys())
