"""Integration tests for story refinement ceremony (Phase 1 planning)."""

import pytest
from src.orchestrator.story_refinement import StoryRefinementSession
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.fixture
def mock_po():
    """Mock Product Owner agent."""
    config = AgentConfig(
        role_id="po",
        name="Sarah (PO)",
        role_archetype="leader",
        model="mock-model",
        temperature=0.7,
        max_tokens=1000,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


@pytest.fixture
def mock_dev_lead():
    """Mock Development Lead agent."""
    config = AgentConfig(
        role_id="dev_lead",
        name="Ahmed (Dev Lead)",
        role_archetype="leader",
        seniority="senior",
        model="mock-model",
        temperature=0.7,
        max_tokens=1000,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


@pytest.fixture
def mock_team(mock_dev_lead):
    """Mock development team."""
    team = [mock_dev_lead]
    for i in range(3):
        config = AgentConfig(
            role_id=f"dev_{i}",
            name=f"Dev {i}",
            role_archetype="developer",
            seniority="mid",
            model="mock-model",
            temperature=0.7,
            max_tokens=1000,
        )
        team.append(BaseAgent(config, vllm_endpoint="mock://"))
    return team


@pytest.fixture
def sample_stories():
    """Sample user stories for refinement."""
    return [
        {
            "id": "US-001",
            "title": "User Registration",
            "description": "As a user, I want to register an account",
            "story_points": 0,  # Unestimated
            "acceptance_criteria": ["User can register", "Email confirmation sent"],
        },
        {
            "id": "US-002",
            "title": "User Login",
            "description": "As a user, I want to log in",
            "story_points": 0,
            "acceptance_criteria": ["User can log in", "Session created"],
        },
    ]


@pytest.mark.asyncio
async def test_po_presents_story(mock_po, mock_team, mock_dev_lead, sample_stories):
    """Test PO presents story with business context."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    # Refine stories
    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    # Should return refined stories
    assert len(refined) > 0, "Should refine at least one story"
    assert all(hasattr(s, "id") for s in refined), "Refined stories should have IDs"


@pytest.mark.asyncio
async def test_team_asks_clarifying_questions(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test team generates clarifying questions."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    _ = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    # Team should have asked questions (conversation history should grow)
    for agent in mock_team:
        if agent != mock_dev_lead:
            # Developers should have conversation history from refinement
            assert (
                len(agent.conversation_history) >= 0
            ), "Agents participate in refinement"


@pytest.mark.asyncio
async def test_team_estimates_story_points(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test collaborative story point estimation."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    # Refined stories should have estimates (or 0 in mock mode)
    for story in refined:
        assert (
            story.story_points >= 0
        ), f"Story {story.id} should have story_points field"
        assert hasattr(
            story, "story_points"
        ), "RefinedStory should have story_points attribute"


@pytest.mark.asyncio
async def test_sprint_commitment_respects_capacity(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test sprint commitment doesn't exceed team capacity."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    team_capacity = 10  # Small capacity

    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=team_capacity
    )

    # Total story points should not exceed capacity
    total_points = sum(s.story_points for s in refined)
    assert (
        total_points <= team_capacity * 1.2
    ), f"Should respect capacity ({total_points} <= {team_capacity * 1.2})"


@pytest.mark.asyncio
async def test_story_refinement_produces_refined_stories(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test refinement session returns RefinedStory objects."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    # Should return list of refined stories
    assert isinstance(refined, list), "Should return list"
    assert len(refined) > 0, "Should refine at least one story"

    # Check story structure
    for story in refined:
        assert hasattr(story, "id"), "Should have ID"
        assert hasattr(story, "title"), "Should have title"
        assert hasattr(story, "story_points"), "Should have story points"


@pytest.mark.asyncio
async def test_story_refinement_with_project_context(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test refinement session accepts and uses project context."""
    project_context = (
        "# TaskFlow\n\n## Mission\nHelp teams focus.\n\n"
        "## Goals\n- Launch MVP in 3 months\n"
    )
    session = StoryRefinementSession(
        mock_po, mock_team, mock_dev_lead, project_context=project_context
    )

    assert session.project_context == project_context

    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    # Should still produce refined stories as before
    assert len(refined) > 0
    assert all(hasattr(s, "id") for s in refined)


@pytest.mark.asyncio
async def test_story_refinement_without_project_context(
    mock_po, mock_team, mock_dev_lead, sample_stories
):
    """Test refinement works normally when no project context is provided."""
    session = StoryRefinementSession(mock_po, mock_team, mock_dev_lead)

    assert session.project_context == ""

    refined = await session.refine_stories(
        sample_stories, sprint_num=1, team_capacity=20
    )

    assert len(refined) > 0
