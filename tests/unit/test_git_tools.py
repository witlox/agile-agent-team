"""Unit tests for git tools (status, diff, add, commit, remote)."""


import pytest

from src.tools.agent_tools.git import (
    GitStatusTool,
    GitDiffTool,
    GitAddTool,
    GitCommitTool,
    GitRemoteTool,
)


@pytest.fixture
def git_workspace(tmp_path):
    """Create a tmp dir with an initialised git repo."""
    workspace = tmp_path / "repo"
    workspace.mkdir()
    # Init git repo synchronously
    import subprocess

    subprocess.run(["git", "init"], cwd=str(workspace), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=str(workspace),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(workspace),
        check=True,
        capture_output=True,
    )
    return workspace


# ---------------------------------------------------------------------------
# GitStatusTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_status_clean(git_workspace):
    """Clean repo shows no output (aside from default)."""
    tool = GitStatusTool(workspace_root=str(git_workspace))
    result = await tool.execute()
    assert result.success


@pytest.mark.asyncio
async def test_git_status_dirty(git_workspace):
    """Untracked file appears in status."""
    (git_workspace / "new.txt").write_text("hello")
    tool = GitStatusTool(workspace_root=str(git_workspace))
    result = await tool.execute()
    assert result.success
    assert "new.txt" in result.output


# ---------------------------------------------------------------------------
# GitAddTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_add_file(git_workspace):
    """Staging a file succeeds."""
    (git_workspace / "new.txt").write_text("hello")
    tool = GitAddTool(workspace_root=str(git_workspace))
    result = await tool.execute(files=["new.txt"])
    assert result.success

    # Verify it's staged via git status
    status = GitStatusTool(workspace_root=str(git_workspace))
    status_result = await status.execute()
    assert "new.txt" in status_result.output


@pytest.mark.asyncio
async def test_git_add_empty_list(git_workspace):
    """Empty file list returns error."""
    tool = GitAddTool(workspace_root=str(git_workspace))
    result = await tool.execute(files=[])
    assert not result.success
    assert "No files" in result.error


# ---------------------------------------------------------------------------
# GitCommitTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_commit(git_workspace):
    """Stage and commit a file, verify it appears in log."""
    (git_workspace / "new.txt").write_text("hello")
    add_tool = GitAddTool(workspace_root=str(git_workspace))
    await add_tool.execute(files=["new.txt"])

    commit_tool = GitCommitTool(workspace_root=str(git_workspace))
    result = await commit_tool.execute(message="test commit")
    assert result.success

    # Verify via git log
    import subprocess

    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(git_workspace),
        capture_output=True,
        text=True,
    )
    assert "test commit" in log.stdout


# ---------------------------------------------------------------------------
# GitDiffTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_diff(git_workspace):
    """Modify a tracked file and verify diff output."""
    # Create initial commit
    (git_workspace / "file.txt").write_text("original")
    import subprocess

    subprocess.run(
        ["git", "add", "file.txt"],
        cwd=str(git_workspace),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(git_workspace),
        check=True,
        capture_output=True,
    )

    # Modify file
    (git_workspace / "file.txt").write_text("modified")

    tool = GitDiffTool(workspace_root=str(git_workspace))
    result = await tool.execute()
    assert result.success
    assert "modified" in result.output or "file.txt" in result.output


# ---------------------------------------------------------------------------
# GitRemoteTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_remote_add(git_workspace):
    """Adding a remote succeeds."""
    tool = GitRemoteTool(workspace_root=str(git_workspace))
    result = await tool.execute(url="https://github.com/test/test.git")
    assert result.success

    # Verify remote exists
    import subprocess

    remote = subprocess.run(
        ["git", "remote", "-v"],
        cwd=str(git_workspace),
        capture_output=True,
        text=True,
    )
    assert "origin" in remote.stdout
    assert "test/test.git" in remote.stdout
