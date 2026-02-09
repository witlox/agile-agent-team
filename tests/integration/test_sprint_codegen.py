"""Integration test for sprint manager with code generation."""

import pytest
import tempfile
from pathlib import Path

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.runtime import VLLMRuntime
from src.tools.agent_tools import create_tools
from src.tools.shared_context import SharedContextDB
from src.orchestrator.sprint_manager import SprintManager
from src.orchestrator.config import ExperimentConfig


@pytest.mark.asyncio
async def test_sprint_manager_with_codegen_pairing_engine():
    """Test that sprint manager uses CodeGenPairingEngine when agents have runtimes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir).resolve()

        # Create two agents with runtimes
        agents = []
        for i in range(2):
            runtime_config = {
                "endpoint": "mock://",
                "model": "test-model",
                "tool_use_protocol": "xml",
                "max_tokens": 1000,
                "temperature": 0.7,
            }
            tools = create_tools(["write_file", "read_file"], str(workspace))
            runtime = VLLMRuntime(runtime_config, tools)

            agent_config = AgentConfig(
                role_id=f"dev_{i}",
                name=f"Developer {i}",
                individual="priya_sharma",
                seniority="senior",
                specializations=["backend"],
                role_archetype="developer",
                model="test-model",
                temperature=0.7,
                max_tokens=1000,
            )

            agent = BaseAgent(
                config=agent_config, vllm_endpoint="mock://", runtime=runtime
            )
            agents.append(agent)

        # Create minimal config
        config = ExperimentConfig(
            name="test-experiment",
            sprint_duration_minutes=1,
            database_url="mock://",
            team_config_dir="team_config",
            vllm_endpoint="mock://",
            tools_workspace_root=str(workspace),
        )

        # Create shared DB
        db = SharedContextDB("mock://")

        # Create sprint manager
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        manager = SprintManager(
            agents=agents, shared_db=db, config=config, output_dir=output_dir
        )

        # Verify CodeGenPairingEngine is used
        from src.agents.pairing_codegen import CodeGenPairingEngine

        assert isinstance(manager.pairing_engine, CodeGenPairingEngine)

        # Verify workspace manager is configured
        assert manager.workspace_manager is not None
        assert manager.workspace_manager.base_dir == workspace


@pytest.mark.asyncio
async def test_sprint_manager_without_runtimes_uses_legacy_pairing():
    """Test that sprint manager uses PairingEngine when agents have no runtimes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create agents WITHOUT runtimes
        agents = []
        for i in range(2):
            agent_config = AgentConfig(
                role_id=f"dev_{i}",
                name=f"Developer {i}",
                model="test-model",
                temperature=0.7,
                max_tokens=1000,
            )

            agent = BaseAgent(
                config=agent_config, vllm_endpoint="mock://", runtime=None  # No runtime
            )
            agents.append(agent)

        # Create minimal config
        config = ExperimentConfig(
            name="test-experiment",
            sprint_duration_minutes=1,
            database_url="mock://",
            team_config_dir="team_config",
            vllm_endpoint="mock://",
        )

        # Create shared DB
        db = SharedContextDB("mock://")

        # Create sprint manager
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        manager = SprintManager(
            agents=agents, shared_db=db, config=config, output_dir=output_dir
        )

        # Verify PairingEngine is used (not CodeGenPairingEngine)
        from src.agents.pairing import PairingEngine
        from src.agents.pairing_codegen import CodeGenPairingEngine

        assert isinstance(manager.pairing_engine, PairingEngine)
        assert not isinstance(manager.pairing_engine, CodeGenPairingEngine)
