"""Stakeholder notification and feedback collection via webhooks."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StakeholderReviewPayload:
    """Rich summary sent to external stakeholders via webhook."""

    experiment_name: str
    sprint: int
    timestamp: str
    sprints_since_last_review: int
    velocity_trend: List[int]
    total_features_completed: int
    avg_test_coverage: float
    avg_cycle_time: float
    disturbances_encountered: List[str]
    completed_stories: List[Dict]  # [{id, title, status}]
    po_assessment: str
    feedback_url: Optional[str] = None  # callback URL if mode=callback
    feedback_file: Optional[str] = None  # file path if mode=file


@dataclass
class StakeholderFeedback:
    """Feedback received from stakeholders (or generated on timeout)."""

    sprint: int
    source: str  # "webhook_callback" | "file" | "auto_approve" | "po_proxy" | "timeout"
    decision: str  # "approved" | "rejected" | "approved_with_changes"
    feedback_text: str
    priority_changes: List[Dict] = field(
        default_factory=list
    )  # [{story_id, action, reason}]
    new_stories: List[Dict] = field(
        default_factory=list
    )  # [{title, description, priority}]
    respondent: str = "system"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class StakeholderNotifier:
    """Sends review summaries to external webhooks and collects feedback.

    Three feedback modes:
    - file: Poll output_dir for stakeholder-feedback-sprint-{N}.json
    - callback: Start tiny aiohttp server, wait for POST
    - (fallback): PO-only review when no webhook configured
    """

    def __init__(
        self,
        webhook_url: str = "",
        webhook_enabled: bool = False,
        feedback_mode: str = "file",
        callback_port: int = 8081,
        poll_interval: int = 30,
        output_dir: Optional[Path] = None,
        mock_mode: bool = False,
    ):
        self.webhook_url = webhook_url
        self.webhook_enabled = webhook_enabled
        self.feedback_mode = feedback_mode
        self.callback_port = callback_port
        self.poll_interval = poll_interval
        self.output_dir = output_dir or Path("/tmp")
        self.mock_mode = mock_mode

    def build_payload(
        self,
        experiment_name: str,
        sprint_num: int,
        sprint_results: List[Dict],
        completed_stories: List[Dict],
        po_assessment: str,
        cadence: int = 3,
    ) -> StakeholderReviewPayload:
        """Build a review payload from sprint data.

        Args:
            experiment_name: Name of the running experiment.
            sprint_num: Current sprint number.
            sprint_results: All sprint result dicts so far.
            completed_stories: Cards in 'done' status.
            po_assessment: PO's summary feedback text.
            cadence: Review cadence (every N sprints).

        Returns:
            Frozen StakeholderReviewPayload ready for webhook delivery.
        """
        velocity_trend = [r.get("velocity", 0) for r in sprint_results]
        total_features = sum(r.get("features_completed", 0) for r in sprint_results)

        coverages = [r.get("test_coverage", 0.0) for r in sprint_results]
        avg_coverage = sum(coverages) / len(coverages) if coverages else 0.0

        cycle_times = [r.get("cycle_time_avg", 0.0) for r in sprint_results]
        avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0

        all_disturbances: List[str] = []
        for r in sprint_results:
            all_disturbances.extend(r.get("disturbances", []))

        story_summaries = [
            {
                "id": c.get("id", ""),
                "title": c.get("title", ""),
                "status": c.get("status", "done"),
            }
            for c in completed_stories
        ]

        feedback_file: Optional[str] = None
        feedback_url: Optional[str] = None
        if self.feedback_mode == "file":
            feedback_file = str(
                self.output_dir / f"stakeholder-feedback-sprint-{sprint_num}.json"
            )
        elif self.feedback_mode == "callback":
            feedback_url = (
                f"http://localhost:{self.callback_port}/feedback/{sprint_num}"
            )

        return StakeholderReviewPayload(
            experiment_name=experiment_name,
            sprint=sprint_num,
            timestamp=datetime.utcnow().isoformat(),
            sprints_since_last_review=cadence,
            velocity_trend=velocity_trend,
            total_features_completed=total_features,
            avg_test_coverage=avg_coverage,
            avg_cycle_time=avg_cycle,
            disturbances_encountered=all_disturbances,
            completed_stories=story_summaries,
            po_assessment=po_assessment,
            feedback_url=feedback_url,
            feedback_file=feedback_file,
        )

    async def send_webhook(self, payload: StakeholderReviewPayload) -> bool:
        """POST the review payload to the configured webhook URL.

        Simple retry: 3 attempts with 5s/15s/30s backoff.
        In mock mode: log payload and return True immediately.

        Returns:
            True if delivered (2xx or mock), False otherwise.
        """
        if not self.webhook_enabled:
            return True

        if self.mock_mode:
            logger.info(
                "Mock mode: skipping webhook POST for sprint %d", payload.sprint
            )
            return True

        import httpx

        payload_dict = {
            "experiment_name": payload.experiment_name,
            "sprint": payload.sprint,
            "timestamp": payload.timestamp,
            "sprints_since_last_review": payload.sprints_since_last_review,
            "velocity_trend": payload.velocity_trend,
            "total_features_completed": payload.total_features_completed,
            "avg_test_coverage": payload.avg_test_coverage,
            "avg_cycle_time": payload.avg_cycle_time,
            "disturbances_encountered": payload.disturbances_encountered,
            "completed_stories": payload.completed_stories,
            "po_assessment": payload.po_assessment,
            "feedback_url": payload.feedback_url,
            "feedback_file": payload.feedback_file,
        }

        backoff_seconds = [5, 15, 30]
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt, wait in enumerate(backoff_seconds):
                try:
                    response = await client.post(
                        self.webhook_url,
                        json=payload_dict,
                        headers={"Content-Type": "application/json"},
                    )
                    if 200 <= response.status_code < 300:
                        logger.info(
                            "Webhook delivered for sprint %d (attempt %d)",
                            payload.sprint,
                            attempt + 1,
                        )
                        return True
                    logger.warning(
                        "Webhook returned %d on attempt %d",
                        response.status_code,
                        attempt + 1,
                    )
                except Exception as exc:
                    logger.warning("Webhook attempt %d failed: %s", attempt + 1, exc)

                if attempt < len(backoff_seconds) - 1:
                    await asyncio.sleep(wait)

        logger.error(
            "Webhook delivery failed after 3 attempts for sprint %d", payload.sprint
        )
        return False

    async def wait_for_feedback(
        self,
        sprint_num: int,
        timeout_minutes: float,
        timeout_action: str = "auto_approve",
        po_generate_func=None,
    ) -> StakeholderFeedback:
        """Wait for stakeholder feedback via file or callback.

        Args:
            sprint_num: Sprint number to wait for feedback on.
            timeout_minutes: How long to wait before applying timeout action.
            timeout_action: What to do on timeout: auto_approve | po_proxy | block.
            po_generate_func: Async callable for PO proxy mode (generates PO feedback).

        Returns:
            StakeholderFeedback with decision and any backlog changes.
        """
        if self.mock_mode:
            return StakeholderFeedback(
                sprint=sprint_num,
                source="auto_approve",
                decision="approved",
                feedback_text="Auto-approved (mock mode)",
                respondent="system",
            )

        if self.feedback_mode == "file":
            return await self._wait_for_file_feedback(
                sprint_num, timeout_minutes, timeout_action, po_generate_func
            )
        elif self.feedback_mode == "callback":
            return await self._wait_for_callback_feedback(
                sprint_num, timeout_minutes, timeout_action, po_generate_func
            )
        else:
            return self._make_timeout_feedback(
                sprint_num, timeout_action, po_generate_func
            )

    async def _wait_for_file_feedback(
        self,
        sprint_num: int,
        timeout_minutes: float,
        timeout_action: str,
        po_generate_func=None,
    ) -> StakeholderFeedback:
        """Poll for a feedback JSON file in output_dir."""
        feedback_path = (
            self.output_dir / f"stakeholder-feedback-sprint-{sprint_num}.json"
        )
        timeout_seconds = timeout_minutes * 60
        elapsed = 0.0

        while elapsed < timeout_seconds:
            if feedback_path.exists():
                try:
                    data = json.loads(feedback_path.read_text())
                    return StakeholderFeedback(
                        sprint=sprint_num,
                        source="file",
                        decision=data.get("decision", "approved"),
                        feedback_text=data.get("feedback_text", ""),
                        priority_changes=data.get("priority_changes", []),
                        new_stories=data.get("new_stories", []),
                        respondent=data.get("respondent", "stakeholder"),
                    )
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.warning("Malformed feedback file: %s", exc)

            await asyncio.sleep(min(self.poll_interval, timeout_seconds - elapsed))
            elapsed += self.poll_interval

        return await self._apply_timeout_action(
            sprint_num, timeout_action, po_generate_func
        )

    async def _wait_for_callback_feedback(
        self,
        sprint_num: int,
        timeout_minutes: float,
        timeout_action: str,
        po_generate_func=None,
    ) -> StakeholderFeedback:
        """Start a tiny HTTP server and wait for a POST with feedback."""
        from aiohttp import web

        feedback_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def handle_feedback(request: web.Request) -> web.Response:
            try:
                data = await request.json()
                feedback = StakeholderFeedback(
                    sprint=sprint_num,
                    source="webhook_callback",
                    decision=data.get("decision", "approved"),
                    feedback_text=data.get("feedback_text", ""),
                    priority_changes=data.get("priority_changes", []),
                    new_stories=data.get("new_stories", []),
                    respondent=data.get("respondent", "stakeholder"),
                )
                if not feedback_future.done():
                    feedback_future.set_result(feedback)
                return web.json_response({"status": "received"})
            except Exception as exc:
                return web.json_response({"error": str(exc)}, status=400)

        app = web.Application()
        app.router.add_post(f"/feedback/{sprint_num}", handle_feedback)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.callback_port)
        await site.start()

        try:
            feedback = await asyncio.wait_for(
                feedback_future, timeout=timeout_minutes * 60
            )
            return feedback
        except asyncio.TimeoutError:
            return await self._apply_timeout_action(
                sprint_num, timeout_action, po_generate_func
            )
        finally:
            await runner.cleanup()

    async def _apply_timeout_action(
        self,
        sprint_num: int,
        timeout_action: str,
        po_generate_func=None,
    ) -> StakeholderFeedback:
        """Apply the configured timeout action."""
        if timeout_action == "po_proxy" and po_generate_func is not None:
            po_text = await po_generate_func()
            return StakeholderFeedback(
                sprint=sprint_num,
                source="po_proxy",
                decision="approved_with_changes",
                feedback_text=po_text,
                respondent="po_proxy",
            )
        elif timeout_action == "block":
            return StakeholderFeedback(
                sprint=sprint_num,
                source="timeout",
                decision="approved",
                feedback_text="Timed out waiting for stakeholder feedback (block mode).",
                respondent="system",
            )
        else:
            # Default: auto_approve
            return StakeholderFeedback(
                sprint=sprint_num,
                source="auto_approve",
                decision="approved",
                feedback_text="Auto-approved after timeout.",
                respondent="system",
            )

    def _make_timeout_feedback(
        self,
        sprint_num: int,
        timeout_action: str,
        po_generate_func=None,
    ) -> StakeholderFeedback:
        """Synchronous fallback for unknown feedback mode."""
        return StakeholderFeedback(
            sprint=sprint_num,
            source="auto_approve",
            decision="approved",
            feedback_text="Unknown feedback mode; auto-approved.",
            respondent="system",
        )
