"""Shared pytest fixtures for all test suites."""

import pytest
import pytest_asyncio

from src.tools.shared_context import SharedContextDB
from src.tools.kanban import KanbanBoard
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest_asyncio.fixture
async def mock_db():
    """In-memory mock database (SharedContextDB with mock:// URL)."""
    db = SharedContextDB("mock://")
    await db.initialize()
    return db


@pytest_asyncio.fixture
async def mock_kanban(mock_db):
    """KanbanBoard backed by the in-memory mock database."""
    board = KanbanBoard(mock_db, wip_limits={"in_progress": 4, "review": 2})
    return board


@pytest.fixture
def mock_agent_config():
    """AgentConfig for a mock agent."""
    return AgentConfig(
        role_id="dev_lead",
        name="Test Lead",
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture(autouse=True)
def enable_mock_llm(monkeypatch):
    """Ensure MOCK_LLM is set for all tests."""
    monkeypatch.setenv("MOCK_LLM", "true")


@pytest.fixture
def mock_agent(mock_agent_config):
    """BaseAgent in mock mode with an empty prompt path."""
    return BaseAgent(mock_agent_config, vllm_endpoint="mock://")


def make_agent(role_id: str) -> BaseAgent:
    """Helper to create a mock agent with a given role_id."""
    config = AgentConfig(
        role_id=role_id,
        name=role_id,
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
    )
    return BaseAgent(config, vllm_endpoint="mock://")
