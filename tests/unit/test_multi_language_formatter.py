"""Unit tests for multi-language formatter tool."""

import pytest
import shutil
from pathlib import Path
from src.tools.agent_tools.formatter import MultiLanguageFormatter


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("black"), reason="black not installed")
async def test_format_python_code(temp_workspace):
    """Test Black formatting on Python code."""
    python_file = temp_workspace / "test.py"
    # Poorly formatted Python code
    python_file.write_text("def foo( x,y ):return x+y")

    formatter = MultiLanguageFormatter(workspace_root=str(temp_workspace))
    result = await formatter.execute(language="python")

    # Black should succeed
    assert result.success, f"Black formatting failed: {result.error}"

    # File should be reformatted
    formatted = python_file.read_text()
    assert "def foo(x, y):" in formatted or "return x + y" in formatted


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("gofmt"), reason="gofmt not installed")
async def test_format_go_code(temp_workspace):
    """Test gofmt formatting on Go code."""
    go_file = temp_workspace / "test.go"
    go_file.write_text("package main\nfunc main(){}")

    formatter = MultiLanguageFormatter(workspace_root=str(temp_workspace))
    result = await formatter.execute(language="go")

    # gofmt should succeed
    assert result.success, f"gofmt formatting failed: {result.error}"


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("rustfmt"), reason="rustfmt not installed")
async def test_format_rust_code(temp_workspace):
    """Test rustfmt formatting on Rust code."""
    rust_file = temp_workspace / "test.rs"
    rust_file.write_text("fn main(){}")

    formatter = MultiLanguageFormatter(workspace_root=str(temp_workspace))
    result = await formatter.execute(language="rust")

    # rustfmt should succeed
    assert result.success, f"rustfmt formatting failed: {result.error}"


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("prettier"), reason="prettier not installed")
async def test_format_typescript_code(temp_workspace):
    """Test Prettier formatting on TypeScript code."""
    ts_file = temp_workspace / "test.ts"
    ts_file.write_text("const x=1;")

    formatter = MultiLanguageFormatter(workspace_root=str(temp_workspace))
    result = await formatter.execute(language="typescript")

    # Prettier should succeed
    assert result.success, f"prettier formatting failed: {result.error}"


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("clang-format"), reason="clang-format not installed")
async def test_format_cpp_code(temp_workspace):
    """Test clang-format formatting on C++ code."""
    cpp_file = temp_workspace / "test.cpp"
    cpp_file.write_text("#include<iostream>\nint main(){}")

    formatter = MultiLanguageFormatter(workspace_root=str(temp_workspace))
    result = await formatter.execute(language="cpp")

    # clang-format should succeed
    assert result.success, f"clang-format formatting failed: {result.error}"


@pytest.mark.asyncio
async def test_language_detection(temp_workspace):
    """Test language detection from file extensions."""
    from src.tools.agent_tools.test_runner_multi import LanguageDetector

    files = {
        "test.py": "python",
        "test.go": "go",
        "test.rs": "rust",
        "test.ts": "typescript",
        "test.cpp": "cpp",
    }

    for filename, expected_lang in files.items():
        file_path = temp_workspace / filename
        file_path.touch()

    # Test language detection
    detected = LanguageDetector.detect(temp_workspace)
    assert detected is not None, "Should detect at least one language"
    assert len(detected) >= 1, "Should detect multiple languages if present"
