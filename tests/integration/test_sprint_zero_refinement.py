"""Integration tests for Sprint 0 PO domain refinement and half-duration."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from src.agents.base_agent import BaseAgent, AgentConfig
from src.orchestrator.backlog import Backlog
from src.orchestrator.config import ExperimentConfig
from src.orchestrator.sprint_manager import SprintManager
from src.tools.shared_context import SharedContextDB


def _make_agent(role_id: str, role_archetype: str = "developer", **kwargs) -> BaseAgent:
    """Helper to create a mock agent."""
    config = AgentConfig(
        role_id=role_id,
        name=role_id,
        role_archetype=role_archetype,
        model="mock-model",
        temperature=0.7,
        max_tokens=1000,
        **kwargs,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def _make_backlog(tmp_path: Path, include_context: bool = True) -> Backlog:
    """Helper to create a backlog with or without stakeholder context."""
    product = {
        "name": "TestApp",
        "description": "A test application",
        "languages": ["python"],
        "tech_stack": ["pytest"],
        "repository": {"type": "greenfield", "url": ""},
    }
    if include_context:
        product.update(
            {
                "mission": "Make testing easy for everyone",
                "vision": "The go-to test framework for small teams",
                "goals": ["Ship MVP in 3 months", "100 users by month 6"],
                "target_audience": "Small dev teams",
                "success_metrics": ["Weekly active users", "Test pass rate"],
            }
        )

    stories = [
        {
            "id": "US-001",
            "title": "User registration",
            "description": "As a user I can register",
            "acceptance_criteria": ["Email validated"],
            "story_points": 3,
            "priority": 1,
        }
    ]

    path = tmp_path / "backlog.yaml"
    path.write_text(yaml.dump({"product": product, "stories": stories}))
    return Backlog(str(path))


def _make_config(workspace: str, duration: int = 60) -> ExperimentConfig:
    """Helper to create a minimal experiment config."""
    return ExperimentConfig(
        name="test-experiment",
        sprint_duration_minutes=duration,
        database_url="mock://",
        team_config_dir="team_config",
        vllm_endpoint="mock://",
        tools_workspace_root=workspace,
        sprint_zero_enabled=True,
    )


def _make_team():
    """Helper to create a minimal team of agents."""
    return [
        _make_agent("po", role_archetype="leader"),
        _make_agent("dev_lead", role_archetype="leader", seniority="senior"),
        _make_agent("qa_lead", role_archetype="leader", seniority="senior"),
        _make_agent("dev_0", role_archetype="developer", seniority="mid"),
        _make_agent("dev_1", role_archetype="developer", seniority="mid"),
    ]


# ---------------------------------------------------------------------------
# PO Domain Refinement Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_po_domain_refinement_stores_brief_in_history():
    """Test that PO domain refinement produces a business brief in conversation history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=True)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=backlog,
        )

        await manager._run_po_domain_refinement()

        po = next(a for a in agents if a.config.role_id == "po")
        # PO should have a domain_refinement entry in conversation history
        refinement_entries = [
            h for h in po.conversation_history if h.get("type") == "domain_refinement"
        ]
        assert len(refinement_entries) == 1
        assert refinement_entries[0]["metadata"]["phase"] == "sprint_zero"
        assert len(refinement_entries[0]["content"]) > 0


@pytest.mark.asyncio
async def test_po_domain_refinement_skips_without_context():
    """Test that PO domain refinement is skipped when no stakeholder context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=False)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=backlog,
        )

        await manager._run_po_domain_refinement()

        po = next(a for a in agents if a.config.role_id == "po")
        refinement_entries = [
            h for h in po.conversation_history if h.get("type") == "domain_refinement"
        ]
        assert len(refinement_entries) == 0


@pytest.mark.asyncio
async def test_po_domain_refinement_skips_without_backlog():
    """Test that PO domain refinement is skipped when no backlog is loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=None,
        )

        await manager._run_po_domain_refinement()

        po = next(a for a in agents if a.config.role_id == "po")
        refinement_entries = [
            h for h in po.conversation_history if h.get("type") == "domain_refinement"
        ]
        assert len(refinement_entries) == 0


@pytest.mark.asyncio
async def test_po_domain_refinement_skips_without_po_agent():
    """Test graceful handling when no PO agent in the team."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=True)
        # Team without PO
        agents = [
            _make_agent("dev_lead", role_archetype="leader", seniority="senior"),
            _make_agent("dev_0", role_archetype="developer"),
        ]
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=backlog,
        )

        # Should not raise
        await manager._run_po_domain_refinement()


# ---------------------------------------------------------------------------
# Sprint 0 Half-Duration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sprint_zero_uses_half_duration():
    """Test that Sprint 0 passes half the regular duration to run_development."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=True)
        agents = _make_team()
        full_duration = 60
        config = _make_config(str(tmp_path / "workspace"), duration=full_duration)
        db = SharedContextDB("mock://")
        await db.initialize()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=output_dir,
            backlog=backlog,
        )

        # Patch run_development to capture the duration_override argument
        captured_args = {}
        original_run_dev = manager.run_development

        async def mock_run_dev(sprint_num, duration_override=None):
            captured_args["sprint_num"] = sprint_num
            captured_args["duration_override"] = duration_override
            # Don't actually run development (would timeout in tests)

        manager.run_development = mock_run_dev
        # Also patch other phases to no-op for speed
        manager.run_qa_review = AsyncMock()
        manager._validate_ci_pipeline = AsyncMock(return_value=True)
        manager.run_retrospective = AsyncMock(return_value={"keep": [], "drop": [], "puzzle": []})
        manager.apply_meta_learning = AsyncMock()
        manager.generate_sprint_artifacts = AsyncMock()
        manager.metrics.calculate_sprint_results = AsyncMock(
            return_value=type("R", (), {
                "velocity": 0,
                "features_completed": 0,
                "test_coverage": 0,
                "pairing_sessions": 0,
                "cycle_time_avg": 0,
                "ci_validated": True,
            })()
        )

        await manager._run_sprint_zero()

        assert captured_args["sprint_num"] == 0
        assert captured_args["duration_override"] == full_duration // 2


@pytest.mark.asyncio
async def test_regular_sprint_uses_full_duration():
    """Test that regular sprints don't use duration_override."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=True)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"), duration=60)
        db = SharedContextDB("mock://")
        await db.initialize()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=output_dir,
            backlog=backlog,
        )

        # Patch run_development to capture the duration_override
        captured_args = {}

        async def mock_run_dev(sprint_num, duration_override=None):
            captured_args["sprint_num"] = sprint_num
            captured_args["duration_override"] = duration_override

        manager.run_development = mock_run_dev
        manager.run_planning = AsyncMock()
        manager.run_qa_review = AsyncMock()
        manager.sprint_review.run_review = AsyncMock(return_value={})
        manager.kanban.get_cards_by_status = AsyncMock(return_value=[])
        manager.run_retrospective = AsyncMock(return_value={"keep": [], "drop": [], "puzzle": []})
        manager.apply_meta_learning = AsyncMock()
        manager.generate_sprint_artifacts = AsyncMock()
        manager.metrics.calculate_sprint_results = AsyncMock(
            return_value=type("R", (), {
                "velocity": 0,
                "features_completed": 0,
                "test_coverage": 0,
                "pairing_sessions": 0,
                "cycle_time_avg": 0,
            })()
        )

        await manager.run_sprint(1)

        assert captured_args["sprint_num"] == 1
        assert captured_args["duration_override"] is None


# ---------------------------------------------------------------------------
# Project Context Wiring Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sprint_manager_passes_project_context_to_refinement():
    """Test that SprintManager wires project context into StoryRefinementSession."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        backlog = _make_backlog(tmp_path, include_context=True)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=backlog,
        )

        # The story refinement session should have the project context
        assert manager.story_refinement.project_context != ""
        assert "## Mission" in manager.story_refinement.project_context
        assert "Make testing easy" in manager.story_refinement.project_context


@pytest.mark.asyncio
async def test_sprint_manager_empty_context_without_backlog():
    """Test that SprintManager has empty context when no backlog is loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agents = _make_team()
        config = _make_config(str(tmp_path / "workspace"))
        db = SharedContextDB("mock://")
        await db.initialize()

        manager = SprintManager(
            agents=agents,
            shared_db=db,
            config=config,
            output_dir=tmp_path / "output",
            backlog=None,
        )

        assert manager.story_refinement.project_context == ""
