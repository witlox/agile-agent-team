"""Integration tests for agent code generation with runtimes."""

import pytest
import tempfile
from pathlib import Path

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.runtime import VLLMRuntime
from src.tools.agent_tools import create_tools


@pytest.mark.asyncio
async def test_agent_with_runtime_executes_task():
    """Test that an agent with a runtime can execute a coding task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir).resolve()

        # Create runtime
        runtime_config = {
            "endpoint": "mock://",  # Mock mode
            "model": "test-model",
            "tool_use_protocol": "xml",
            "max_tokens": 1000,
            "temperature": 0.7
        }

        tools = create_tools(["write_file", "read_file"], str(workspace))
        runtime = VLLMRuntime(runtime_config, tools)

        # Create agent with runtime
        agent_config = AgentConfig(
            role_id="test_agent",
            name="Test Agent",
            individual="priya_sharma",
            seniority="senior",
            specializations=["backend"],
            role_archetype="developer",
            model="test-model",
            temperature=0.7,
            max_tokens=1000
        )

        agent = BaseAgent(
            config=agent_config,
            vllm_endpoint="mock://",
            runtime=runtime
        )

        # Execute coding task
        result = await agent.execute_coding_task(
            task_description="Create a hello world function in Python",
            max_turns=5
        )

        # Verify result
        assert result["success"]
        assert len(result["files_changed"]) > 0
        assert result["turns"] >= 1


@pytest.mark.asyncio
async def test_agent_without_runtime_raises_error():
    """Test that agent without runtime cannot execute coding tasks."""
    agent_config = AgentConfig(
        role_id="test_agent",
        name="Test Agent",
        model="test-model",
        temperature=0.7,
        max_tokens=1000
    )

    agent = BaseAgent(
        config=agent_config,
        vllm_endpoint="mock://",
        runtime=None  # No runtime
    )

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="no runtime configured"):
        await agent.execute_coding_task("Write some code")
