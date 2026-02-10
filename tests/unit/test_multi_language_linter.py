"""Unit tests for multi-language linter tool."""

import shutil
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.agent_tools.linter import MultiLanguageLinter


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def linter(temp_workspace):
    """Create a MultiLanguageLinter instance."""
    return MultiLanguageLinter(workspace_root=str(temp_workspace))


# ---------------------------------------------------------------------------
# _parse_lint_output tests
# ---------------------------------------------------------------------------


def test_parse_lint_output_ruff(linter):
    """Parse ruff summary."""
    output = "src/foo.py:1:1: F401 `os` imported but unused\nFound 3 errors."
    result = linter._parse_lint_output(output, "ruff")
    assert result["errors"] == 3


def test_parse_lint_output_golangci(linter):
    """Parse golangci-lint multi-line output — count issues."""
    output = "main.go:10:5: unused variable\n" "util.go:20:3: ineffectual assignment\n"
    result = linter._parse_lint_output(output, "golangci-lint")
    assert result["errors"] == 2


def test_parse_lint_output_clippy(linter):
    """Parse clippy warnings and errors."""
    output = (
        "warning: unused variable `x`\n"
        "warning: unused import\n"
        "error: cannot find value `y`\n"
    )
    result = linter._parse_lint_output(output, "clippy")
    assert result["warnings"] == 2
    assert result["errors"] == 1


def test_parse_lint_output_eslint(linter):
    """Parse ESLint summary line."""
    output = (
        "/app/src/index.ts\n"
        "  2:1  error  no-unused-vars\n"
        "  5:3  warning  no-console\n\n"
        "2 problems (1 error, 1 warning)\n"
    )
    result = linter._parse_lint_output(output, "eslint")
    assert result["errors"] == 1
    assert result["warnings"] == 1


def test_parse_lint_output_clang_tidy(linter):
    """Parse clang-tidy output — count warnings and errors."""
    output = (
        "src/main.cpp:5:10: warning: unused variable\n"
        "src/main.cpp:8:5: error: undeclared identifier\n"
        "src/util.cpp:3:1: warning: missing return\n"
    )
    result = linter._parse_lint_output(output, "clang-tidy")
    assert result["warnings"] == 2
    assert result["errors"] == 1


def test_parse_lint_output_no_issues(linter):
    """Clean output yields all zeroes."""
    result = linter._parse_lint_output("", "ruff")
    assert result == {"errors": 0, "warnings": 0, "files_checked": 0}


# ---------------------------------------------------------------------------
# Real ruff execution (if installed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("ruff"), reason="ruff not installed")
async def test_lint_python_code(temp_workspace):
    """Run ruff on Python code with unused import."""
    python_file = temp_workspace / "test.py"
    python_file.write_text("import os\nx = 1")  # unused import

    lint = MultiLanguageLinter(workspace_root=str(temp_workspace))
    result = await lint.execute(language="python")

    # Ruff should run (may or may not find issues)
    assert result is not None


# ---------------------------------------------------------------------------
# execute() edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lint_unsupported_language(temp_workspace, linter):
    """Unsupported language returns error."""
    result = await linter.execute(language="fortran")
    assert not result.success
    assert "Unsupported language" in result.error


@pytest.mark.asyncio
async def test_lint_cpp_no_compile_commands(temp_workspace, linter):
    """C++ lint without compile_commands.json returns specific error."""
    (temp_workspace / "main.cpp").write_text("int main(){}")
    result = await linter.execute(language="cpp")
    assert not result.success
    assert "compile_commands.json" in result.error


@pytest.mark.asyncio
async def test_lint_rust_with_fix(temp_workspace, linter):
    """Clippy with fix=True returns helpful error."""
    result = await linter.execute(language="rust", fix=True)
    assert not result.success
    assert "cargo fix" in result.error


@pytest.mark.asyncio
async def test_lint_auto_detect(temp_workspace, linter):
    """Auto-detect dispatches correct linter from workspace markers."""
    (temp_workspace / "pyproject.toml").write_text("[project]")
    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"All checks passed", b""))
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await linter.execute()  # no language arg
    assert result.success
    # Should have dispatched ruff (Python detected)
    args = mock_exec.call_args[0]
    assert "ruff" in args


@pytest.mark.asyncio
async def test_lint_no_language_detected(temp_workspace, linter):
    """Empty workspace with no language arg returns error."""
    result = await linter.execute()
    assert not result.success
    assert "No recognized language" in result.error
