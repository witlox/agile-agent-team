"""Structured behavioral trace export with unique decision IDs.

Records every agent decision for reward attribution in RL environments.
Each decision gets a unique ID formatted as:
    {agent_id}-s{sprint:02d}-{phase}-{seq:03d}

Decision traces are written per-agent as JSON files under
<output>/sprint-NN/traces/<agent_id>.json.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Decision:
    """A single recorded agent decision."""

    decision_id: str
    timestamp: str
    phase: str
    context: str  # Truncated input (first 500 chars)
    action_type: str  # generate | execute_coding_task | checkpoint_decision | ask_question
    action_content: str  # Truncated output (first 1000 chars)
    reasoning_trace: str  # Full response (for models that produce CoT)
    outcome: Optional[str] = None  # Populated post-hoc by external pipeline
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionTracer:
    """Records agent decisions and generates unique decision IDs.

    Lifecycle: one tracer per agent per sprint. SprintManager creates tracers
    at sprint start, calls ``set_phase()`` at each ceremony boundary, and
    writes traces during artifact generation.
    """

    def __init__(self, agent_id: str, sprint_num: int) -> None:
        self._agent_id = agent_id
        self._sprint_num = sprint_num
        self._phase: str = "unknown"
        self._seq: int = 0
        self._decisions: List[Decision] = []

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def sprint_num(self) -> int:
        return self._sprint_num

    @property
    def current_phase(self) -> str:
        return self._phase

    @property
    def decisions(self) -> List[Decision]:
        return list(self._decisions)

    @property
    def last_decision_id(self) -> str:
        """Return the most recent decision ID, or empty string if none."""
        if not self._decisions:
            return ""
        return self._decisions[-1].decision_id

    def set_phase(self, phase: str) -> None:
        """Set the current sprint phase. Resets the per-phase sequence counter."""
        self._phase = phase
        self._seq = 0

    def next_decision_id(self) -> str:
        """Generate and return the next decision ID (increments sequence)."""
        self._seq += 1
        return (
            f"{self._agent_id}-s{self._sprint_num:02d}-"
            f"{self._phase}-{self._seq:03d}"
        )

    def record(self, decision: Decision) -> None:
        """Append a decision to the trace log."""
        self._decisions.append(decision)

    def record_from_generate(
        self,
        context: str,
        response: str,
        action_type: str = "generate",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Convenience: create and record a decision from a generate() call.

        Returns the decision_id assigned.
        """
        decision_id = self.next_decision_id()
        decision = Decision(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=self._phase,
            context=context[:500],
            action_type=action_type,
            action_content=response[:1000],
            reasoning_trace=response,
            metadata=metadata or {},
        )
        self.record(decision)
        return decision_id

    def record_from_coding_task(
        self,
        context: str,
        result: Dict[str, Any],
    ) -> str:
        """Convenience: create and record a decision from execute_coding_task().

        Returns the decision_id assigned.
        """
        decision_id = self.next_decision_id()
        content = result.get("content", "")
        decision = Decision(
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            phase=self._phase,
            context=context[:500],
            action_type="execute_coding_task",
            action_content=content[:1000],
            reasoning_trace=content,
            metadata={
                "files_changed": result.get("files_changed", []),
                "tool_calls": result.get("tool_calls", []),
                "turns": result.get("turns", 0),
                "success": result.get("success", False),
            },
        )
        self.record(decision)
        return decision_id

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full trace for JSON export."""
        return {
            "agent_id": self._agent_id,
            "sprint": self._sprint_num,
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "timestamp": d.timestamp,
                    "phase": d.phase,
                    "context": d.context,
                    "action_type": d.action_type,
                    "action_content": d.action_content,
                    "reasoning_trace": d.reasoning_trace,
                    "outcome": d.outcome,
                    "metadata": d.metadata,
                }
                for d in self._decisions
            ],
        }

    def write_trace(self, output_dir: Path) -> None:
        """Write the trace to ``output_dir/<agent_id>.json``."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{self._agent_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
