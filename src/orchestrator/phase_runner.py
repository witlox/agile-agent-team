"""Phase-level execution API for RL environment integration.

Enables running individual sprint phases in isolation for episode-level
training. Wraps SprintManager's phase methods with setup/teardown and
structured output.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sprint_manager import SprintManager


@dataclass
class PhaseResult:
    """Result of a single phase execution."""

    phase: str
    sprint_num: int
    duration_seconds: float
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    kanban_snapshot: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class PhaseRunner:
    """Runs individual sprint phases in isolation.

    Wraps SprintManager's phase methods with setup/teardown and structured
    output.  Used by dojo for episode-level training (2-10 minute focused
    episodes).

    Usage::

        runner = PhaseRunner(sprint_manager)
        result = await runner.run_phase("planning", sprint_num=3)
        result = await runner.run_phase("development", sprint_num=3,
                                         duration_minutes=5)
    """

    PHASES = ["planning", "development", "qa_review", "retro", "meta_learning"]

    def __init__(self, sprint_manager: "SprintManager") -> None:
        self._sm = sprint_manager

    async def run_phase(
        self,
        phase: str,
        sprint_num: int,
        duration_minutes: Optional[int] = None,
    ) -> PhaseResult:
        """Run a single phase and return structured results.

        Args:
            phase: One of PHASES.
            sprint_num: Sprint number for context.
            duration_minutes: Override wall-clock duration (development only).

        Returns:
            PhaseResult with phase artifacts, decisions, and kanban snapshot.

        Raises:
            ValueError: If phase name is invalid.
        """
        if phase not in self.PHASES:
            raise ValueError(f"Unknown phase: {phase!r}. Valid phases: {self.PHASES}")

        # Attach tracers if tracing is enabled and not already attached
        tracing = getattr(self._sm.config, "tracing_enabled", False)
        if tracing:
            self._sm._attach_tracers(sprint_num)

        self._sm._set_agent_phase(phase)
        start = time.monotonic()
        error: Optional[str] = None
        artifacts: Dict[str, Any] = {}

        try:
            artifacts = await self._dispatch(phase, sprint_num, duration_minutes)
        except Exception as exc:
            error = str(exc)

        elapsed = time.monotonic() - start

        # Collect decisions from tracers
        decisions: List[Dict[str, Any]] = []
        if tracing:
            for agent in self._sm.agents:
                if agent._tracer is not None:
                    for d in agent._tracer.decisions:
                        if d.phase == phase:
                            decisions.append(
                                {
                                    "decision_id": d.decision_id,
                                    "agent_id": agent.agent_id,
                                    "action_type": d.action_type,
                                    "phase": d.phase,
                                    "timestamp": d.timestamp,
                                }
                            )

        # Kanban snapshot
        kanban_snapshot = await self._sm.kanban.get_snapshot()

        return PhaseResult(
            phase=phase,
            sprint_num=sprint_num,
            duration_seconds=elapsed,
            decisions=decisions,
            artifacts=artifacts,
            kanban_snapshot=kanban_snapshot,
            error=error,
        )

    async def run_sequence(
        self,
        phases: List[str],
        sprint_num: int,
    ) -> List[PhaseResult]:
        """Run multiple phases sequentially, returning results for each.

        Args:
            phases: Ordered list of phase names to run.
            sprint_num: Sprint number for context.

        Returns:
            List of PhaseResult, one per phase.
        """
        results: List[PhaseResult] = []
        for phase in phases:
            result = await self.run_phase(phase, sprint_num)
            results.append(result)
            if result.error:
                break  # Stop on first error
        return results

    async def _dispatch(
        self,
        phase: str,
        sprint_num: int,
        duration_minutes: Optional[int],
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate SprintManager method."""
        if phase == "planning":
            result = await self._sm.run_planning(sprint_num)
            return result if isinstance(result, dict) else {}
        elif phase == "development":
            result = await self._sm.run_development(
                sprint_num, duration_override=duration_minutes
            )
            return result if isinstance(result, dict) else {}
        elif phase == "qa_review":
            result = await self._sm.run_qa_review(sprint_num)
            return result if isinstance(result, dict) else {}
        elif phase == "retro":
            result = await self._sm.run_retrospective(sprint_num)
            return result if isinstance(result, dict) else {}
        elif phase == "meta_learning":
            # Get retro data from last sprint result if available
            retro_data = (
                self._sm._sprint_results[-1]
                if self._sm._sprint_results
                else {"sprint": sprint_num, "keep": [], "drop": [], "puzzle": []}
            )
            await self._sm.apply_meta_learning(sprint_num, retro_data)
            return {"applied": True}
        return {}
