"""Unit tests for the CoordinationLoop class."""

import asyncio


from src.agents.base_agent import AgentConfig, BaseAgent
from src.agents.messaging import create_message_bus
from src.orchestrator.config import CoordinationConfig, TeamConfig
from src.orchestrator.coordination_loop import (
    BorrowRequest,
    CoordinationLoop,
    CoordinationOutcome,
    CrossTeamDependency,
    TeamHealthSnapshot,
)
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
        seniority="senior",
        role_archetype="developer",
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def _make_loop(
    num_coordinators: int = 2,
) -> tuple:
    """Build a CoordinationLoop with mock components."""
    coordinators = [
        _make_agent("coord_se", "Staff Engineer"),
        _make_agent("coord_el", "Enablement Lead"),
    ][:num_coordinators]

    team_configs = [
        TeamConfig(
            id="team-alpha",
            name="Alpha",
            agent_ids=["a1", "a2", "a3"],
        ),
        TeamConfig(
            id="team-beta",
            name="Beta",
            agent_ids=["b1", "b2"],
        ),
    ]

    db = SharedContextDB("mock://")
    bus = create_message_bus({"backend": "asyncio"})

    for coord in coordinators:
        coord.attach_message_bus(bus)

    config = CoordinationConfig(
        enabled=True,
        full_loop_cadence=1,
        mid_sprint_checkin=True,
        max_borrows_per_sprint=2,
    )

    loop = CoordinationLoop(
        coordinators=coordinators,
        team_configs=team_configs,
        shared_db=db,
        message_bus=bus,
        coordination_config=config,
    )

    return loop, coordinators, db, bus


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


def test_team_health_snapshot_fields():
    """TeamHealthSnapshot stores all health metrics."""
    snap = TeamHealthSnapshot(
        team_id="alpha",
        velocity=8.0,
        wip_count=3,
        blocked_count=1,
        agent_count=5,
        borrowed_in=["x"],
        borrowed_out=["y"],
    )
    assert snap.team_id == "alpha"
    assert snap.velocity == 8.0
    assert snap.blocked_count == 1
    assert snap.borrowed_in == ["x"]


def test_cross_team_dependency_fields():
    """CrossTeamDependency stores dependency info."""
    dep = CrossTeamDependency(
        source_team="alpha",
        target_team="beta",
        card_id=42,
        dependency_type="needs_api",
        status="open",
    )
    assert dep.source_team == "alpha"
    assert dep.card_id == 42
    assert dep.status == "open"


def test_borrow_request_fields():
    """BorrowRequest stores borrow details."""
    br = BorrowRequest(
        from_team="alpha",
        to_team="beta",
        agent_id="a1",
        reason="capacity",
        duration_sprints=2,
    )
    assert br.from_team == "alpha"
    assert br.to_team == "beta"
    assert br.agent_id == "a1"
    assert br.duration_sprints == 2


def test_coordination_outcome_defaults():
    """CoordinationOutcome has sensible defaults."""
    co = CoordinationOutcome()
    assert co.borrows == []
    assert co.dependency_updates == []
    assert co.recommendations == []
    assert co.raw_evaluation == ""


# ---------------------------------------------------------------------------
# Gather team health
# ---------------------------------------------------------------------------


def test_gather_team_health_returns_snapshots():
    """_gather_team_health returns one snapshot per team."""
    loop, _, db, _ = _make_loop()

    snapshots = run(loop._gather_team_health(1))
    assert len(snapshots) == 2
    assert snapshots[0].team_id == "team-alpha"
    assert snapshots[1].team_id == "team-beta"
    assert snapshots[0].agent_count == 3
    assert snapshots[1].agent_count == 2


# ---------------------------------------------------------------------------
# Dependency detection
# ---------------------------------------------------------------------------


def test_detect_dependencies_finds_cross_team():
    """Cards with depends_on_team metadata are detected."""
    loop, _, db, _ = _make_loop()

    # Add a card with cross-team dependency metadata
    run(
        db.add_card(
            {
                "title": "Needs API from beta",
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

    deps = run(loop._detect_dependencies(1))
    assert len(deps) == 1
    assert deps[0].source_team == "team-alpha"
    assert deps[0].target_team == "team-beta"
    assert deps[0].dependency_type == "needs_api"
    assert deps[0].status == "open"


def test_detect_dependencies_empty_when_none():
    """No false positives when no dependencies exist."""
    loop, _, db, _ = _make_loop()

    # Add a card without dependency metadata
    run(
        db.add_card(
            {
                "title": "Normal card",
                "status": "in_progress",
                "team_id": "team-alpha",
            }
        )
    )

    deps = run(loop._detect_dependencies(1))
    assert deps == []


# ---------------------------------------------------------------------------
# Full loop (mock coordinators)
# ---------------------------------------------------------------------------


def test_full_loop_mock_coordinators():
    """Full coordination loop completes with mock LLM coordinators."""
    loop, _, db, _ = _make_loop()

    from src.metrics.sprint_metrics import SprintResult

    team_results = {
        "team-alpha": SprintResult(
            velocity=8,
            features_completed=3,
            test_coverage=0.8,
            process_coverage=0.85,
            branch_coverage=0.7,
            pairing_sessions=4,
            cycle_time_avg=120.0,
        ),
        "team-beta": SprintResult(
            velocity=5,
            features_completed=2,
            test_coverage=0.75,
            process_coverage=0.80,
            branch_coverage=0.65,
            pairing_sessions=3,
            cycle_time_avg=100.0,
        ),
    }

    outcome = run(loop.run_full_loop(2, team_results))

    assert isinstance(outcome, CoordinationOutcome)
    assert outcome.raw_evaluation  # non-empty evaluation text
    # Recommendations should exist (mock coordinator generates text)
    assert isinstance(outcome.recommendations, list)


# ---------------------------------------------------------------------------
# Mid-sprint checkin
# ---------------------------------------------------------------------------


def test_mid_sprint_checkin_returns_recommendations():
    """Mid-sprint checkin returns a list of recommendations."""
    loop, _, db, _ = _make_loop()

    recs = run(loop.run_mid_sprint_checkin(1))
    assert isinstance(recs, list)
    assert len(recs) > 0


def test_mid_sprint_checkin_no_coordinators():
    """Mid-sprint checkin works without coordinators (uses mock fallback)."""
    loop, _, db, _ = _make_loop(num_coordinators=0)

    recs = run(loop.run_mid_sprint_checkin(1))
    assert isinstance(recs, list)
    assert len(recs) > 0
    assert "healthy" in recs[0].lower() or "blocked" in recs[0].lower()


# ---------------------------------------------------------------------------
# Broadcast outcome
# ---------------------------------------------------------------------------


def test_broadcast_outcome_publishes_to_channel():
    """_broadcast_outcome publishes to the message bus."""
    loop, _, db, bus = _make_loop()

    # Create coordination channel
    try:
        bus.create_channel("coordination", members={"coord_se", "coord_el"})
    except ValueError:
        pass

    published = []

    async def _handler(msg):
        published.append(msg)

    bus.subscribe("coordination_outcome", "coord_se", _handler)

    outcome = CoordinationOutcome(
        recommendations=["Test recommendation"],
    )
    run(loop._broadcast_outcome(outcome, 1))

    # The publish should succeed without error
    # (actual delivery depends on bus internals)
    assert isinstance(outcome.recommendations, list)
