"""Integration tests for stakeholder review with SprintManager components."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from src.agents.base_agent import BaseAgent, AgentConfig
from src.agents.messaging import create_message_bus
from src.orchestrator.stakeholder_notify import StakeholderNotifier
from src.tools.shared_context import SharedContextDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(role_id: str = "po", name: str = "Test PO") -> BaseAgent:
    os.environ["MOCK_LLM"] = "true"
    config = AgentConfig(
        role_id=role_id,
        name=name,
        model="mock",
        temperature=0.7,
        max_tokens=256,
        seniority="senior",
        role_archetype="leader",
    )
    return BaseAgent(config, vllm_endpoint="mock://")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stakeholder_review_with_webhook_disabled(tmp_path: Path):
    """When webhook is disabled, stakeholder_review falls back to PO-only."""
    notifier = StakeholderNotifier(
        webhook_enabled=False,
        output_dir=tmp_path,
        mock_mode=True,
    )

    # Verify send_webhook returns True (no-op)
    payload = notifier.build_payload("exp", 3, [], [], "ok")
    assert await notifier.send_webhook(payload) is True

    # Verify wait_for_feedback in mock mode returns auto_approve
    feedback = await notifier.wait_for_feedback(sprint_num=3, timeout_minutes=1)
    assert feedback.source == "auto_approve"
    assert feedback.decision == "approved"


@pytest.mark.asyncio
async def test_stakeholder_review_file_feedback_applied(tmp_path: Path):
    """Write a feedback file, verify notifier picks it up and parses it."""
    notifier = StakeholderNotifier(
        webhook_enabled=True,
        webhook_url="https://hooks.example.com/test",
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )

    # Pre-create the feedback file
    feedback_path = tmp_path / "stakeholder-feedback-sprint-6.json"
    feedback_path.write_text(
        json.dumps(
            {
                "decision": "approved_with_changes",
                "feedback_text": "Add search feature.",
                "priority_changes": [
                    {"story_id": "US-010", "action": "deprioritize", "reason": "later"}
                ],
                "new_stories": [
                    {
                        "title": "Search Feature",
                        "description": "Full-text search",
                        "priority": 1,
                    }
                ],
                "respondent": "Stakeholder A",
            }
        )
    )

    feedback = await notifier.wait_for_feedback(sprint_num=6, timeout_minutes=0.1)

    assert feedback.decision == "approved_with_changes"
    assert len(feedback.priority_changes) == 1
    assert feedback.priority_changes[0]["story_id"] == "US-010"
    assert len(feedback.new_stories) == 1
    assert feedback.new_stories[0]["title"] == "Search Feature"


@pytest.mark.asyncio
async def test_stakeholder_review_stores_in_db():
    """Feedback is persisted in SharedContextDB."""
    db = SharedContextDB("mock://")
    await db.initialize()

    feedback_data = {
        "sprint": 6,
        "source": "file",
        "decision": "approved_with_changes",
        "feedback_text": "Add search feature.",
        "priority_changes": [
            {"story_id": "US-010", "action": "deprioritize", "reason": "later"}
        ],
        "new_stories": [
            {
                "title": "Search Feature",
                "description": "Full-text search",
                "priority": 1,
            }
        ],
        "respondent": "Stakeholder A",
    }

    await db.store_stakeholder_feedback(feedback_data)

    # Retrieve and verify
    results = await db.get_stakeholder_feedback(sprint=6)
    assert len(results) == 1
    assert results[0]["decision"] == "approved_with_changes"
    assert results[0]["respondent"] == "Stakeholder A"

    # Verify unfiltered retrieval
    all_results = await db.get_stakeholder_feedback()
    assert len(all_results) == 1

    # Store another for different sprint
    await db.store_stakeholder_feedback(
        {
            "sprint": 9,
            "source": "auto_approve",
            "decision": "approved",
            "feedback_text": "Auto.",
            "respondent": "system",
        }
    )
    assert len(await db.get_stakeholder_feedback()) == 2
    assert len(await db.get_stakeholder_feedback(sprint=9)) == 1


@pytest.mark.asyncio
async def test_stakeholder_review_publishes_event():
    """Message bus event is fired after feedback is processed."""
    bus = create_message_bus()

    received_events = []

    async def capture_event(msg):
        received_events.append(msg)

    bus.subscribe("stakeholder_feedback", "test_listener", capture_event)

    # Publish the event as SprintManager would
    await bus.publish(
        "system",
        "stakeholder_feedback",
        {
            "sprint": 6,
            "decision": "approved_with_changes",
            "source": "file",
            "has_changes": True,
        },
    )

    # Give the async handler a moment to process
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    msg = received_events[0]
    assert msg.content["sprint"] == 6
    assert msg.content["decision"] == "approved_with_changes"
    assert msg.content["has_changes"] is True
