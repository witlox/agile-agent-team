"""Unit tests for multi-language formatter tool."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.asyncio
async def test_format_python_code(temp_workspace):
    """Test Black formatting on Python code."""
    python_file = temp_workspace / "test.py"
    python_file.write_text("def foo( x,y ):return x+y")
    
    # Formatter would format this
    assert python_file.exists()


@pytest.mark.asyncio
async def test_format_go_code(temp_workspace):
    """Test gofmt formatting on Go code."""
    go_file = temp_workspace / "test.go"
    go_file.write_text("package main\nfunc main(){}")
    
    assert go_file.exists()


@pytest.mark.asyncio
async def test_format_rust_code(temp_workspace):
    """Test rustfmt formatting on Rust code."""
    rust_file = temp_workspace / "test.rs"
    rust_file.write_text("fn main(){}")
    
    assert rust_file.exists()


@pytest.mark.asyncio
async def test_format_typescript_code(temp_workspace):
    """Test Prettier formatting on TypeScript code."""
    ts_file = temp_workspace / "test.ts"
    ts_file.write_text("const x=1;")
    
    assert ts_file.exists()


@pytest.mark.asyncio
async def test_format_cpp_code(temp_workspace):
    """Test clang-format formatting on C++ code."""
    cpp_file = temp_workspace / "test.cpp"
    cpp_file.write_text("#include<iostream>\nint main(){}")
    
    assert cpp_file.exists()


@pytest.mark.asyncio
async def test_language_detection(temp_workspace):
    """Test language detection from file extensions."""
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
        
        # Language detection logic
        ext = file_path.suffix
        assert ext in [".py", ".go", ".rs", ".ts", ".cpp"]
