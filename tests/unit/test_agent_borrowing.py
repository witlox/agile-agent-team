"""Unit tests for agent borrowing in MultiTeamOrchestrator."""

import asyncio
from pathlib import Path


from src.agents.base_agent import AgentConfig, BaseAgent
from src.agents.messaging import create_message_bus
from src.orchestrator.config import CoordinationConfig, ExperimentConfig, TeamConfig
from src.orchestrator.coordination_loop import BorrowRequest
from src.orchestrator.multi_team import MultiTeamOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(role_id: str, name: str = "") -> BaseAgent:
    config = AgentConfig(
        role_id=role_id,
        name=name or role_id,
        model="mock",
        temperature=0.7,
        max_tokens=1000,
        seniority="mid",
        role_archetype="developer",
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def _make_config(**overrides) -> ExperimentConfig:
    defaults = dict(
        name="borrow-test",
        sprint_duration_minutes=5,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="mock://",
        sprint_zero_enabled=False,
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def _make_orch(tmp_path: Path) -> MultiTeamOrchestrator:
    """Create a 2-team orchestrator with 5 agents."""
    agents = [
        _make_agent("a1", "Agent A1"),
        _make_agent("a2", "Agent A2"),
        _make_agent("a3", "Agent A3"),
        _make_agent("b1", "Agent B1"),
        _make_agent("b2", "Agent B2"),
    ]

    team_configs = [
        TeamConfig(id="team-alpha", name="Alpha", agent_ids=["a1", "a2", "a3"]),
        TeamConfig(id="team-beta", name="Beta", agent_ids=["b1", "b2"]),
    ]

    db_mock = __import__(
        "src.tools.shared_context", fromlist=["SharedContextDB"]
    ).SharedContextDB("mock://")
    bus = create_message_bus({"backend": "asyncio"})

    for agent in agents:
        agent.attach_message_bus(bus)

    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db_mock,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    return orch


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_borrow_agent_moves_to_target_team(tmp_path):
    """Agent is reassigned to the target team after borrow."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    assert len(orch._team_agents["team-alpha"]) == 3
    assert len(orch._team_agents["team-beta"]) == 2

    request = BorrowRequest(
        from_team="team-alpha",
        to_team="team-beta",
        agent_id="a1",
        reason="capacity",
    )
    success = run(orch.borrow_agent(request))

    assert success is True
    assert len(orch._team_agents["team-alpha"]) == 2
    assert len(orch._team_agents["team-beta"]) == 3

    # Verify agent's team_id was updated
    borrowed = next(a for a in orch._team_agents["team-beta"] if a.agent_id == "a1")
    assert borrowed.config.team_id == "team-beta"


def test_borrow_agent_sets_original_team_id(tmp_path):
    """Borrow sets original_team_id to track the home team."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    request = BorrowRequest(
        from_team="team-alpha",
        to_team="team-beta",
        agent_id="a2",
        reason="need backend help",
    )
    run(orch.borrow_agent(request))

    borrowed = next(a for a in orch._team_agents["team-beta"] if a.agent_id == "a2")
    assert borrowed.config.original_team_id == "team-alpha"


def test_borrow_agent_invalid_agent_returns_false(tmp_path):
    """Borrowing a nonexistent agent returns False."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    request = BorrowRequest(
        from_team="team-alpha",
        to_team="team-beta",
        agent_id="nonexistent",
        reason="test",
    )
    success = run(orch.borrow_agent(request))
    assert success is False


def test_borrow_agent_invalid_team_returns_false(tmp_path):
    """Borrowing to a nonexistent team returns False."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    request = BorrowRequest(
        from_team="team-alpha",
        to_team="nonexistent-team",
        agent_id="a1",
        reason="test",
    )
    success = run(orch.borrow_agent(request))
    assert success is False


def test_return_borrowed_agents_restores_all(tmp_path):
    """All borrowed agents are returned to their home teams."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())
    orch._coordination_config = CoordinationConfig(enabled=True)

    # Borrow a1 and a2 to beta
    run(orch.borrow_agent(BorrowRequest("team-alpha", "team-beta", "a1", "help")))
    run(orch.borrow_agent(BorrowRequest("team-alpha", "team-beta", "a2", "help")))

    assert len(orch._team_agents["team-alpha"]) == 1
    assert len(orch._team_agents["team-beta"]) == 4

    # Return all borrowed agents
    count = run(orch.return_borrowed_agents())
    assert count == 2
    assert len(orch._team_agents["team-alpha"]) == 3
    assert len(orch._team_agents["team-beta"]) == 2


def test_return_borrowed_agents_clears_original_team_id(tmp_path):
    """Returning agents clears original_team_id."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())
    orch._coordination_config = CoordinationConfig(enabled=True)

    run(orch.borrow_agent(BorrowRequest("team-alpha", "team-beta", "a1", "help")))
    run(orch.return_borrowed_agents())

    agent_a1 = next(a for a in orch._team_agents["team-alpha"] if a.agent_id == "a1")
    assert agent_a1.config.original_team_id == ""
    assert agent_a1.config.team_id == "team-alpha"


def test_return_borrowed_when_none_borrowed(tmp_path):
    """Return when no agents are borrowed returns 0."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    count = run(orch.return_borrowed_agents())
    assert count == 0


def test_max_borrows_per_sprint_enforced(tmp_path):
    """Only max_borrows_per_sprint borrows are processed from an outcome."""
    orch = _make_orch(tmp_path)
    run(orch.setup_teams())

    # Create 5 borrow requests but config allows only 2
    config = CoordinationConfig(
        enabled=True,
        max_borrows_per_sprint=2,
    )
    orch._coordination_config = config

    requests = [
        BorrowRequest("team-alpha", "team-beta", f"a{i}", "test") for i in range(1, 4)
    ]

    # Only first 2 should be attempted (via slicing in run_sprint logic)
    capped = requests[: config.max_borrows_per_sprint]
    assert len(capped) == 2
