"""Qualification tests for agent configuration, prompt loading, and factory."""

import os
from pathlib import Path

import pytest

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.agent_factory import AgentFactory


TEAM_CONFIG_DIR = Path(__file__).parent.parent.parent / "team_config"


def _dev_lead_path() -> str:
    return str(TEAM_CONFIG_DIR / "02_individuals" / "dev_lead.md")


@pytest.fixture
def dev_lead_config():
    return AgentConfig(
        role_id="dev_lead",
        name="Dev Lead",
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
        prompt_path=_dev_lead_path(),
    )


def test_prompt_loading(dev_lead_config):
    """Prompt should include content from base, archetype, and individual profile."""
    agent = BaseAgent(dev_lead_config, vllm_endpoint="mock://")
    prompt = agent.prompt
    assert prompt  # non-empty
    # Base agent content
    assert "agile development team" in prompt.lower() or "base agent" in prompt.lower()
    # Individual profile content
    assert "lead" in prompt.lower()


def test_prompt_loading_no_path():
    """Agent with empty prompt_path returns a default prompt."""
    config = AgentConfig(
        role_id="unknown",
        name="Unknown",
        model="x",
        temperature=0.7,
        max_tokens=100,
        prompt_path="",
    )
    agent = BaseAgent(config, vllm_endpoint="mock://")
    assert agent.prompt  # non-empty default


def test_agent_config_parsing():
    """AgentFactory parses dev_lead.md correctly."""
    factory = AgentFactory(
        str(TEAM_CONFIG_DIR),
        "mock://",
        agent_model_configs={
            "dev_lead": {"model": "TestModel", "temperature": 0.5, "max_tokens": 512}
        },
    )
    config = factory._parse_agent_config(TEAM_CONFIG_DIR / "02_individuals" / "dev_lead.md")
    assert config.role_id == "dev_lead"
    assert config.model == "TestModel"
    assert config.temperature == 0.5
    assert config.max_tokens == 512
    assert config.prompt_path.endswith("dev_lead.md")


@pytest.mark.asyncio
async def test_all_agents_created():
    """AgentFactory should create 11 agents from team_config/02_individuals/."""
    factory = AgentFactory(str(TEAM_CONFIG_DIR), "mock://")
    agents = await factory.create_all_agents()
    assert len(agents) == 11


@pytest.mark.asyncio
async def test_mock_generate(dev_lead_config):
    """With MOCK_LLM=true, generate() returns a non-empty string."""
    agent = BaseAgent(dev_lead_config, vllm_endpoint="mock://")
    response = await agent.generate("Hello, team!")
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_conversation_history_grows(dev_lead_config):
    """Each generate() call appends to conversation_history."""
    agent = BaseAgent(dev_lead_config, vllm_endpoint="mock://")
    assert len(agent.conversation_history) == 0
    await agent.generate("msg1")
    assert len(agent.conversation_history) == 2  # user + assistant
    await agent.generate("msg2")
    assert len(agent.conversation_history) == 4
