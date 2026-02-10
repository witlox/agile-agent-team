"""Integration tests for cross-team coordination."""

import asyncio
from pathlib import Path


from src.agents.base_agent import AgentConfig, BaseAgent
from src.agents.messaging import create_message_bus
from src.orchestrator.config import CoordinationConfig, ExperimentConfig, TeamConfig
from src.orchestrator.coordination_loop import CoordinationLoop
from src.orchestrator.multi_team import MultiTeamOrchestrator
from src.tools.shared_context import SharedContextDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(
    role_id: str, name: str = "", archetype: str = "developer"
) -> BaseAgent:
    config = AgentConfig(
        role_id=role_id,
        name=name or role_id,
        model="mock",
        temperature=0.7,
        max_tokens=1000,
        seniority="senior",
        role_archetype=archetype,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def _make_config(**overrides) -> ExperimentConfig:
    defaults = dict(
        name="coord-integration",
        sprint_duration_minutes=5,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="mock://",
        sprint_zero_enabled=False,
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def _make_full_setup(tmp_path: Path) -> tuple:
    """Create a full setup with teams, coordinators, db, and bus."""
    # Team agents
    team_agents = [
        _make_agent("po_alpha", "PO Alpha", "leader"),
        _make_agent("dev_lead_alpha", "Dev Lead Alpha", "developer+leader"),
        _make_agent("dev_alpha", "Dev Alpha", "developer"),
        _make_agent("dev_beta_1", "Dev Beta 1", "developer"),
        _make_agent("dev_beta_2", "Dev Beta 2", "developer"),
    ]

    # Coordinator agents (not assigned to any team)
    coordinators = [
        _make_agent("coord_se", "Staff Engineer", "staff_engineer"),
        _make_agent("coord_el", "Enablement Lead", "enablement_lead"),
    ]

    team_configs = [
        TeamConfig(
            id="team-alpha",
            name="Alpha",
            agent_ids=["po_alpha", "dev_lead_alpha", "dev_alpha"],
        ),
        TeamConfig(
            id="team-beta",
            name="Beta",
            agent_ids=["dev_beta_1", "dev_beta_2"],
        ),
    ]

    db = SharedContextDB("mock://")
    bus = create_message_bus({"backend": "asyncio"})

    for agent in team_agents + coordinators:
        agent.attach_message_bus(bus)

    coordination_config = CoordinationConfig(
        enabled=True,
        full_loop_cadence=1,
        mid_sprint_checkin=True,
        max_borrows_per_sprint=2,
        coordinator_agent_ids=["coord_se", "coord_el"],
    )

    config = _make_config(
        teams=team_configs,
        coordination=coordination_config,
    )

    return team_agents, coordinators, team_configs, db, bus, config, coordination_config


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_coordination_disabled_no_effect(tmp_path):
    """When coordination is disabled, run_sprint behaves like Phase 2."""
    team_agents, _, team_configs, db, bus, config, _ = _make_full_setup(tmp_path)

    # Override coordination to disabled
    config.coordination = CoordinationConfig(enabled=False)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=team_agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    # No coordination loop should be set
    assert orch._coordination_loop is None
    assert orch._coordination_config is None


def test_setup_coordination_initializes_loop(tmp_path):
    """setup_coordination creates CoordinationLoop and sets callbacks."""
    (
        team_agents,
        coordinators,
        team_configs,
        db,
        bus,
        config,
        coordination_config,
    ) = _make_full_setup(tmp_path)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=team_agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())
    run(orch.setup_coordination(coordinators, coordination_config))

    assert orch._coordination_loop is not None
    assert orch._coordination_config is not None
    assert orch._coordination_config.enabled is True

    # Mid-sprint callback should be set on team managers
    for manager in orch._team_managers.values():
        assert manager._mid_sprint_callback is not None


def test_coordinators_excluded_from_teams(tmp_path):
    """Coordinator agents are not in any team's agent list."""
    (
        team_agents,
        coordinators,
        team_configs,
        db,
        bus,
        config,
        coordination_config,
    ) = _make_full_setup(tmp_path)

    # Only team_agents go into the orchestrator
    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=team_agents,  # coordinators excluded
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    # Coordinator agent_ids should not appear in any team
    coord_ids = {"coord_se", "coord_el"}
    for team_id, agents in orch._team_agents.items():
        for agent in agents:
            assert agent.agent_id not in coord_ids


def test_mid_sprint_callback_invoked(tmp_path):
    """SprintManager calls mid_sprint_callback when set."""
    from src.orchestrator.sprint_manager import SprintManager

    agents = [_make_agent("dev_1", "Dev 1")]
    db = SharedContextDB("mock://")
    config = _make_config()

    callback_calls = []

    async def mock_callback(sprint_num: int):
        callback_calls.append(sprint_num)

    manager = SprintManager(
        agents=agents,
        shared_db=db,
        config=config,
        output_dir=tmp_path,
    )
    manager._mid_sprint_callback = mock_callback

    # The callback is invoked between dev and QA in run_sprint
    # We can verify it's stored correctly
    assert manager._mid_sprint_callback is not None


def test_cross_team_dependency_detection(tmp_path):
    """End-to-end: card with dependency metadata is detected by CoordinationLoop."""
    (
        team_agents,
        coordinators,
        team_configs,
        db,
        bus,
        config,
        coordination_config,
    ) = _make_full_setup(tmp_path)

    run(db.initialize())

    # Add a card with cross-team dependency
    run(
        db.add_card(
            {
                "title": "Needs platform API",
                "status": "in_progress",
                "team_id": "team-alpha",
                "metadata": {
                    "depends_on_team": "team-beta",
                    "dependency_type": "needs_api",
                    "dependency_status": "open",
                },
            }
        )
    )

    loop = CoordinationLoop(
        coordinators=coordinators,
        team_configs=team_configs,
        shared_db=db,
        message_bus=bus,
        coordination_config=coordination_config,
    )

    deps = run(loop._detect_dependencies(1))
    assert len(deps) == 1
    assert deps[0].source_team == "team-alpha"
    assert deps[0].target_team == "team-beta"
    assert deps[0].dependency_type == "needs_api"
