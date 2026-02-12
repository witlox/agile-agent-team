"""Unit tests for PhaseRunner (F-07)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator.phase_runner import PhaseResult, PhaseRunner


def _make_mock_sprint_manager(tracing: bool = False):
    """Create a mock SprintManager with stubbed phase methods."""
    sm = MagicMock()
    sm.config = MagicMock()
    sm.config.tracing_enabled = tracing

    # Mock agents list
    agent = MagicMock()
    agent.agent_id = "dev_a"
    agent._tracer = None
    sm.agents = [agent]

    # Mock kanban
    sm.kanban = MagicMock()
    sm.kanban.get_snapshot = AsyncMock(
        return_value={
            "ready": [],
            "in_progress": [],
            "review": [],
            "done": [{"id": "card-1", "title": "Test"}],
        }
    )

    # Mock phase methods
    sm.run_planning = AsyncMock(
        return_value={"stories_selected": [{"id": "US-01"}], "capacity": 9}
    )
    sm.run_development = AsyncMock(
        return_value={"pairing_sessions": 2, "days_completed": 3}
    )
    sm.run_qa_review = AsyncMock(
        return_value={"cards_reviewed": 2, "cards_approved": 1, "cards_rejected": 1}
    )
    sm.run_retrospective = AsyncMock(
        return_value={
            "sprint": 1,
            "keep": [{"agent": "dev_a", "text": "Good pairing"}],
            "drop": [],
            "puzzle": [],
        }
    )
    sm.apply_meta_learning = AsyncMock()
    sm._sprint_results = []

    # Mock tracer lifecycle methods
    sm._attach_tracers = MagicMock()
    sm._set_agent_phase = MagicMock()

    return sm


class TestPhaseResult:
    def test_defaults(self):
        result = PhaseResult(phase="planning", sprint_num=1, duration_seconds=1.5)
        assert result.phase == "planning"
        assert result.sprint_num == 1
        assert result.decisions == []
        assert result.artifacts == {}
        assert result.error is None


class TestPhaseRunner:
    @pytest.mark.asyncio
    async def test_run_planning(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        result = await runner.run_phase("planning", sprint_num=1)

        assert result.phase == "planning"
        assert result.sprint_num == 1
        assert result.duration_seconds > 0
        assert result.error is None
        assert result.artifacts["stories_selected"] == [{"id": "US-01"}]
        sm.run_planning.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_run_development_with_duration(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        result = await runner.run_phase("development", sprint_num=2, duration_minutes=5)

        assert result.phase == "development"
        assert result.error is None
        sm.run_development.assert_awaited_once_with(2, duration_override=5)

    @pytest.mark.asyncio
    async def test_run_qa_review(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        result = await runner.run_phase("qa_review", sprint_num=1)

        assert result.artifacts["cards_approved"] == 1
        assert result.artifacts["cards_rejected"] == 1

    @pytest.mark.asyncio
    async def test_invalid_phase_raises(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        with pytest.raises(ValueError, match="Unknown phase"):
            await runner.run_phase("invalid_phase", sprint_num=1)

    @pytest.mark.asyncio
    async def test_kanban_snapshot_captured(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        result = await runner.run_phase("planning", sprint_num=1)

        assert "done" in result.kanban_snapshot
        assert len(result.kanban_snapshot["done"]) == 1

    @pytest.mark.asyncio
    async def test_run_sequence(self):
        sm = _make_mock_sprint_manager()
        runner = PhaseRunner(sm)
        results = await runner.run_sequence(
            ["planning", "development", "qa_review"], sprint_num=1
        )

        assert len(results) == 3
        assert results[0].phase == "planning"
        assert results[1].phase == "development"
        assert results[2].phase == "qa_review"
        assert all(r.error is None for r in results)

    @pytest.mark.asyncio
    async def test_run_sequence_stops_on_error(self):
        sm = _make_mock_sprint_manager()
        sm.run_development = AsyncMock(side_effect=RuntimeError("boom"))
        runner = PhaseRunner(sm)
        results = await runner.run_sequence(
            ["planning", "development", "qa_review"], sprint_num=1
        )

        assert len(results) == 2
        assert results[0].error is None
        assert results[1].error == "boom"

    @pytest.mark.asyncio
    async def test_phase_with_tracing(self):
        sm = _make_mock_sprint_manager(tracing=True)

        # Set up a mock tracer on the agent
        tracer = MagicMock()
        decision = MagicMock()
        decision.decision_id = "dev_a-s01-planning-001"
        decision.phase = "planning"
        decision.action_type = "generate"
        decision.timestamp = "2026-01-01T00:00:00Z"
        tracer.decisions = [decision]
        sm.agents[0]._tracer = tracer

        runner = PhaseRunner(sm)
        result = await runner.run_phase("planning", sprint_num=1)

        assert len(result.decisions) == 1
        assert result.decisions[0]["decision_id"] == "dev_a-s01-planning-001"
        sm._attach_tracers.assert_called_once_with(1)
