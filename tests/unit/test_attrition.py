"""Unit tests for the attrition engine (F-01)."""

import json
import random
import pytest
from typing import List, Optional

from src.orchestrator.attrition import AttritionConfig, AttritionEngine, DepartureEvent
from src.agents.base_agent import BaseAgent, AgentConfig


def _make_agent(
    role_id: str,
    seniority: str = "mid",
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
        role_archetype="developer",
    )
    return BaseAgent(config, vllm_endpoint="mock://")


class TestRollForDepartures:
    def test_disabled_returns_empty(self):
        cfg = AttritionConfig(enabled=False)
        engine = AttritionEngine(cfg)
        agents = [_make_agent("dev_a")]
        assert engine.roll_for_departures(15, agents) == []

    def test_before_starts_after_sprint_returns_empty(self):
        cfg = AttritionConfig(enabled=True, starts_after_sprint=10)
        engine = AttritionEngine(cfg)
        agents = [_make_agent("dev_a")]
        assert engine.roll_for_departures(5, agents) == []

    def test_protected_roles_not_departed(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            protect_roles=["dev_lead", "qa_lead", "po"],
        )
        engine = AttritionEngine(cfg)
        agents = [
            _make_agent("dev_lead"),
            _make_agent("qa_lead"),
            _make_agent("po"),
        ]
        deps = engine.roll_for_departures(5, agents)
        assert deps == []

    def test_probability_zero_no_departures(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=0.0,
        )
        engine = AttritionEngine(cfg)
        agents = [_make_agent("dev_a"), _make_agent("dev_b")]
        deps = engine.roll_for_departures(5, agents)
        assert deps == []

    def test_probability_one_all_eligible_depart(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            max_departures_per_sprint=10,
            protect_roles=[],
        )
        engine = AttritionEngine(cfg)
        agents = [_make_agent("dev_a"), _make_agent("dev_b"), _make_agent("dev_c")]
        deps = engine.roll_for_departures(5, agents)
        assert len(deps) == 3

    def test_max_departures_per_sprint_cap(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            max_departures_per_sprint=1,
            protect_roles=[],
        )
        engine = AttritionEngine(cfg)
        agents = [_make_agent("dev_a"), _make_agent("dev_b"), _make_agent("dev_c")]
        deps = engine.roll_for_departures(5, agents)
        assert len(deps) == 1

    def test_departure_event_data(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            backfill_enabled=True,
            backfill_delay_sprints=2,
            max_departures_per_sprint=1,
            protect_roles=[],
        )
        engine = AttritionEngine(cfg)
        agent = _make_agent(
            "dev_a", seniority="senior", specializations=["backend", "networking"]
        )
        deps = engine.roll_for_departures(10, [agent])
        assert len(deps) == 1
        d = deps[0]
        assert d.sprint == 10
        assert d.agent_id == "dev_a"
        assert d.seniority == "senior"
        assert d.specializations_lost == ["backend", "networking"]
        assert d.backfill_sprint == 12  # 10 + 2

    def test_backfill_none_when_disabled(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=1.0,
            backfill_enabled=False,
            max_departures_per_sprint=1,
            protect_roles=[],
        )
        engine = AttritionEngine(cfg)
        deps = engine.roll_for_departures(5, [_make_agent("dev_a")])
        assert deps[0].backfill_sprint is None

    def test_seeded_rng_deterministic(self):
        cfg = AttritionConfig(
            enabled=True,
            starts_after_sprint=0,
            probability_per_sprint=0.5,
            max_departures_per_sprint=10,
            protect_roles=[],
        )
        agents = [_make_agent(f"dev_{i}") for i in range(5)]
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        engine1 = AttritionEngine(cfg, rng=rng1)
        engine2 = AttritionEngine(cfg, rng=rng2)
        deps1 = engine1.roll_for_departures(5, agents)
        deps2 = engine2.roll_for_departures(5, agents)
        assert [d.agent_id for d in deps1] == [d.agent_id for d in deps2]


class TestDepartureReport:
    def test_generates_valid_json(self, tmp_path):
        events = [
            DepartureEvent(
                sprint=5,
                agent_id="dev_a",
                agent_name="Dev A",
                seniority="mid",
                specializations_lost=["backend"],
                stories_contributed=["US-001"],
                meta_learnings_count=3,
                backfill_sprint=6,
            )
        ]
        cfg = AttritionConfig()
        engine = AttritionEngine(cfg)
        engine.generate_departure_report(events, tmp_path)
        path = tmp_path / "departure_report.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["departures"]) == 1
        assert data["departures"][0]["agent_id"] == "dev_a"
        assert data["departures"][0]["backfill_sprint"] == 6


class TestCreateReplacement:
    @pytest.mark.asyncio
    async def test_returns_agent_with_fresh_state(self):
        from src.agents.agent_factory import AgentFactory

        factory = AgentFactory(
            config_dir="team_config",
            vllm_endpoint="mock://",
            agent_model_configs={},
            runtime_configs={},
        )
        departed = DepartureEvent(
            sprint=5,
            agent_id="dev_mid_backend",
            agent_name="Backend Dev",
            seniority="mid",
            specializations_lost=["backend"],
            stories_contributed=[],
            meta_learnings_count=0,
        )
        cfg = AttritionConfig()
        engine = AttritionEngine(cfg)
        new_agent = await engine.create_replacement(departed, factory, [])
        assert new_agent is not None
        assert "backfill" in new_agent.config.role_id
        assert new_agent.config.seniority == "mid"
        assert new_agent.conversation_history == []
