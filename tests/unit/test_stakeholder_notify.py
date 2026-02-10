"""Unit tests for StakeholderNotifier — payload building, webhook, feedback."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestrator.stakeholder_notify import (
    StakeholderFeedback,
    StakeholderNotifier,
    StakeholderReviewPayload,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def notifier(tmp_path: Path) -> StakeholderNotifier:
    return StakeholderNotifier(
        webhook_url="https://hooks.example.com/test",
        webhook_enabled=True,
        feedback_mode="file",
        callback_port=18081,
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )


@pytest.fixture
def mock_notifier(tmp_path: Path) -> StakeholderNotifier:
    return StakeholderNotifier(
        webhook_url="https://hooks.example.com/test",
        webhook_enabled=True,
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=True,
    )


@pytest.fixture
def sprint_results() -> list:
    return [
        {
            "sprint": 1,
            "velocity": 12,
            "features_completed": 3,
            "test_coverage": 85.0,
            "cycle_time_avg": 4.5,
            "disturbances": ["flaky_test"],
        },
        {
            "sprint": 2,
            "velocity": 15,
            "features_completed": 4,
            "test_coverage": 90.0,
            "cycle_time_avg": 3.8,
            "disturbances": ["scope_creep"],
        },
        {
            "sprint": 3,
            "velocity": 10,
            "features_completed": 2,
            "test_coverage": 88.0,
            "cycle_time_avg": 5.0,
            "disturbances": [],
        },
    ]


@pytest.fixture
def done_cards() -> list:
    return [
        {"id": "US-001", "title": "User Registration", "status": "done"},
        {"id": "US-002", "title": "Login Flow", "status": "done"},
    ]


# ---------------------------------------------------------------------------
# Payload building
# ---------------------------------------------------------------------------


def test_build_payload_from_sprint_results(
    notifier: StakeholderNotifier, sprint_results: list, done_cards: list
):
    payload = notifier.build_payload(
        experiment_name="test-experiment",
        sprint_num=3,
        sprint_results=sprint_results,
        completed_stories=done_cards,
        po_assessment="Good progress overall.",
        cadence=3,
    )

    assert isinstance(payload, StakeholderReviewPayload)
    assert payload.experiment_name == "test-experiment"
    assert payload.sprint == 3
    assert payload.sprints_since_last_review == 3
    assert payload.velocity_trend == [12, 15, 10]
    assert payload.total_features_completed == 9
    assert payload.avg_test_coverage == pytest.approx(87.666, abs=0.01)
    assert payload.avg_cycle_time == pytest.approx(4.433, abs=0.01)
    assert payload.disturbances_encountered == ["flaky_test", "scope_creep"]
    assert len(payload.completed_stories) == 2
    assert payload.po_assessment == "Good progress overall."
    assert payload.feedback_file is not None
    assert "stakeholder-feedback-sprint-3" in payload.feedback_file


def test_build_payload_empty_results(
    notifier: StakeholderNotifier,
):
    payload = notifier.build_payload(
        experiment_name="empty-run",
        sprint_num=1,
        sprint_results=[],
        completed_stories=[],
        po_assessment="",
    )

    assert payload.velocity_trend == []
    assert payload.total_features_completed == 0
    assert payload.avg_test_coverage == 0.0
    assert payload.avg_cycle_time == 0.0
    assert payload.disturbances_encountered == []
    assert payload.completed_stories == []


# ---------------------------------------------------------------------------
# Webhook sending
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_webhook_success(
    notifier: StakeholderNotifier, sprint_results: list, done_cards: list
):
    payload = notifier.build_payload("exp", 3, sprint_results, done_cards, "ok")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        result = await notifier.send_webhook(payload)
        assert result is True
        mock_client_instance.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_webhook_retry_on_failure(
    notifier: StakeholderNotifier, sprint_results: list, done_cards: list
):
    payload = notifier.build_payload("exp", 3, sprint_results, done_cards, "ok")

    # All 3 attempts fail with 500
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        # Patch sleep to avoid waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await notifier.send_webhook(payload)

        assert result is False
        assert mock_client_instance.post.call_count == 3


@pytest.mark.asyncio
async def test_send_webhook_disabled_returns_true(tmp_path: Path):
    notifier = StakeholderNotifier(webhook_enabled=False, output_dir=tmp_path)
    payload = notifier.build_payload("exp", 1, [], [], "")
    result = await notifier.send_webhook(payload)
    assert result is True


@pytest.mark.asyncio
async def test_mock_mode_skips_http(
    mock_notifier: StakeholderNotifier, sprint_results: list, done_cards: list
):
    payload = mock_notifier.build_payload("exp", 3, sprint_results, done_cards, "ok")
    result = await mock_notifier.send_webhook(payload)
    assert result is True
    # No httpx import or call should happen in mock mode


# ---------------------------------------------------------------------------
# Feedback waiting — file mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_feedback_file_mode(tmp_path: Path):
    notifier = StakeholderNotifier(
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )

    # Write feedback file before waiting
    feedback_path = tmp_path / "stakeholder-feedback-sprint-3.json"
    feedback_path.write_text(
        json.dumps(
            {
                "decision": "approved_with_changes",
                "feedback_text": "Looks good, add dark mode.",
                "priority_changes": [
                    {"story_id": "US-005", "action": "deprioritize", "reason": "later"}
                ],
                "new_stories": [
                    {
                        "title": "Dark mode",
                        "description": "Add dark theme",
                        "priority": 1,
                    }
                ],
                "respondent": "Jane Stakeholder",
            }
        )
    )

    feedback = await notifier.wait_for_feedback(sprint_num=3, timeout_minutes=0.1)

    assert feedback.source == "file"
    assert feedback.decision == "approved_with_changes"
    assert feedback.feedback_text == "Looks good, add dark mode."
    assert len(feedback.priority_changes) == 1
    assert len(feedback.new_stories) == 1
    assert feedback.respondent == "Jane Stakeholder"


@pytest.mark.asyncio
async def test_wait_for_feedback_file_timeout_auto_approve(tmp_path: Path):
    notifier = StakeholderNotifier(
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )

    # No file written — should timeout
    feedback = await notifier.wait_for_feedback(
        sprint_num=5,
        timeout_minutes=0.02,  # ~1.2 seconds
        timeout_action="auto_approve",
    )

    assert feedback.source == "auto_approve"
    assert feedback.decision == "approved"
    assert "Auto-approved" in feedback.feedback_text


@pytest.mark.asyncio
async def test_wait_for_feedback_file_timeout_po_proxy(tmp_path: Path):
    notifier = StakeholderNotifier(
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )

    async def mock_po_generate():
        return "PO says: proceed with caution."

    feedback = await notifier.wait_for_feedback(
        sprint_num=5,
        timeout_minutes=0.02,
        timeout_action="po_proxy",
        po_generate_func=mock_po_generate,
    )

    assert feedback.source == "po_proxy"
    assert feedback.decision == "approved_with_changes"
    assert "PO says" in feedback.feedback_text
    assert feedback.respondent == "po_proxy"


@pytest.mark.asyncio
async def test_wait_for_feedback_file_timeout_block(tmp_path: Path):
    notifier = StakeholderNotifier(
        feedback_mode="file",
        poll_interval=1,
        output_dir=tmp_path,
        mock_mode=False,
    )

    feedback = await notifier.wait_for_feedback(
        sprint_num=5,
        timeout_minutes=0.02,
        timeout_action="block",
    )

    assert feedback.source == "timeout"
    assert feedback.decision == "approved"
    assert "block mode" in feedback.feedback_text.lower()


# ---------------------------------------------------------------------------
# Feedback waiting — callback mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_feedback_callback_mode(tmp_path: Path):
    """Start callback server and POST feedback to it."""
    port = 18082
    notifier = StakeholderNotifier(
        feedback_mode="callback",
        callback_port=port,
        output_dir=tmp_path,
        mock_mode=False,
    )

    async def post_feedback():
        await asyncio.sleep(0.5)  # Wait for server to start
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://127.0.0.1:{port}/feedback/7",
                json={
                    "decision": "rejected",
                    "feedback_text": "Not ready yet.",
                    "respondent": "Bob Stakeholder",
                },
            )

    # Run both concurrently
    poster = asyncio.create_task(post_feedback())
    feedback = await notifier.wait_for_feedback(sprint_num=7, timeout_minutes=0.5)
    await poster

    assert feedback.source == "webhook_callback"
    assert feedback.decision == "rejected"
    assert feedback.feedback_text == "Not ready yet."
    assert feedback.respondent == "Bob Stakeholder"


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


def test_feedback_dataclass_fields():
    fb = StakeholderFeedback(
        sprint=5,
        source="file",
        decision="approved",
        feedback_text="Ship it!",
        priority_changes=[
            {"story_id": "US-010", "action": "deprioritize", "reason": "done"}
        ],
        new_stories=[{"title": "New feature", "description": "Do it", "priority": 2}],
        respondent="CTO",
    )

    assert fb.sprint == 5
    assert fb.source == "file"
    assert fb.decision == "approved"
    assert fb.feedback_text == "Ship it!"
    assert len(fb.priority_changes) == 1
    assert len(fb.new_stories) == 1
    assert fb.respondent == "CTO"
    assert fb.timestamp  # Auto-populated


def test_feedback_default_timestamp():
    fb = StakeholderFeedback(
        sprint=1,
        source="auto_approve",
        decision="approved",
        feedback_text="ok",
    )
    assert fb.timestamp != ""
    assert "T" in fb.timestamp  # ISO format


def test_payload_is_frozen():
    payload = StakeholderReviewPayload(
        experiment_name="test",
        sprint=1,
        timestamp="2026-02-10T00:00:00",
        sprints_since_last_review=3,
        velocity_trend=[10],
        total_features_completed=3,
        avg_test_coverage=85.0,
        avg_cycle_time=4.0,
        disturbances_encountered=[],
        completed_stories=[],
        po_assessment="ok",
    )
    with pytest.raises(AttributeError):
        payload.sprint = 99  # type: ignore[misc]
