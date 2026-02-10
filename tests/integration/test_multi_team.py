"""Integration tests for multi-team orchestration."""

import asyncio


from src.agents.base_agent import AgentConfig, BaseAgent
from src.agents.messaging import create_message_bus
from src.orchestrator.backlog import Backlog
from src.orchestrator.config import ExperimentConfig, TeamConfig
from src.orchestrator.multi_team import MultiTeamOrchestrator
from src.tools.shared_context import SharedContextDB


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
        name="multi-team-test",
        sprint_duration_minutes=5,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="mock://",
        sprint_zero_enabled=False,
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def _make_teams() -> tuple:
    """Create a 2-team setup with agents, configs, bus, and db."""
    agents = [
        _make_agent("alex_senior_po", "PO"),
        _make_agent("ahmed_senior_dev_lead", "Dev Lead"),
        _make_agent("marcus_mid_backend", "Backend Dev"),
        _make_agent("priya_senior_devops", "DevOps"),
        _make_agent("elena_mid_frontend", "Frontend Dev"),
    ]

    team_configs = [
        TeamConfig(
            id="team-alpha",
            name="Alpha",
            team_type="stream_aligned",
            agent_ids=[
                "alex_senior_po",
                "ahmed_senior_dev_lead",
                "marcus_mid_backend",
            ],
        ),
        TeamConfig(
            id="team-beta",
            name="Beta",
            team_type="platform",
            agent_ids=["priya_senior_devops", "elena_mid_frontend"],
        ),
    ]

    db = SharedContextDB("mock://")
    bus = create_message_bus({"backend": "asyncio"})

    for agent in agents:
        agent.attach_message_bus(bus)

    return agents, team_configs, db, bus


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_multi_team_setup_partitions_agents(tmp_path):
    """setup_teams assigns agents to correct teams."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    assert len(orch._team_agents["team-alpha"]) == 3
    assert len(orch._team_agents["team-beta"]) == 2

    # Check team_id was set on agents
    alpha_ids = {a.config.team_id for a in orch._team_agents["team-alpha"]}
    assert alpha_ids == {"team-alpha"}


def test_multi_team_isolated_kanban(tmp_path):
    """Team A cards are invisible to team B's kanban board."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    mgr_alpha = orch._team_managers["team-alpha"]
    mgr_beta = orch._team_managers["team-beta"]

    # Add card to alpha
    run(
        mgr_alpha.kanban.add_card(
            {"title": "Alpha task", "status": "ready", "sprint": 1}
        )
    )

    # Alpha sees it
    snap_a = run(mgr_alpha.kanban.get_snapshot())
    assert len(snap_a["ready"]) == 1

    # Beta does not
    snap_b = run(mgr_beta.kanban.get_snapshot())
    assert len(snap_b["ready"]) == 0


def test_multi_team_portfolio_distribution(tmp_path):
    """Stories from portfolio backlog are distributed to teams without own backlogs."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    stories = [
        {"id": f"US-{i:03d}", "title": f"Story {i}", "priority": i, "story_points": 3}
        for i in range(1, 7)
    ]
    portfolio = Backlog.from_stories(stories, product_name="Test")

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=portfolio,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())
    run(orch.distribute_portfolio_stories(1))

    # Both teams should have backlogs assigned
    assert orch._team_managers["team-alpha"].backlog is not None
    assert orch._team_managers["team-beta"].backlog is not None

    # Stories distributed (3 per team by default)
    alpha_remaining = orch._team_managers["team-alpha"].backlog.remaining
    beta_remaining = orch._team_managers["team-beta"].backlog.remaining
    assert alpha_remaining + beta_remaining == 6


def test_multi_team_team_specific_backlog(tmp_path):
    """Team with own backlog_path uses it instead of portfolio."""
    agents, team_configs, db, bus = _make_teams()

    # Create a team-specific backlog file
    backlog_file = tmp_path / "alpha_backlog.yaml"
    backlog_file.write_text(
        "product:\n  name: Alpha Product\n  description: test\nstories:\n"
        "  - id: 'A-001'\n    title: 'Alpha Story'\n    priority: 1\n    story_points: 3\n"
    )

    team_configs[0].backlog_path = str(backlog_file)

    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    # Alpha has its own backlog
    assert orch._team_backlogs["team-alpha"] is not None
    assert orch._team_backlogs["team-alpha"].product_name == "Alpha Product"

    # Beta has no backlog
    assert orch._team_backlogs["team-beta"] is None


def test_multi_team_shared_message_bus(tmp_path):
    """Agents on different teams share the same message bus."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    # Cross-team messaging: alpha agent sends to beta agent
    alpha_agent = orch._team_agents["team-alpha"][0]
    beta_agent = orch._team_agents["team-beta"][0]

    msg = run(alpha_agent.send_message(beta_agent.agent_id, {"text": "hello"}))
    assert msg is not None

    received = run(beta_agent.receive_message(timeout=1.0))
    assert received is not None
    assert received.content["text"] == "hello"


def test_multi_team_output_directories(tmp_path):
    """Per-team output subdirectories are created."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    assert (tmp_path / "team-alpha").is_dir()
    assert (tmp_path / "team-beta").is_dir()


def test_multi_team_metrics_per_team(tmp_path):
    """Each team has separate SprintManagers with their own team_id."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    assert orch._team_managers["team-alpha"].team_id == "team-alpha"
    assert orch._team_managers["team-beta"].team_id == "team-beta"
    assert orch._team_managers["team-alpha"].kanban.team_id == "team-alpha"
    assert orch._team_managers["team-beta"].kanban.team_id == "team-beta"


def test_multi_team_generate_final_report(tmp_path):
    """generate_final_report produces a portfolio report."""
    agents, team_configs, db, bus = _make_teams()
    config = _make_config(teams=team_configs)

    orch = MultiTeamOrchestrator(
        team_configs=team_configs,
        all_agents=agents,
        shared_db=db,
        experiment_config=config,
        portfolio_backlog=None,
        message_bus=bus,
        output_dir=tmp_path,
    )
    run(orch.setup_teams())

    # Simulate some results
    orch._team_results["team-alpha"] = [
        {"sprint": 1, "velocity": 8, "features_completed": 3}
    ]
    orch._team_results["team-beta"] = [
        {"sprint": 1, "velocity": 5, "features_completed": 2}
    ]

    run(orch.generate_final_report())

    report_path = tmp_path / "final_report.json"
    assert report_path.exists()

    import json

    report = json.loads(report_path.read_text())
    assert report["mode"] == "multi_team"
    assert "team-alpha" in report["teams"]
    assert report["portfolio"]["total_features"] == 5
    assert report["portfolio"]["num_teams"] == 2
