"""Qualification tests for agent configuration, prompt loading, and factory."""

from pathlib import Path

import pytest

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.agent_factory import AgentFactory


TEAM_CONFIG_DIR = Path(__file__).parent.parent.parent / "team_config"


@pytest.fixture
def dev_lead_config():
    """Config using new compositional structure."""
    return AgentConfig(
        role_id="ahmed_senior_dev_lead",
        name="Ahmed Hassan (Development Lead)",
        individual="ahmed_hassan",
        seniority="senior",
        specializations=["backend", "distributed_systems"],
        role_archetype="developer+leader",
        demographics={"pronouns": "he/him", "cultural_background": "Egyptian"},
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
    )


def test_prompt_loading(dev_lead_config):
    """Prompt should include content from base, archetype, seniority, specializations, and individual."""
    agent = BaseAgent(dev_lead_config, vllm_endpoint="mock://")
    prompt = agent.prompt
    assert prompt  # non-empty
    # Should contain layered content
    assert len(prompt) > 1000  # Compositional prompts are large
    # Check for leader content
    assert "leader" in prompt.lower() or "leadership" in prompt.lower()


def test_prompt_loading_minimal():
    """Agent with minimal config loads base agent content."""
    config = AgentConfig(
        role_id="minimal_agent",
        name="Minimal Agent",
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
    )
    agent = BaseAgent(config, vllm_endpoint="mock://")
    assert agent.prompt  # non-empty
    # Should at least load base agent
    assert (
        "agile development team" in agent.prompt.lower()
        or "base agent" in agent.prompt.lower()
    )


def test_agent_config_creation():
    """AgentFactory creates AgentConfig from new compositional structure."""
    factory = AgentFactory(
        str(TEAM_CONFIG_DIR),
        "mock://",
        agent_model_configs={
            "test_agent": {
                "name": "Test Agent",
                "individual": "priya_sharma",
                "seniority": "senior",
                "specializations": ["devops", "cloud_architecture"],
                "role_archetype": "developer",
                "demographics": {
                    "pronouns": "she/her",
                    "cultural_background": "Indian",
                },
                "model": "TestModel",
                "temperature": 0.5,
                "max_tokens": 512,
            }
        },
    )
    config = factory._create_agent_config(
        "test_agent", factory.agent_model_configs["test_agent"]
    )
    assert config.role_id == "test_agent"
    assert config.individual == "priya_sharma"
    assert config.seniority == "senior"
    assert config.specializations == ["devops", "cloud_architecture"]
    assert config.model == "TestModel"
    assert config.temperature == 0.5
    assert config.max_tokens == 512


@pytest.mark.asyncio
async def test_all_agents_created():
    """AgentFactory creates agents from agent_model_configs."""
    # Create a sample config with 3 agents
    agent_configs = {
        "agent1": {
            "name": "Agent 1",
            "individual": "priya_sharma",
            "seniority": "senior",
            "specializations": ["devops"],
            "role_archetype": "developer",
            "demographics": {},
            "model": "mock-model",
            "temperature": 0.7,
            "max_tokens": 100,
        },
        "agent2": {
            "name": "Agent 2",
            "individual": "jamie_rodriguez",
            "seniority": "junior",
            "specializations": ["backend"],
            "role_archetype": "developer",
            "demographics": {},
            "model": "mock-model",
            "temperature": 0.7,
            "max_tokens": 100,
        },
        "agent3": {
            "name": "Agent 3",
            "individual": "yuki_tanaka",
            "seniority": "senior",
            "specializations": ["test_automation"],
            "role_archetype": "tester",
            "demographics": {},
            "model": "mock-model",
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }
    factory = AgentFactory(
        str(TEAM_CONFIG_DIR), "mock://", agent_model_configs=agent_configs
    )
    agents = await factory.create_all_agents()
    assert len(agents) == 3
    assert all(isinstance(agent, BaseAgent) for agent in agents)


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
