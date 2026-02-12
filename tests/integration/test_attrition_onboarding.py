"""Integration tests for attrition + onboarding (F-01, F-02, F-03)."""

import json
import pytest
from typing import List, Optional

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.agent_factory import AgentFactory
from src.agents.decision_tracer import DecisionTracer
from src.orchestrator.attrition import AttritionConfig, AttritionEngine
from src.orchestrator.onboarding import OnboardingConfig, OnboardingManager


def _make_agent(
    role_id: str,
    seniority: str = "mid",
    role_archetype: str = "developer",
    specializations: Optional[List[str]] = None,
    name: str = "",
) -> BaseAgent:
    config = AgentConfig(
        role_id=role_id,
        name=name or role_id,
        model="mock-model",
        temperature=0.7,
        max_tokens=100,
        seniority=seniority,
        specializations=specializations or [],
        role_archetype=role_archetype,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


class TestFullDepartureFlow:
    """Roll → remove from agent list → departure_report.json."""

    def test_departure_produces_report(self, tmp_path):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            max_departures_per_sprint=1,
            protect_roles=["dev_lead"],
        )
        engine = AttritionEngine(cfg)
        agents = [
            _make_agent(
                "dev_lead", seniority="senior", role_archetype="developer+leader"
            ),
            _make_agent("dev_mid_backend", seniority="mid"),
        ]
        departures = engine.roll_for_departures(5, agents)
        assert len(departures) == 1
        assert departures[0].agent_id == "dev_mid_backend"

        # Remove departed agent
        agents = [a for a in agents if a.agent_id != departures[0].agent_id]
        assert len(agents) == 1

        # Generate report
        engine.generate_departure_report(departures, tmp_path)
        report_path = tmp_path / "departure_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["departures"][0]["agent_id"] == "dev_mid_backend"


class TestFullBackfillFlow:
    """Departure → delay → hire → onboarding state created."""

    @pytest.mark.asyncio
    async def test_backfill_creates_agent_with_onboarding(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            backfill_enabled=True,
            backfill_delay_sprints=1,
            max_departures_per_sprint=1,
            protect_roles=["dev_lead"],
        )
        engine = AttritionEngine(cfg)
        factory = AgentFactory(
            config_dir="team_config",
            vllm_endpoint="mock://",
            agent_model_configs={},
            runtime_configs={},
        )

        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        dev = _make_agent(
            "dev_mid_backend", seniority="mid", specializations=["backend"]
        )
        agents = [lead, dev]

        # Sprint 5: departure (dev_lead is protected, only dev_mid_backend can depart)
        departures = engine.roll_for_departures(5, agents)
        assert len(departures) == 1
        dep = departures[0]
        assert dep.agent_id == "dev_mid_backend"
        agents = [a for a in agents if a.agent_id != dep.agent_id]

        # Sprint 5: not yet time for backfill (delay = 1)
        assert dep.backfill_sprint == 6

        # Sprint 6: create replacement
        new_agent = await engine.create_replacement(dep, factory, agents)
        assert new_agent is not None

        agents.append(new_agent)

        # Start onboarding
        onboarding_mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=2),
            agents=agents,
        )
        onboarding_mgr.start_onboarding(new_agent, sprint_num=6)

        assert onboarding_mgr.is_onboarding(new_agent.agent_id)
        assert (
            onboarding_mgr.get_buddy_pairing_constraint(new_agent.agent_id)
            == "dev_lead"
        )


class TestBuddyPairingForced:
    """During onboarding, new agent must pair with buddy."""

    def test_buddy_constraint_during_onboarding(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        dev_a = _make_agent("dev_a", seniority="mid")
        new_agent = _make_agent("backfill", seniority="mid")
        agents = [lead, dev_a, new_agent]

        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=2),
            agents=agents,
        )
        mgr.start_onboarding(new_agent, sprint_num=5)

        # During onboarding, constraint forces pairing with buddy
        assert mgr.get_buddy_pairing_constraint("backfill") == "dev_lead"
        # After 2 sprints, onboarding is complete
        mgr.advance_sprint("backfill")
        mgr.advance_sprint("backfill")
        assert mgr.get_buddy_pairing_constraint("backfill") is None


class TestOnboardingCompletion:
    """Onboarding completes after N sprints."""

    def test_completion_after_duration(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        agents = [lead, new_agent]

        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=3),
            agents=agents,
        )
        mgr.start_onboarding(new_agent, sprint_num=10)

        for i in range(3):
            assert mgr.is_onboarding("backfill")
            mgr.advance_sprint("backfill")
        assert not mgr.is_onboarding("backfill")


class TestTracingProducesValidFiles:
    """Tracing produces valid trace files with decision IDs."""

    @pytest.mark.asyncio
    async def test_trace_files_contain_decisions(self, tmp_path):
        agent = _make_agent("alex_dev", seniority="senior")
        tracer = DecisionTracer("alex_dev", 3)
        agent.attach_tracer(tracer)

        # Simulate sprint phases
        tracer.set_phase("planning")
        await agent.generate("Select stories for sprint 3")

        tracer.set_phase("retro")
        await agent.generate("Sprint 3 retrospective")

        # Write traces
        traces_dir = tmp_path / "traces"
        tracer.write_trace(traces_dir)

        trace_path = traces_dir / "alex_dev.json"
        assert trace_path.exists()

        data = json.loads(trace_path.read_text())
        assert data["agent_id"] == "alex_dev"
        assert data["sprint"] == 3
        assert len(data["decisions"]) == 2
        assert data["decisions"][0]["phase"] == "planning"
        assert data["decisions"][1]["phase"] == "retro"
        assert "alex_dev-s03-planning-001" == data["decisions"][0]["decision_id"]
        assert "alex_dev-s03-retro-001" == data["decisions"][1]["decision_id"]

    def test_decision_id_in_last_decision_id(self):
        agent = _make_agent("dev_a")
        tracer = DecisionTracer("dev_a", 1)
        agent.attach_tracer(tracer)
        tracer.set_phase("dev")
        tracer.record_from_generate("prompt", "response")

        assert agent.last_decision_id == "dev_a-s01-dev-001"
