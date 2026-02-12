"""Integration tests for RL environment API (F-05 through F-10).

These tests verify that the individual components work together:
config builder → sprint manager → phase runner → observation → reward.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator.config import ExperimentConfig
from src.orchestrator.config_builder import ExperimentConfigBuilder
from src.orchestrator.observation import ObservationExtractor
from src.orchestrator.phase_runner import PhaseRunner
from src.orchestrator.reward import RewardCalculator
from src.orchestrator.scenario_catalog import ScenarioCatalog
from src.agents.runtime.factory import (
    _RUNTIME_REGISTRY,
    register_runtime,
)
from src.agents.runtime.base import AgentRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyRuntime(AgentRuntime):
    """Minimal runtime for integration tests."""

    def __init__(self, config, tools):
        super().__init__(config, tools)

    async def execute_task(self, system_prompt, user_message, max_turns=20):
        from src.agents.runtime.base import RuntimeResult

        return RuntimeResult(content="dummy", tool_calls=[], success=True)


def _mock_sprint_manager(config):
    """Build a mock SprintManager wired to the given config."""
    sm = MagicMock()
    sm.config = config
    sm.agents = []

    agent = MagicMock()
    agent.agent_id = "dev_a"
    agent.config = MagicMock()
    agent.config.role_id = "dev_a"
    agent.config.seniority = "mid"
    agent.config.specializations = ["backend"]
    agent.config.role_archetype = "developer"
    agent.is_swapped = False
    agent.conversation_history = []
    agent._tracer = None
    sm.agents.append(agent)

    sm.kanban = MagicMock()
    sm.kanban.get_snapshot = AsyncMock(
        return_value={"ready": [], "in_progress": [], "review": [], "done": []}
    )

    sm.run_planning = AsyncMock(
        return_value={"stories_selected": [{"id": "US-01"}], "capacity": 3}
    )
    sm.run_development = AsyncMock(
        return_value={"pairing_sessions": 1, "days_completed": 2}
    )
    sm.run_qa_review = AsyncMock(
        return_value={"cards_reviewed": 1, "cards_approved": 1, "cards_rejected": 0}
    )
    sm.run_retrospective = AsyncMock(
        return_value={"sprint": 1, "keep": [], "drop": [], "puzzle": []}
    )
    sm.apply_meta_learning = AsyncMock()
    sm._sprint_results = [
        {
            "sprint": 1,
            "velocity": 8,
            "features_completed": 3,
            "test_coverage": 0.75,
            "pairing_sessions": 2,
            "departure_events": [],
            "backfill_events": [],
        }
    ]

    sm._attach_tracers = MagicMock()
    sm._set_agent_phase = MagicMock()
    sm.disturbance_engine = None

    onboarding_mgr = MagicMock()
    onboarding_mgr.is_onboarding = MagicMock(return_value=False)
    sm._onboarding_manager = onboarding_mgr

    return sm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConfigBuilderToSprintManager:
    """Build config via ConfigBuilder, create mock SM, run phase."""

    @pytest.mark.asyncio
    async def test_builder_to_phase_to_observation(self):
        config = (
            ExperimentConfigBuilder()
            .name("integration-test")
            .sprint_duration(5)
            .database_url("mock://")
            .tracing(False)
            .agents({"dev_a": {"name": "Dev A", "model": "mock", "runtime": "mock"}})
            .build()
        )
        assert isinstance(config, ExperimentConfig)
        assert config.name == "integration-test"

        sm = _mock_sprint_manager(config)
        runner = PhaseRunner(sm)
        result = await runner.run_phase("planning", sprint_num=1)
        assert result.error is None

        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1, phase="planning")
        assert obs.sprint_num == 1
        assert len(obs.agents) == 1


class TestCustomRuntimeRegistration:
    """Register custom runtime, verify it's available."""

    def test_register_and_use(self):
        register_runtime(
            "integration_test_rt",
            lambda cfg, tools: _DummyRuntime(cfg, tools),
        )
        assert "integration_test_rt" in _RUNTIME_REGISTRY
        _RUNTIME_REGISTRY.pop("integration_test_rt", None)


class TestPhaseSequencePipeline:
    """Full pipeline: planning → development → observation extraction."""

    @pytest.mark.asyncio
    async def test_sequence_with_observation(self):
        config = ExperimentConfigBuilder().database_url("mock://").build()
        sm = _mock_sprint_manager(config)

        runner = PhaseRunner(sm)
        results = await runner.run_sequence(["planning", "development"], sprint_num=1)
        assert len(results) == 2
        assert all(r.error is None for r in results)

        extractor = ObservationExtractor(sm)
        obs = await extractor.extract(sprint_num=1, phase="development")
        obs_dict = extractor.to_dict(obs)
        # Should be JSON-serializable
        assert json.dumps(obs_dict)


class TestRewardFromSprintResult:
    """Reward calculation from actual sprint result data."""

    def test_reward_from_sprint_result(self):
        calc = RewardCalculator()
        sprint_result = {
            "velocity": 8,
            "features_completed": 3,
            "features_planned": 5,
            "test_coverage": 0.75,
            "pairing_sessions": 4,
        }
        reward = calc.compute(sprint_result, expected_velocity=10)
        assert 0.0 <= reward.total <= 1.0
        assert reward.outcome > 0
        assert "velocity_ratio" in reward.components


class TestScenarioToExecution:
    """Scenario catalog → config builder → phase execution."""

    @pytest.mark.asyncio
    async def test_scenario_to_phase(self):
        catalog = ScenarioCatalog()
        scenario = catalog.generate("implementation", difficulty=0.5, seed=42)

        config = (
            ExperimentConfigBuilder()
            .name("scenario-test")
            .sprint_duration(scenario.duration_minutes)
            .database_url("mock://")
            .disturbances(**scenario.disturbance_overrides)
            .build()
        )
        assert isinstance(config, ExperimentConfig)

        sm = _mock_sprint_manager(config)
        runner = PhaseRunner(sm)

        # Run only the phases specified by the scenario
        results = await runner.run_sequence(scenario.phases, sprint_num=1)
        assert len(results) == len(scenario.phases)
        assert all(r.error is None for r in results)


class TestConfigRoundTrip:
    """Builder → ExperimentConfig → from_dict → identical config."""

    def test_round_trip(self):
        original = (
            ExperimentConfigBuilder()
            .name("roundtrip")
            .sprint_duration(15)
            .database_url("mock://")
            .tracing(True)
            .disturbances(enabled=True, frequencies={"flaky_test": 0.3})
            .build()
        )

        # Serialize to dict-like form and reconstruct
        data = {
            "experiment": {
                "name": original.name,
                "sprint_duration_minutes": original.sprint_duration_minutes,
                "tracing": original.tracing_enabled,
            },
            "database": {"url": original.database_url},
            "disturbances": {
                "enabled": original.disturbances_enabled,
                "frequencies": original.disturbance_frequencies,
            },
        }
        reconstructed = ExperimentConfig.from_dict(data)

        assert reconstructed.name == original.name
        assert reconstructed.sprint_duration_minutes == original.sprint_duration_minutes
        assert reconstructed.database_url == original.database_url
        assert reconstructed.tracing_enabled == original.tracing_enabled
        assert reconstructed.disturbances_enabled == original.disturbances_enabled
        assert reconstructed.disturbance_frequencies == original.disturbance_frequencies
