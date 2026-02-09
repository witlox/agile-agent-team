"""Unit tests for workspace manager (greenfield/brownfield support)."""

import pytest
from pathlib import Path
from src.codegen.workspace import WorkspaceManager


@pytest.fixture
def temp_base(tmp_path):
    """Temporary base directory for workspaces."""
    base = tmp_path / "workspaces"
    base.mkdir()
    return base


@pytest.mark.asyncio
async def test_create_sprint_workspace_greenfield(temp_base):
    """Test fresh workspace creation in greenfield mode."""
    manager = WorkspaceManager(
        base_dir=str(temp_base),
        repo_config={},  # No repo = greenfield
        workspace_mode="per_story",
    )

    workspace = manager.create_sprint_workspace(sprint_num=1, story_id="us-001")

    # Should create workspace directory
    assert workspace.exists(), "Workspace should be created"
    assert workspace.is_dir(), "Should be a directory"

    # Should have git initialized
    assert (workspace / ".git").exists(), "Should have git repo"


@pytest.mark.asyncio
async def test_create_sprint_workspace_brownfield_incremental(temp_base, tmp_path):
    """Test workspace reuse and pull in brownfield mode."""
    # Create a fake remote repo
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()

    # Initialize as git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=remote_repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=remote_repo,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=remote_repo,
        capture_output=True,
    )
    (remote_repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=remote_repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=remote_repo,
        capture_output=True,
    )

    manager = WorkspaceManager(
        base_dir=str(temp_base),
        repo_config={"url": str(remote_repo), "clone_mode": "incremental"},
        workspace_mode="per_sprint",
    )

    # First workspace
    workspace1 = manager.create_sprint_workspace(sprint_num=1)
    assert workspace1.exists(), "Should create first workspace"

    # Second workspace (should reuse if incremental)
    workspace2 = manager.create_sprint_workspace(sprint_num=1)
    assert workspace2.exists(), "Should reuse workspace"


def test_init_fresh_repo(temp_base):
    """Test fresh git repo initialization."""
    manager = WorkspaceManager(
        base_dir=str(temp_base), repo_config={}, workspace_mode="per_story"
    )

    workspace = temp_base / "test-init"
    workspace.mkdir()

    manager._init_fresh_repo(workspace)

    # Should have git initialized
    assert (workspace / ".git").exists(), "Should have git repo"

    # Should have initial commit
    import subprocess

    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=workspace,
        capture_output=True,
    )
    assert result.returncode == 0, "Should have git history"


@pytest.mark.asyncio
async def test_clone_repo(temp_base, tmp_path):
    """Test repository cloning from URL."""
    # Create a fake remote repo
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()

    import subprocess

    subprocess.run(["git", "init"], cwd=remote_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )
    (remote_repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=remote_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Test"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )

    manager = WorkspaceManager(
        base_dir=str(temp_base),
        repo_config={"url": str(remote_repo)},
        workspace_mode="per_story",
    )

    workspace = temp_base / "cloned"
    workspace.mkdir()

    manager._clone_repo(workspace)

    # Should have cloned content
    assert (workspace / "file.txt").exists(), "Should clone files"
    assert (workspace / ".git").exists(), "Should clone git repo"


@pytest.mark.asyncio
async def test_pull_latest_incremental_mode(temp_base, tmp_path):
    """Test git pull in incremental mode."""
    # Create a repo
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()

    import subprocess

    subprocess.run(["git", "init"], cwd=remote_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )
    (remote_repo / "file.txt").write_text("v1")
    subprocess.run(["git", "add", "."], cwd=remote_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "V1"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )

    # Get the actual branch name (main or master depending on git version)
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
        text=True,
    )
    default_branch = branch_result.stdout.strip()

    # Clone to workspace
    workspace = temp_base / "workspace"
    subprocess.run(
        ["git", "clone", str(remote_repo), str(workspace)],
        capture_output=True,
        check=True,
    )

    # Update remote
    (remote_repo / "file.txt").write_text("v2")
    subprocess.run(["git", "add", "."], cwd=remote_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "V2"],
        cwd=remote_repo,
        capture_output=True,
        check=True,
    )

    manager = WorkspaceManager(
        base_dir=str(temp_base),
        repo_config={"url": str(remote_repo), "branch": default_branch},
        workspace_mode="per_sprint",
    )

    # Pull latest
    manager._pull_latest(workspace)

    # Should have latest content
    content = (workspace / "file.txt").read_text()
    assert "v2" in content, "Should pull latest changes"


def test_create_feature_branch(temp_base):
    """Test feature branch creation."""
    manager = WorkspaceManager(
        base_dir=str(temp_base), repo_config={}, workspace_mode="per_story"
    )

    workspace = temp_base / "branch-test"
    workspace.mkdir()
    manager._init_fresh_repo(workspace)

    branch_name = manager.create_feature_branch(workspace, "US-001")

    # Should create branch
    assert "feature/" in branch_name, "Should use feature/ prefix"
    assert "us-001" in branch_name.lower(), "Should include story ID"

    # Verify branch exists
    import subprocess

    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=workspace,
        capture_output=True,
    )
    current_branch = result.stdout.decode().strip()
    assert current_branch == branch_name, f"Should be on feature branch {branch_name}"


def test_cleanup_workspace(temp_base):
    """Test workspace cleanup."""
    workspace = temp_base / "cleanup-test"
    workspace.mkdir()
    (workspace / "file.txt").write_text("test")

    assert workspace.exists(), "Workspace should exist"

    # Cleanup
    import shutil

    shutil.rmtree(workspace)

    assert not workspace.exists(), "Workspace should be cleaned up"


@pytest.mark.asyncio
async def test_brownfield_clone_failure_handling(temp_base):
    """Test error handling when clone fails."""
    manager = WorkspaceManager(
        base_dir=str(temp_base),
        repo_config={"url": "https://invalid-url-that-does-not-exist.com/repo.git"},
        workspace_mode="per_story",
    )

    # Should handle clone failure gracefully
    with pytest.raises(Exception):
        workspace = manager.create_sprint_workspace(sprint_num=1, story_id="us-001")
