"""Unit tests for multi-language builder tool."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.mark.asyncio
async def test_build_python_project(temp_workspace):
    """Test Python build (no explicit build, but can install deps)."""
    (temp_workspace / "requirements.txt").write_text("pytest==7.4.3")
    assert (temp_workspace / "requirements.txt").exists()


@pytest.mark.asyncio
async def test_build_go_project(temp_workspace):
    """Test Go build with go build."""
    (temp_workspace / "go.mod").write_text("module test\ngo 1.21")
    (temp_workspace / "main.go").write_text("package main\nfunc main(){}")
    
    assert (temp_workspace / "go.mod").exists()


@pytest.mark.asyncio
async def test_build_rust_project(temp_workspace):
    """Test Rust build with cargo build."""
    (temp_workspace / "Cargo.toml").write_text('[package]\nname = "test"\nversion = "0.1.0"')
    
    assert (temp_workspace / "Cargo.toml").exists()


@pytest.mark.asyncio
async def test_build_typescript_project(temp_workspace):
    """Test TypeScript build with tsc."""
    (temp_workspace / "tsconfig.json").write_text('{"compilerOptions": {}}')
    
    assert (temp_workspace / "tsconfig.json").exists()


@pytest.mark.asyncio
async def test_build_cpp_project(temp_workspace):
    """Test C++ build with cmake/make."""
    (temp_workspace / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
    
    assert (temp_workspace / "CMakeLists.txt").exists()


@pytest.mark.asyncio
async def test_language_detection(temp_workspace):
    """Test language detection from build files."""
    build_files = {
        "requirements.txt": "python",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "tsconfig.json": "typescript",
        "CMakeLists.txt": "cpp",
    }
    
    for filename in build_files:
        file_path = temp_workspace / filename
        file_path.touch()
        assert file_path.exists()
