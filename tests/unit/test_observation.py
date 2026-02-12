"""Unit tests for ObservationExtractor (F-08)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator.observation import (
    AgentObservation,
    Observation,
    ObservationExtractor,
)


def _make_mock_sm(
    num_agents: int = 2,
    with_tracer: bool = False,
    with_onboarding: bool = False,
):
    """Create a mock SprintManager for observation extraction."""
    sm = MagicMock()
    sm.config = MagicMock()
    sm.config.team_config_dir = "/nonexistent"  # avoid touching filesystem

    agents = []
    for i in range(num_agents):
        agent = MagicMock()
        agent.agent_id = f"dev_{i}"
        agent.config = MagicMock()
        agent.config.role_id = f"dev_{i}"
        agent.config.seniority = "mid" if i % 2 == 0 else "senior"
        agent.config.specializations = ["backend"] if i == 0 else ["frontend"]
        agent.config.role_archetype = "developer"
        agent.is_swapped = False
        agent.conversation_history = [{"role": "user", "content": "hi"}] * (i + 1)

        if with_tracer:
            tracer = MagicMock()
            decision = MagicMock()
            decision.decision_id = f"dev_{i}-s01-planning-001"
            decision.phase = "planning"
            decision.action_type = "generate"
            decision.timestamp = "2026-01-01T00:00:00Z"
            tracer.decisions = [decision]
            agent._tracer = tracer
        else:
            agent._tracer = None

        agents.append(agent)

    sm.agents = agents

    # Mock kanban
    sm.kanban = MagicMock()
    sm.kanban.get_snapshot = AsyncMock(
        return_value={
            "ready": [{"id": "c-1"}],
            "in_progress": [],
            "review": [],
            "done": [{"id": "c-2"}],
        }
    )

    sm._sprint_results = []
    sm.disturbance_engine = None

    # Mock onboarding manager
    onboarding_mgr = MagicMock()
    if with_onboarding:
        onboarding_mgr.is_onboarding = MagicMock(side_effect=lambda aid: aid == "dev_0")
    else:
        onboarding_mgr.is_onboarding = MagicMock(return_value=False)
    sm._onboarding_manager = onboarding_mgr

    return sm


class TestObservation:
    def test_dataclass_defaults(self):
        obs = Observation(sprint_num=1, phase="planning")
        assert obs.sprint_num == 1
        assert obs.phase == "planning"
        assert obs.agents == []
        assert obs.kanban == {}
        assert obs.sprint_metrics is None


class TestAgentObservation:
    def test_dataclass_fields(self):
        ao = AgentObservation(
            agent_id="dev_0",
            role_id="dev_0",
            seniority="mid",
            specializations=["backend"],
            is_swapped=False,
            is_onboarding=True,
        )
        assert ao.agent_id == "dev_0"
        assert ao.is_onboarding is True
        assert ao.conversation_length == 0


class TestObservationExtractor:
    @pytest.mark.asyncio
    async def test_extract_basic(self):
        sm = _make_mock_sm(num_agents=2)
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1, phase="development")

        assert obs.sprint_num == 1
        assert obs.phase == "development"
        assert len(obs.agents) == 2
        assert obs.agents[0].agent_id == "dev_0"
        assert obs.agents[1].agent_id == "dev_1"

    @pytest.mark.asyncio
    async def test_kanban_populated(self):
        sm = _make_mock_sm()
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        assert "ready" in obs.kanban
        assert len(obs.kanban["done"]) == 1

    @pytest.mark.asyncio
    async def test_agent_fields(self):
        sm = _make_mock_sm()
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        a0 = obs.agents[0]
        assert a0.seniority == "mid"
        assert a0.specializations == ["backend"]
        assert a0.is_swapped is False
        assert a0.conversation_length == 1

    @pytest.mark.asyncio
    async def test_to_dict_json_safe(self):
        sm = _make_mock_sm()
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)
        d = extractor.to_dict(obs)

        # Should be JSON-serializable
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        assert d["sprint_num"] == 1

    @pytest.mark.asyncio
    async def test_empty_state(self):
        sm = _make_mock_sm(num_agents=0)
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        assert len(obs.agents) == 0
        assert obs.team_composition == {}

    @pytest.mark.asyncio
    async def test_onboarding_reflected(self):
        sm = _make_mock_sm(with_onboarding=True)
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        assert obs.agents[0].is_onboarding is True
        assert obs.agents[1].is_onboarding is False

    @pytest.mark.asyncio
    async def test_swap_status_reflected(self):
        sm = _make_mock_sm()
        sm.agents[0].is_swapped = True
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        assert obs.agents[0].is_swapped is True
        assert obs.agents[1].is_swapped is False

    @pytest.mark.asyncio
    async def test_team_composition(self):
        sm = _make_mock_sm(num_agents=3)
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        # 2 mid + 1 senior
        assert obs.team_composition["mid"] == 2
        assert obs.team_composition["senior"] == 1
        assert obs.team_composition["role_developer"] == 3

    @pytest.mark.asyncio
    async def test_tracer_decisions_included(self):
        sm = _make_mock_sm(with_tracer=True)
        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1)

        assert len(obs.agents[0].recent_decisions) == 1
        assert obs.agents[0].recent_decisions[0]["action_type"] == "generate"
