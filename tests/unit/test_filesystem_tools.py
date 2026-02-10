"""Unit tests for filesystem tools (read, write, edit, list, search)."""

import pytest

from src.tools.agent_tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListFilesTool,
    SearchCodeTool,
)


@pytest.fixture
def workspace(tmp_path):
    """Use tmp_path directly as workspace."""
    return tmp_path


# ---------------------------------------------------------------------------
# ReadFileTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_file(workspace):
    """Write a file, then read it back."""
    f = workspace / "hello.txt"
    f.write_text("hello world\n", encoding="utf-8")
    tool = ReadFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="hello.txt")
    assert result.success
    assert "hello world" in result.output
    assert result.metadata["lines"] == 1


@pytest.mark.asyncio
async def test_read_file_not_found(workspace):
    """Reading nonexistent file returns error."""
    tool = ReadFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="nope.txt")
    assert not result.success
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# WriteFileTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_file(workspace):
    """Write file and verify on disk."""
    tool = WriteFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="out.txt", content="test content\n")
    assert result.success
    assert (workspace / "out.txt").read_text() == "test content\n"
    assert "out.txt" in result.files_changed


@pytest.mark.asyncio
async def test_write_file_creates_dirs(workspace):
    """Write to nested path creates parent dirs."""
    tool = WriteFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="a/b/c.txt", content="deep")
    assert result.success
    assert (workspace / "a" / "b" / "c.txt").read_text() == "deep"


# ---------------------------------------------------------------------------
# EditFileTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_file(workspace):
    """Edit replaces old text with new text."""
    f = workspace / "edit_me.py"
    f.write_text("x = 1\ny = 2\n")
    tool = EditFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="edit_me.py", old_text="x = 1", new_text="x = 42")
    assert result.success
    assert "x = 42" in f.read_text()


@pytest.mark.asyncio
async def test_edit_file_no_match(workspace):
    """Edit with nonexistent old_text returns error."""
    f = workspace / "edit_me.py"
    f.write_text("x = 1\n")
    tool = EditFileTool(workspace_root=str(workspace))
    result = await tool.execute(
        path="edit_me.py", old_text="MISSING", new_text="replacement"
    )
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_edit_file_not_found(workspace):
    """Edit nonexistent file returns error."""
    tool = EditFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="nope.py", old_text="a", new_text="b")
    assert not result.success
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# ListFilesTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_files(workspace):
    """List files in workspace."""
    (workspace / "a.py").write_text("pass")
    (workspace / "b.txt").write_text("hello")
    sub = workspace / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("pass")

    tool = ListFilesTool(workspace_root=str(workspace))
    result = await tool.execute(pattern="**/*.py")
    assert result.success
    assert "a.py" in result.output
    assert "c.py" in result.output
    assert result.metadata["count"] == 2


@pytest.mark.asyncio
async def test_list_files_no_match(workspace):
    """List with no matches returns 'No files found'."""
    tool = ListFilesTool(workspace_root=str(workspace))
    result = await tool.execute(pattern="**/*.rs")
    assert result.success
    assert "No files found" in result.output


# ---------------------------------------------------------------------------
# SearchCodeTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_code(workspace):
    """Search finds pattern in files."""
    (workspace / "foo.py").write_text("def hello():\n    pass\n")
    (workspace / "bar.py").write_text("x = 1\n")
    tool = SearchCodeTool(workspace_root=str(workspace))
    result = await tool.execute(pattern="def hello", file_pattern="**/*.py")
    assert result.success
    assert "foo.py" in result.output
    assert result.metadata["count"] == 1


@pytest.mark.asyncio
async def test_search_code_no_match(workspace):
    """Search with no results returns informative message."""
    (workspace / "foo.py").write_text("x = 1\n")
    tool = SearchCodeTool(workspace_root=str(workspace))
    result = await tool.execute(pattern="ZZZNOTFOUND")
    assert result.success
    assert "No matches" in result.output


# ---------------------------------------------------------------------------
# Path escape (security)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_escape_blocked_read(workspace):
    """Attempting to read outside workspace is rejected."""
    tool = ReadFileTool(workspace_root=str(workspace))
    result = await tool.execute(path="../../etc/passwd")
    assert not result.success
    assert "escapes workspace" in result.error
