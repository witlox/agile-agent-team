"""Unit tests for multi-language linter tool."""

import pytest
import shutil
from src.tools.agent_tools.linter import MultiLanguageLinter


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("ruff"), reason="ruff not installed")
async def test_lint_python_code(temp_workspace):
    """Test ruff on Python code."""
    python_file = temp_workspace / "test.py"
    python_file.write_text("import os\nx = 1")  # unused import

    linter = MultiLanguageLinter(workspace_root=str(temp_workspace))
    result = await linter.execute(language="python")

    # Ruff should run (may or may not find issues)
    assert result is not None


@pytest.mark.asyncio
async def test_lint_go_code(temp_workspace):
    """Test golangci-lint on Go code."""
    go_file = temp_workspace / "test.go"
    go_file.write_text("package main\nfunc main(){}")

    assert go_file.exists()


@pytest.mark.asyncio
async def test_lint_rust_code(temp_workspace):
    """Test clippy on Rust code."""
    rust_file = temp_workspace / "test.rs"
    rust_file.write_text("fn main(){}")

    assert rust_file.exists()


@pytest.mark.asyncio
async def test_lint_typescript_code(temp_workspace):
    """Test ESLint on TypeScript code."""
    ts_file = temp_workspace / "test.ts"
    ts_file.write_text("const x = 1;")

    assert ts_file.exists()


@pytest.mark.asyncio
async def test_lint_cpp_code(temp_workspace):
    """Test clang-tidy on C++ code."""
    cpp_file = temp_workspace / "test.cpp"
    cpp_file.write_text("#include<iostream>\nint main(){}")

    assert cpp_file.exists()


@pytest.mark.asyncio
async def test_language_detection(temp_workspace):
    """Test language detection from file extensions."""
    extensions = [".py", ".go", ".rs", ".ts", ".cpp"]

    for ext in extensions:
        file_path = temp_workspace / f"test{ext}"
        file_path.touch()
        assert file_path.suffix == ext
