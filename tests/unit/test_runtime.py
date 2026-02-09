"""Tests for agent runtime system."""

import pytest
import tempfile

from src.tools.agent_tools import create_tools
from src.agents.runtime import VLLMRuntime


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vllm_runtime(temp_workspace):
    """Create a VLLMRuntime in mock mode."""
    config = {
        "endpoint": "mock://",  # Mock mode
        "model": "test-model",
        "tool_use_protocol": "xml",
        "max_tokens": 1000,
        "temperature": 0.7,
    }

    tools = create_tools(["read_file", "write_file"], temp_workspace)

    return VLLMRuntime(config, tools)


@pytest.mark.asyncio
async def test_tool_execution(temp_workspace):
    """Test that tools can be executed."""
    from pathlib import Path

    # Use resolved path for workspace
    workspace = Path(temp_workspace).resolve()
    tools = create_tools(["write_file", "read_file"], str(workspace))

    # Write a file
    write_tool = tools[0]
    result = await write_tool.execute(path="test.txt", content="Hello, world!")

    assert result.success
    assert "test.txt" in result.files_changed

    # Read it back
    read_tool = tools[1]
    result = await read_tool.execute(path="test.txt")

    assert result.success
    assert result.output == "Hello, world!"


@pytest.mark.asyncio
async def test_tool_security(temp_workspace):
    """Test that tools enforce workspace boundaries."""
    tools = create_tools(["read_file"], temp_workspace)

    read_tool = tools[0]

    # Try to escape workspace
    result = await read_tool.execute(path="../../../etc/passwd")

    assert not result.success
    assert "escapes workspace" in result.error.lower()


@pytest.mark.asyncio
async def test_vllm_runtime_mock_mode(vllm_runtime):
    """Test VLLMRuntime in mock mode."""
    result = await vllm_runtime.execute_task(
        system_prompt="You are a helpful coding assistant.",
        user_message="Write a hello world function",
        max_turns=5,
    )

    assert result.success
    assert result.turns >= 1
    assert len(result.files_changed) > 0  # Mock creates some file
    assert "example.py" in result.files_changed[0]  # File contains "example.py"


def test_tool_factory():
    """Test tool factory creates correct tools."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create tools by name
        tools = create_tools(["read_file", "write_file", "bash"], tmpdir)

        assert len(tools) == 3
        assert tools[0].name == "read_file"
        assert tools[1].name == "write_file"
        assert tools[2].name == "bash"

        # Create tools using a set
        tools = create_tools(["filesystem"], tmpdir)
        tool_names = [t.name for t in tools]

        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names


def test_tool_parameters_schema():
    """Test that tools have valid parameter schemas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tools = create_tools(["write_file"], tmpdir)

        write_tool = tools[0]
        params = write_tool.parameters

        assert params["type"] == "object"
        assert "path" in params["properties"]
        assert "content" in params["properties"]
        assert "path" in params["required"]
