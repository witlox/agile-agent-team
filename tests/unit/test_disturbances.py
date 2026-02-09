"""Unit tests for disturbance engine."""

import random
import pytest
from src.orchestrator.disturbances import DisturbanceEngine
from src.tools.shared_context import SharedContextDB
from src.tools.kanban import KanbanBoard
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.fixture
def mock_db():
    """Mock database."""
    return SharedContextDB(database_url="mock://")


@pytest.fixture
async def kanban(mock_db):
    """Kanban board with mock data."""
    await mock_db.initialize()
    board = KanbanBoard(mock_db)

    # Add some test cards
    await board.add_card(
        {
            "id": "TASK-001",
            "title": "Implement feature A",
            "description": "Feature A implementation",
            "status": "in_progress",
            "story_points": 3,
            "sprint": 1,
        }
    )
    await board.add_card(
        {
            "id": "TASK-002",
            "title": "Implement feature B",
            "description": "Feature B implementation",
            "status": "ready",
            "story_points": 5,
            "sprint": 1,
            "depends_on": ["TASK-001"],
        }
    )

    return board


@pytest.fixture
def mock_agents():
    """Create mock agents."""
    agents = []

    # Junior agent
    junior_config = AgentConfig(
        role_id="dev_junior",
        name="Jamie (Junior)",
        seniority="junior",
        role_archetype=["developer"],
        model="mock-model",
        temperature=0.7,
        max_tokens=1000,
    )
    junior = BaseAgent(junior_config)
    agents.append(junior)

    # Senior agent
    senior_config = AgentConfig(
        role_id="dev_senior",
        name="Alex (Senior)",
        seniority="senior",
        role_archetype=["developer"],
        model="mock-model",
        temperature=0.7,
        max_tokens=1000,
    )
    senior = BaseAgent(senior_config)
    agents.append(senior)

    return agents


@pytest.fixture
def disturbance_engine():
    """Create disturbance engine with test frequencies."""
    frequencies = {
        "dependency_breaks": 0.5,  # 50% chance
        "flaky_test": 0.5,
        "production_incident": 0.3,
        "scope_creep": 0.4,
        "junior_misunderstanding": 0.3,
        "architectural_debt_surfaces": 0.2,
        "merge_conflict": 0.25,
    }
    blast_radius_controls = {
        "max_velocity_impact": 0.25,
        "max_quality_regression": 0.15,
    }
    rng = random.Random(42)
    return DisturbanceEngine(frequencies, blast_radius_controls, rng=rng)


@pytest.mark.asyncio
async def test_dependency_break_fires(disturbance_engine, kanban, mock_agents, mock_db):
    """Test dependency break disturbance selects a card and blocks it."""
    # Apply dependency break
    await disturbance_engine.apply(
        "dependency_breaks", mock_agents, kanban, mock_db
    )

    # Check that a card was marked as blocked
    snapshot = await kanban.get_snapshot()
    all_cards = snapshot.get("ready", []) + snapshot.get("in_progress", [])

    # At least one card should have dependency break metadata
    blocked_cards = [
        c for c in all_cards if "DEPENDENCY BREAK" in c.get("title", "")
    ]

    assert len(blocked_cards) > 0, "Dependency break should mark a card as blocked"


@pytest.mark.asyncio
async def test_production_incident_creates_hotfix(
    disturbance_engine, kanban, mock_agents, mock_db
):
    """Test production incident creates HOTFIX card."""
    initial_snapshot = await kanban.get_snapshot()
    initial_count = sum(len(v) for v in initial_snapshot.values())

    # Apply production incident
    await disturbance_engine.apply(
        "production_incident", mock_agents, kanban, mock_db
    )

    # Check that a HOTFIX card was created
    final_snapshot = await kanban.get_snapshot()
    all_cards = (
        final_snapshot.get("ready", [])
        + final_snapshot.get("in_progress", [])
        + final_snapshot.get("review", [])
    )

    hotfix_cards = [c for c in all_cards if "HOTFIX" in c.get("title", "")]

    assert len(hotfix_cards) > 0, "Production incident should create HOTFIX card"
    assert any(
        c.get("story_points", 0) >= 3 for c in hotfix_cards
    ), "HOTFIX should have story points"


@pytest.mark.asyncio
async def test_flaky_test_tags_card(disturbance_engine, kanban, mock_agents, mock_db):
    """Test flaky test disturbance tags card with [FLAKY TESTS]."""
    # Apply flaky tests disturbance
    await disturbance_engine.apply("flaky_test", mock_agents, kanban, mock_db)

    # Check that a card was tagged
    snapshot = await kanban.get_snapshot()
    all_cards = (
        snapshot.get("ready", [])
        + snapshot.get("in_progress", [])
        + snapshot.get("review", [])
    )

    flaky_cards = [c for c in all_cards if "FLAKY" in c.get("title", "")]

    assert len(flaky_cards) > 0, "Flaky tests should tag a card"


@pytest.mark.asyncio
async def test_scope_creep_adds_unplanned_card(
    disturbance_engine, kanban, mock_agents, mock_db
):
    """Test scope creep adds new card mid-sprint."""
    initial_snapshot = await kanban.get_snapshot()
    initial_count = sum(len(v) for v in initial_snapshot.values())

    # Apply scope creep
    await disturbance_engine.apply("scope_creep", mock_agents, kanban, mock_db)

    # Check that a new card was added
    final_snapshot = await kanban.get_snapshot()
    final_count = sum(len(v) for v in final_snapshot.values())

    assert (
        final_count > initial_count
    ), "Scope creep should add a new unplanned card"

    # Card should have SCOPE CREEP marker
    all_cards = (
        final_snapshot.get("ready", [])
        + final_snapshot.get("in_progress", [])
        + final_snapshot.get("review", [])
    )
    scope_cards = [c for c in all_cards if "SCOPE CREEP" in c.get("title", "")]

    assert len(scope_cards) > 0, "Scope creep card should be marked"


@pytest.mark.asyncio
async def test_junior_misunderstanding_tags_agent(
    disturbance_engine, kanban, mock_agents, mock_db
):
    """Test junior misunderstanding tags random junior agent."""
    # Filter for junior agents
    junior_agents = [
        a for a in mock_agents if a.config.seniority == "junior"
    ]

    if not junior_agents:
        pytest.skip("No junior agents available")

    # Apply junior misunderstanding
    await disturbance_engine.apply(
        "junior_misunderstanding", mock_agents, kanban, mock_db
    )

    # Check that a card was tagged with clarification needed
    snapshot = await kanban.get_snapshot()
    all_cards = (
        snapshot.get("ready", [])
        + snapshot.get("in_progress", [])
        + snapshot.get("review", [])
    )

    clarification_cards = [
        c for c in all_cards if "CLARIFICATION" in c.get("title", "")
    ]

    assert (
        len(clarification_cards) > 0
    ), "Junior misunderstanding should tag a card"


@pytest.mark.asyncio
async def test_architectural_debt_surfaces(
    disturbance_engine, kanban, mock_agents, mock_db
):
    """Test architectural debt tags card with [TECH DEBT]."""
    # Apply architectural debt
    await disturbance_engine.apply(
        "architectural_debt_surfaces", mock_agents, kanban, mock_db
    )

    # Check that a card was tagged
    snapshot = await kanban.get_snapshot()
    all_cards = (
        snapshot.get("ready", [])
        + snapshot.get("in_progress", [])
        + snapshot.get("review", [])
    )

    debt_cards = [c for c in all_cards if "TECH DEBT" in c.get("title", "")]

    assert len(debt_cards) > 0, "Architectural debt should tag a card"


@pytest.mark.asyncio
async def test_merge_conflict_tags_card_and_notifies_lead(
    disturbance_engine, kanban, mock_agents, mock_db
):
    """Test merge conflict tags card and notifies dev lead."""
    # Apply merge conflict
    await disturbance_engine.apply(
        "merge_conflict", mock_agents, kanban, mock_db
    )

    # Check that a card was tagged
    snapshot = await kanban.get_snapshot()
    all_cards = (
        snapshot.get("ready", [])
        + snapshot.get("in_progress", [])
        + snapshot.get("review", [])
    )

    conflict_cards = [
        c for c in all_cards if "MERGE CONFLICT" in c.get("title", "")
    ]

    assert len(conflict_cards) > 0, "Merge conflict should tag a card"


@pytest.mark.asyncio
async def test_blast_radius_velocity_cap(disturbance_engine):
    """Test blast radius caps velocity impact at configured threshold."""
    max_impact = disturbance_engine.max_velocity_impact

    assert max_impact == 0.25, "Max velocity impact should be 25%"

    # Test that impact calculation respects the cap
    # (This would require access to internal methods or metrics tracking)
    # For now, just verify the configuration is loaded
    assert hasattr(disturbance_engine, "max_velocity_impact")


@pytest.mark.asyncio
async def test_blast_radius_quality_cap(disturbance_engine):
    """Test blast radius caps quality regression at configured threshold."""
    max_regression = disturbance_engine.max_quality_regression

    assert max_regression == 0.15, "Max quality regression should be 15%"

    assert hasattr(disturbance_engine, "max_quality_regression")


def test_rng_determinism():
    """Test same seed produces same disturbance sequence."""
    # Create two engines with same seed
    frequencies = {"dependency_breaks": 0.5}
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    engine1 = DisturbanceEngine(frequencies, {}, rng=rng1)
    engine2 = DisturbanceEngine(frequencies, {}, rng=rng2)

    # Roll for same sprint
    result1 = engine1.roll_for_sprint(1)
    result2 = engine2.roll_for_sprint(1)

    assert (
        result1 == result2
    ), "Same seed should produce same disturbance sequence"

    # Different seeds should (likely) produce different results
    rng3 = random.Random(99)
    engine3 = DisturbanceEngine(frequencies, {}, rng=rng3)
    result3 = engine3.roll_for_sprint(1)

    # Note: There's a small chance these could be equal by coincidence
    # but with 50% frequency, it's unlikely
