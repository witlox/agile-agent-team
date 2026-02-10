"""Unit tests for tool base classes (_resolve_path security, ToolResult)."""

import pytest
from typing import Dict, Any

from src.tools.agent_tools.base import Tool, ToolResult


class DummyTool(Tool):
    """Minimal concrete Tool for testing _resolve_path."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "dummy tool"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="ok")


@pytest.fixture
def tool(tmp_path):
    """Create a DummyTool rooted at tmp_path."""
    return DummyTool(workspace_root=str(tmp_path))


# ---------------------------------------------------------------------------
# _resolve_path tests
# ---------------------------------------------------------------------------


def test_resolve_path_normal(tool, tmp_path):
    """Normal relative path resolves inside workspace."""
    result = tool._resolve_path("src/main.py")
    assert result == tmp_path / "src" / "main.py"


def test_resolve_path_traversal_blocked(tool):
    """Path traversal with .. is rejected."""
    with pytest.raises(ValueError, match="escapes workspace"):
        tool._resolve_path("../../etc/passwd")


def test_resolve_path_absolute_blocked(tool):
    """Absolute path outside workspace is rejected."""
    with pytest.raises(ValueError, match="escapes workspace"):
        tool._resolve_path("/etc/passwd")


def test_resolve_path_dot(tool, tmp_path):
    """Single dot resolves to workspace root."""
    result = tool._resolve_path(".")
    assert result == tmp_path


# ---------------------------------------------------------------------------
# ToolResult defaults
# ---------------------------------------------------------------------------


def test_tool_result_defaults():
    """ToolResult fields have correct defaults."""
    r = ToolResult(success=True, output="hello")
    assert r.success is True
    assert r.output == "hello"
    assert r.error is None
    assert r.files_changed == []
    assert r.metadata == {}


def test_tool_result_with_error():
    """ToolResult stores error string."""
    r = ToolResult(success=False, output="", error="boom")
    assert r.error == "boom"
    assert r.success is False
