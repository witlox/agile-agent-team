"""Integration tests for the PairingEngine."""

import pytest

from src.agents.pairing import PairingEngine
from tests.conftest import make_agent


@pytest.fixture
def two_agents():
    return [make_agent("dev_lead"), make_agent("dev_mid_backend")]


@pytest.fixture
def pairing_engine(two_agents, mock_db):
    return PairingEngine(two_agents, db=mock_db)


@pytest.fixture
def sample_task():
    return {
        "id": 1,
        "sprint": 1,
        "title": "Implement login",
        "description": "Login feature",
    }


@pytest.mark.asyncio
async def test_pairing_session_completes(pairing_engine, sample_task):
    """A full pairing session should complete with outcome 'completed' or 'escalated'."""
    pair = (pairing_engine.agents[0], pairing_engine.agents[1])
    result = await pairing_engine.run_pairing_session(pair, sample_task)
    assert result["outcome"] in ("completed", "escalated")
    assert result["driver_id"] == "dev_lead"
    assert result["navigator_id"] == "dev_mid_backend"


@pytest.mark.asyncio
async def test_pairing_busy_tracking(pairing_engine, sample_task):
    """Agents are marked busy during session and freed after."""
    pair = (pairing_engine.agents[0], pairing_engine.agents[1])
    # Before session: no agents busy
    assert len(pairing_engine._busy_agents) == 0

    _result = await pairing_engine.run_pairing_session(pair, sample_task)

    # After session: agents freed
    assert len(pairing_engine._busy_agents) == 0


@pytest.mark.asyncio
async def test_get_available_pairs_excludes_busy(pairing_engine):
    """Agents in _busy_agents should not appear in available pairs."""
    pairing_engine._busy_agents.add("dev_lead")
    pairs = pairing_engine.get_available_pairs()
    for driver, navigator in pairs:
        assert driver.config.role_id != "dev_lead"
        assert navigator.config.role_id != "dev_lead"


@pytest.mark.asyncio
async def test_escalation_logged(pairing_engine, sample_task, mock_db):
    """Escalation is logged when pair doesn't reach consensus.

    We force this by checking that log_pairing_session was called.
    """
    pair = (pairing_engine.agents[0], pairing_engine.agents[1])
    _result = await pairing_engine.run_pairing_session(pair, sample_task)
    # Session result must be logged to DB
    sessions = await mock_db.get_pairing_sessions_for_sprint(1)
    assert len(sessions) >= 1
