"""Integration test for Sprint 0 infrastructure setup."""

import asyncio
import tempfile
from pathlib import Path
import yaml
import pytest

from src.orchestrator.backlog import Backlog
from src.orchestrator.sprint_manager import SprintManager
from src.orchestrator.config import ExperimentConfig
from src.tools.shared_context import SharedContextDB
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.mark.asyncio
async def test_sprint_zero_greenfield():
    """Test Sprint 0 with a greenfield project."""

    # Create temporary backlog with Sprint 0 metadata
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create backlog with product metadata
        backlog_path = tmpdir_path / "backlog.yaml"
        backlog_data = {
            "product": {
                "name": "Test Project",
                "description": "Integration test project",
                "languages": ["python"],
                "tech_stack": ["github-actions", "docker"],
                "repository": {
                    "type": "greenfield",
                    "url": ""
                }
            },
            "stories": []
        }
        backlog_path.write_text(yaml.dump(backlog_data))

        # Load backlog
        backlog = Backlog(str(backlog_path))
        metadata = backlog.get_product_metadata()

        # Verify metadata loaded correctly
        assert metadata.name == "Test Project"
        assert "python" in metadata.languages
        assert "docker" in metadata.tech_stack
        assert metadata.repository_type == "greenfield"


@pytest.mark.asyncio
async def test_sprint_zero_planning():
    """Test Sprint 0 planning phase generates infrastructure stories."""

    # Create minimal config
    config = ExperimentConfig(
        name="test-sprint-zero",
        sprint_duration_minutes=20,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="http://localhost:8000",
        sprint_zero_enabled=True,
        tools_workspace_root="/tmp/test-workspace"
    )

    # Create mock database
    db = SharedContextDB("mock://")
    await db.initialize()

    # Create minimal agent list (empty is fine for this test)
    agents = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create backlog
        backlog_path = tmpdir_path / "backlog.yaml"
        backlog_data = {
            "product": {
                "name": "Test Project",
                "description": "Test",
                "languages": ["python", "go"],
                "tech_stack": ["github-actions"],
                "repository": {"type": "greenfield", "url": ""}
            },
            "stories": []
        }
        backlog_path.write_text(yaml.dump(backlog_data))
        backlog = Backlog(str(backlog_path))

        # Create sprint manager
        output_dir = tmpdir_path / "output"
        sprint_mgr = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=output_dir,
            backlog=backlog
        )

        # Run Sprint 0 planning
        await sprint_mgr._run_planning_sprint_zero()

        # Verify infrastructure stories were added to kanban
        ready_cards = await db.get_cards_by_status("ready")

        # Should have generated stories for Python, Go, and CI
        assert len(ready_cards) > 0

        # Check that stories are Sprint 0
        for card in ready_cards:
            assert card["sprint"] == 0

        # Verify story types
        story_titles = [card["title"].lower() for card in ready_cards]
        assert any("python" in title and "lint" in title for title in story_titles)
        assert any("go" in title for title in story_titles)
        assert any("ci" in title or "github" in title for title in story_titles)


@pytest.mark.asyncio
async def test_sprint_zero_explicit_stories():
    """Test Sprint 0 with explicitly provided infrastructure stories in backlog."""

    config = ExperimentConfig(
        name="test-explicit",
        sprint_duration_minutes=20,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="http://localhost:8000",
        sprint_zero_enabled=True,
        tools_workspace_root="/tmp/test-workspace"
    )

    db = SharedContextDB("mock://")
    await db.initialize()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create backlog with explicit Sprint 0 stories
        backlog_path = tmpdir_path / "backlog.yaml"
        backlog_data = {
            "product": {
                "name": "Test Project",
                "description": "Test",
                "languages": ["python"],
                "tech_stack": ["github-actions"],
                "repository": {"type": "greenfield", "url": ""}
            },
            "stories": [
                {
                    "id": "INFRA-CUSTOM-001",
                    "title": "Custom Infrastructure Story",
                    "description": "Custom story provided by stakeholder",
                    "acceptance_criteria": ["Criteria 1"],
                    "story_points": 5,
                    "priority": 1,
                    "sprint": 0  # Explicitly Sprint 0
                }
            ]
        }
        backlog_path.write_text(yaml.dump(backlog_data))
        backlog = Backlog(str(backlog_path))

        output_dir = tmpdir_path / "output"
        sprint_mgr = SprintManager(
            agents=[],
            shared_db=db,
            config=config,
            output_dir=output_dir,
            backlog=backlog
        )

        # Run Sprint 0 planning
        await sprint_mgr._run_planning_sprint_zero()

        # Verify custom story was used
        ready_cards = await db.get_cards_by_status("ready")
        assert len(ready_cards) == 1
        assert ready_cards[0]["title"] == "Custom Infrastructure Story"


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_sprint_zero_greenfield())
    print("✓ test_sprint_zero_greenfield")

    asyncio.run(test_sprint_zero_planning())
    print("✓ test_sprint_zero_planning")

    asyncio.run(test_sprint_zero_explicit_stories())
    print("✓ test_sprint_zero_explicit_stories")

    print("\nAll Sprint 0 integration tests passed!")
