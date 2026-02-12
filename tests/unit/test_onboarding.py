"""Unit tests for the onboarding manager (F-02)."""

from typing import List, Optional

from src.orchestrator.onboarding import OnboardingConfig, OnboardingManager
from src.agents.base_agent import BaseAgent, AgentConfig


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


class TestBuddySelection:
    def test_prefers_dev_lead(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        senior = _make_agent("dev_sr", seniority="senior")
        new_agent = _make_agent("backfill_dev", seniority="mid")
        mgr = OnboardingManager(OnboardingConfig(), agents=[lead, senior, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        state = mgr._states["backfill_dev"]
        assert state.buddy_id == "dev_lead"

    def test_prefers_senior_with_matching_spec(self):
        senior_backend = _make_agent(
            "dev_sr_backend", seniority="senior", specializations=["backend"]
        )
        senior_frontend = _make_agent(
            "dev_sr_frontend", seniority="senior", specializations=["frontend"]
        )
        new_agent = _make_agent(
            "backfill_dev", seniority="mid", specializations=["backend"]
        )
        mgr = OnboardingManager(
            OnboardingConfig(),
            agents=[senior_backend, senior_frontend, new_agent],
        )
        mgr.start_onboarding(new_agent, sprint_num=5)
        state = mgr._states["backfill_dev"]
        assert state.buddy_id == "senior_backend" or state.buddy_id == "dev_sr_backend"
        assert state.buddy_id == "dev_sr_backend"

    def test_fallback_to_any_senior(self):
        senior = _make_agent(
            "dev_sr_networking", seniority="senior", specializations=["networking"]
        )
        new_agent = _make_agent(
            "backfill_dev", seniority="mid", specializations=["backend"]
        )
        mgr = OnboardingManager(OnboardingConfig(), agents=[senior, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        assert mgr._states["backfill_dev"].buddy_id == "dev_sr_networking"

    def test_fallback_to_mid_level(self):
        mid = _make_agent("dev_mid_backend", seniority="mid")
        new_agent = _make_agent("backfill_dev", seniority="junior")
        mgr = OnboardingManager(OnboardingConfig(), agents=[mid, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=1)
        assert mgr._states["backfill_dev"].buddy_id == "dev_mid_backend"


class TestBuddyPairingConstraint:
    def test_returns_buddy_id_during_onboarding(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=2), agents=[lead, new_agent]
        )
        mgr.start_onboarding(new_agent, sprint_num=5)
        assert mgr.get_buddy_pairing_constraint("backfill") == "dev_lead"

    def test_returns_none_after_onboarding_complete(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=2), agents=[lead, new_agent]
        )
        mgr.start_onboarding(new_agent, sprint_num=5)
        mgr.advance_sprint("backfill")
        mgr.advance_sprint("backfill")
        assert mgr.get_buddy_pairing_constraint("backfill") is None

    def test_returns_none_for_unknown_agent(self):
        mgr = OnboardingManager(OnboardingConfig())
        assert mgr.get_buddy_pairing_constraint("nonexistent") is None


class TestAdvanceSprint:
    def test_marks_complete_after_duration(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=2), agents=[lead, new_agent]
        )
        mgr.start_onboarding(new_agent, sprint_num=5)

        assert mgr.is_onboarding("backfill") is True
        mgr.advance_sprint("backfill")
        assert mgr.is_onboarding("backfill") is True
        mgr.advance_sprint("backfill")
        assert mgr.is_onboarding("backfill") is False

    def test_advance_noop_for_unknown(self):
        mgr = OnboardingManager(OnboardingConfig())
        mgr.advance_sprint("nobody")  # Should not raise


class TestStandupAnnouncement:
    def test_returns_announcement_on_first_sprint(self):
        lead = _make_agent(
            "dev_lead",
            seniority="senior",
            role_archetype="developer+leader",
            name="Lead Dev",
        )
        new_agent = _make_agent("backfill", seniority="mid", name="New Dev")
        mgr = OnboardingManager(OnboardingConfig(), agents=[lead, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        announcement = mgr.get_standup_announcement("backfill")
        assert announcement is not None
        assert "New Dev" in announcement
        assert "Lead Dev" in announcement

    def test_returns_none_after_first_sprint(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=3), agents=[lead, new_agent]
        )
        mgr.start_onboarding(new_agent, sprint_num=5)
        mgr.advance_sprint("backfill")
        assert mgr.get_standup_announcement("backfill") is None

    def test_returns_none_for_nonexistent(self):
        mgr = OnboardingManager(OnboardingConfig())
        assert mgr.get_standup_announcement("nobody") is None


class TestIsOnboarding:
    def test_true_during_false_after(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(
            OnboardingConfig(onboarding_duration_sprints=1), agents=[lead, new_agent]
        )
        mgr.start_onboarding(new_agent, sprint_num=5)
        assert mgr.is_onboarding("backfill") is True
        mgr.advance_sprint("backfill")
        assert mgr.is_onboarding("backfill") is False

    def test_false_for_unknown(self):
        mgr = OnboardingManager(OnboardingConfig())
        assert mgr.is_onboarding("nobody") is False


class TestOnboardingMetrics:
    def test_metrics_structure(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(OnboardingConfig(), agents=[lead, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        metrics = mgr.get_onboarding_metrics("backfill")
        assert metrics["agent_id"] == "backfill"
        assert metrics["hire_sprint"] == 5
        assert metrics["buddy_id"] == "dev_lead"
        assert metrics["sprints_completed"] == 0
        assert metrics["is_complete"] is False

    def test_empty_for_unknown(self):
        mgr = OnboardingManager(OnboardingConfig())
        assert mgr.get_onboarding_metrics("nobody") == {}


class TestRecordContribution:
    def test_records_first_contribution(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(OnboardingConfig(), agents=[lead, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        mgr.record_contribution("backfill", sprint_num=5, action_count=10)
        metrics = mgr.get_onboarding_metrics("backfill")
        assert metrics["first_contribution_sprint"] == 5
        assert metrics["first_contribution_action"] == 10

    def test_does_not_overwrite_first_contribution(self):
        lead = _make_agent(
            "dev_lead", seniority="senior", role_archetype="developer+leader"
        )
        new_agent = _make_agent("backfill", seniority="mid")
        mgr = OnboardingManager(OnboardingConfig(), agents=[lead, new_agent])
        mgr.start_onboarding(new_agent, sprint_num=5)
        mgr.record_contribution("backfill", sprint_num=5, action_count=10)
        mgr.record_contribution("backfill", sprint_num=6, action_count=20)
        metrics = mgr.get_onboarding_metrics("backfill")
        assert metrics["first_contribution_sprint"] == 5
        assert metrics["first_contribution_action"] == 10
