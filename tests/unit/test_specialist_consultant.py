"""Unit tests for specialist consultant system."""

import pytest
from pathlib import Path
from src.orchestrator.specialist_consultant import (
    SpecialistConsultantSystem,
    SpecialistRequest,
)
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.fixture
def temp_team_config(tmp_path):
    """Create temporary team_config directory."""
    config_dir = tmp_path / "team_config"
    specialists_dir = config_dir / "07_specialists"
    specialists_dir.mkdir(parents=True)

    # Create a test specialist profile
    ml_profile = specialists_dir / "ml_specialist.md"
    ml_profile.write_text("# ML Specialist\n\nExpert in machine learning.")

    return str(config_dir)


@pytest.fixture
def specialist_system(temp_team_config):
    """Create specialist consultant system."""
    return SpecialistConsultantSystem(
        team_config_dir=temp_team_config,
        max_per_sprint=3,
        velocity_penalty_per_consultation=2.0,
    )


@pytest.fixture
def mock_team():
    """Create mock team members."""
    junior = BaseAgent(
        AgentConfig(
            role_id="dev_junior",
            name="Junior Dev",
            role_archetype="developer",
            seniority="junior",
            model="mock",
            temperature=0.7,
            max_tokens=1000,
        ),
        vllm_endpoint="mock://",
    )

    senior = BaseAgent(
        AgentConfig(
            role_id="dev_senior",
            name="Senior Dev",
            role_archetype="developer",
            seniority="senior",
            model="mock",
            temperature=0.7,
            max_tokens=1000,
        ),
        vllm_endpoint="mock://",
    )

    return [junior, senior]


def test_can_request_specialist(specialist_system):
    """Test consultation availability checking."""
    # Sprint 1 has no consultations yet
    assert specialist_system.can_request_specialist(sprint_num=1)
    assert specialist_system.get_remaining_consultations(sprint_num=1) == 3

    # Simulate 3 consultations
    specialist_system.consultations_used[1] = 3
    assert not specialist_system.can_request_specialist(sprint_num=1)
    assert specialist_system.get_remaining_consultations(sprint_num=1) == 0


def test_should_request_specialist(specialist_system):
    """Test automatic detection of expertise gaps."""
    # Team without ML expertise
    team_skills = ["backend", "frontend"]

    # ML blocker should trigger ML specialist
    blocker = "We need to implement a neural network for prediction"
    domain = specialist_system.should_request_specialist(blocker, team_skills)
    assert domain == "ml"

    # Security blocker should trigger security specialist
    blocker = "How do we implement OAuth authentication?"
    domain = specialist_system.should_request_specialist(blocker, team_skills)
    assert domain == "security"

    # Performance blocker should trigger performance specialist
    blocker = "The API is too slow, need performance optimization"
    domain = specialist_system.should_request_specialist(blocker, team_skills)
    assert domain == "performance"

    # Team already has ML expertise - no specialist needed
    team_skills = ["backend", "ml"]
    blocker = "We need to implement a neural network"
    domain = specialist_system.should_request_specialist(blocker, team_skills)
    assert domain is None


@pytest.mark.asyncio
async def test_request_specialist(specialist_system, mock_team):
    """Test requesting specialist consultation."""
    request = SpecialistRequest(
        reason="Team stuck on ML model training",
        domain="ml",
        requesting_agent_id="dev_senior",
        sprint_num=1,
        day_num=3,
    )

    outcome = await specialist_system.request_specialist(request, mock_team)

    # Should succeed on first request
    assert outcome is not None
    assert outcome.specialist_domain == "ml"
    assert outcome.trainee_id == "dev_junior"  # Prefers junior for learning
    assert outcome.velocity_penalty == 2.0
    assert outcome.issue_resolved is True

    # Should track usage
    assert specialist_system.consultations_used[1] == 1
    assert len(specialist_system.consultation_history) == 1


@pytest.mark.asyncio
async def test_max_consultations_enforced(specialist_system, mock_team):
    """Test max 3 consultations per sprint limit."""
    # Request 3 consultations
    for i in range(3):
        request = SpecialistRequest(
            reason=f"Blocker {i+1}",
            domain="ml",
            requesting_agent_id="dev_senior",
            sprint_num=1,
            day_num=i+1,
        )
        outcome = await specialist_system.request_specialist(request, mock_team)
        assert outcome is not None

    # 4th request should fail
    request = SpecialistRequest(
        reason="Blocker 4",
        domain="security",
        requesting_agent_id="dev_senior",
        sprint_num=1,
        day_num=4,
    )
    outcome = await specialist_system.request_specialist(request, mock_team)
    assert outcome is None  # Limit reached


def test_sprint_summary(specialist_system):
    """Test sprint summary generation."""
    # Simulate 2 consultations
    specialist_system.consultations_used[1] = 2

    summary = specialist_system.get_sprint_summary(sprint_num=1)

    assert summary["consultations_used"] == 2
    assert summary["consultations_remaining"] == 1
    assert summary["total_velocity_penalty"] == 0  # No outcomes recorded


def test_specialist_domains(specialist_system):
    """Test available specialist domains."""
    assert "ml" in specialist_system.specialist_domains
    assert "security" in specialist_system.specialist_domains
    assert "performance" in specialist_system.specialist_domains
    assert "cloud" in specialist_system.specialist_domains
    assert "architecture" in specialist_system.specialist_domains
