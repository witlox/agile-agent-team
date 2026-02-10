"""Unit tests for multi-language builder tool."""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.agent_tools.builder import MultiLanguageBuilder


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def builder(temp_workspace):
    """Create a MultiLanguageBuilder instance."""
    return MultiLanguageBuilder(workspace_root=str(temp_workspace))


def _mock_subprocess(returncode=0, stdout=b"", stderr=b""):
    """Return an AsyncMock that behaves like asyncio.create_subprocess_exec."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    return proc


# ---------------------------------------------------------------------------
# Python builds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_python_requirements(temp_workspace, builder):
    """Build dispatches pip install -r requirements.txt when file exists."""
    (temp_workspace / "requirements.txt").write_text("pytest==7.4.3")
    proc = _mock_subprocess(stdout=b"Successfully installed pytest-7.4.3")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="python")
    assert result.success
    # Verify pip install -r requirements.txt was called
    args = mock_exec.call_args[0]
    assert "pip" in args
    assert "-r" in args
    assert "requirements.txt" in args


@pytest.mark.asyncio
async def test_build_python_pyproject(temp_workspace, builder):
    """Build dispatches pip install -e . when pyproject.toml exists."""
    (temp_workspace / "pyproject.toml").write_text("[project]\nname='x'")
    proc = _mock_subprocess(stdout=b"Successfully installed x")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="python")
    assert result.success
    args = mock_exec.call_args[0]
    assert "-e" in args
    assert "." in args


@pytest.mark.asyncio
async def test_build_python_no_config(temp_workspace, builder):
    """No build files → error result."""
    result = await builder.execute(language="python")
    assert not result.success
    assert "No requirements.txt" in result.error


# ---------------------------------------------------------------------------
# Go builds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_go(temp_workspace, builder):
    """Go build dispatches go mod download then go build ./..."""
    (temp_workspace / "go.mod").write_text("module example.com/m\ngo 1.21")
    proc = _mock_subprocess(stdout=b"ok")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="go")
    assert result.success
    # Should have called go mod download then go build
    calls = mock_exec.call_args_list
    assert len(calls) == 2
    assert "mod" in calls[0][0]
    assert "build" in calls[1][0]


@pytest.mark.asyncio
async def test_build_go_release(temp_workspace, builder):
    """Go release build includes -ldflags -s -w."""
    (temp_workspace / "go.mod").write_text("module m")
    proc = _mock_subprocess(stdout=b"ok")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="go", release=True)
    assert result.success
    # The second call (go build) should contain ldflags
    build_call_args = mock_exec.call_args_list[1][0]
    assert "-ldflags" in build_call_args


# ---------------------------------------------------------------------------
# Rust builds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_rust(temp_workspace, builder):
    """Rust build dispatches cargo build."""
    (temp_workspace / "Cargo.toml").write_text("[package]")
    proc = _mock_subprocess(stdout=b"Compiling")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="rust")
    assert result.success
    args = mock_exec.call_args[0]
    assert "cargo" in args
    assert "build" in args


@pytest.mark.asyncio
async def test_build_rust_release(temp_workspace, builder):
    """Rust release build includes --release flag."""
    (temp_workspace / "Cargo.toml").write_text("[package]")
    proc = _mock_subprocess(stdout=b"Compiling")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute(language="rust", release=True)
    assert result.success
    args = mock_exec.call_args[0]
    assert "--release" in args


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_unsupported_language(temp_workspace, builder):
    """Unsupported language returns error."""
    result = await builder.execute(language="fortran")
    assert not result.success
    assert "Unsupported language" in result.error


@pytest.mark.asyncio
async def test_build_auto_detect(temp_workspace, builder):
    """Auto-detect dispatches correct builder from workspace markers."""
    (temp_workspace / "Cargo.toml").write_text("[package]")
    proc = _mock_subprocess(stdout=b"Compiling")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await builder.execute()  # no language arg
    assert result.success
    args = mock_exec.call_args[0]
    assert "cargo" in args
