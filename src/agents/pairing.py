"""Pairing engine for dialogue-driven collaborative programming."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .base_agent import BaseAgent


class PairingEngine:
    """Orchestrates TDD pairing sessions between agent pairs."""

    def __init__(self, agents: List[BaseAgent], db=None):
        self.agents = agents
        self.active_sessions: List[asyncio.Task] = []
        self._busy_agents: set = set()
        self.db = db  # Optional SharedContextDB for logging

    def get_available_pairs(self) -> List[Tuple[BaseAgent, BaseAgent]]:
        """Find agents available for pairing (not currently in a session)."""
        available = [a for a in self.agents if a.config.role_id not in self._busy_agents]
        pairs: List[Tuple[BaseAgent, BaseAgent]] = []
        for i in range(0, len(available) - 1, 2):
            pairs.append((available[i], available[i + 1]))
        return pairs

    async def run_pairing_session(
        self, pair: Tuple[BaseAgent, BaseAgent], task: Dict
    ) -> Dict:
        """Execute TDD pairing session with dialogue checkpoints.

        Returns a session result dict.
        """
        driver, navigator = pair
        self._busy_agents.add(driver.config.role_id)
        self._busy_agents.add(navigator.config.role_id)

        start_time = datetime.utcnow()
        session_result: Dict = {
            "sprint": task.get("sprint", 0),
            "driver_id": driver.config.role_id,
            "navigator_id": navigator.config.role_id,
            "task_id": task.get("id"),
            "start_time": start_time.isoformat(),
            "outcome": "pending",
            "decisions": {},
        }

        try:
            # Phase 1: Design dialogue
            approach = await self.brainstorm_approaches(driver, navigator, task)
            session_result["decisions"]["approach"] = approach

            # Phase 2: TDD cycles with checkpoints
            implementation = await self.collaborative_implementation(
                driver, navigator, task, approach
            )
            session_result["decisions"]["implementation"] = implementation

            # Phase 3: Consensus
            approved = await self.get_consensus(driver, navigator, implementation)

            if approved:
                await self.commit(implementation, pair, task)
                session_result["outcome"] = "completed"
            else:
                await self.escalate(pair, task, implementation)
                session_result["outcome"] = "escalated"
        finally:
            self._busy_agents.discard(driver.config.role_id)
            self._busy_agents.discard(navigator.config.role_id)
            session_result["end_time"] = datetime.utcnow().isoformat()

        if self.db is not None:
            await self.db.log_pairing_session(session_result)

        return session_result

    async def brainstorm_approaches(
        self, driver: BaseAgent, navigator: BaseAgent, task: Dict
    ) -> str:
        """Initial design discussion between pair.

        Runs 3 rounds of dialogue and returns an agreed approach.
        """
        task_desc = task.get("description", task.get("title", "unknown task"))
        prompt = f"Task: {task_desc}\nPropose an implementation approach."

        approaches: List[str] = []
        for i in range(3):
            if i % 2 == 0:
                resp = await driver.generate(prompt)
            else:
                resp = await navigator.generate(
                    f"Driver proposes: {approaches[-1]}\nDo you agree or suggest changes?"
                )
            approaches.append(resp)

        # Final agreement from driver
        agreed = await driver.generate(
            f"Based on our discussion, our agreed approach is: {approaches[-1]}"
        )
        return agreed

    async def collaborative_implementation(
        self,
        driver: BaseAgent,
        navigator: BaseAgent,
        task: Dict,
        approach: str,
    ) -> str:
        """TDD implementation with checkpoint dialogues (4 checkpoints)."""
        task_desc = task.get("description", task.get("title", "unknown task"))
        implementation_parts: List[str] = []

        for checkpoint in range(1, 5):
            progress = (checkpoint / 4) * 100
            prompt = (
                f"Implementing: {task_desc}\n"
                f"Approach: {approach}\n"
                f"Checkpoint {checkpoint}/4 ({progress:.0f}%): "
                f"Write the next part of the implementation."
            )
            code = await driver.generate(prompt)
            implementation_parts.append(code)

            # Navigator reviews at each checkpoint
            review_prompt = (
                f"Review checkpoint {checkpoint}/4:\n{code}\n"
                "Any issues or suggestions?"
            )
            feedback = await navigator.generate(review_prompt)
            if feedback and "issue" in feedback.lower():
                # Driver incorporates feedback
                revised = await driver.generate(
                    f"Incorporating feedback: {feedback}\nRevised implementation:"
                )
                implementation_parts.append(revised)

        return "\n".join(implementation_parts)

    async def get_consensus(
        self, driver: BaseAgent, navigator: BaseAgent, implementation: str
    ) -> bool:
        """Both agents review the implementation and approve or reject.

        Returns True only if both approve.
        """
        driver_review = await driver.generate(
            f"Final review — approve this implementation? Reply 'approve' or 'reject':\n"
            f"{implementation[:200]}"
        )
        navigator_review = await navigator.generate(
            f"Final review — approve this implementation? Reply 'approve' or 'reject':\n"
            f"{implementation[:200]}"
        )
        driver_approved = "approve" in driver_review.lower()
        navigator_approved = "approve" in navigator_review.lower()
        return driver_approved and navigator_approved

    async def commit(
        self, implementation: str, pair: Tuple[BaseAgent, BaseAgent], task: Dict
    ):
        """Mark task as done in the kanban (if board is accessible via db)."""
        # The kanban board is not directly held here; the sprint_manager
        # handles moving the card after commit. This method logs intent.
        driver, navigator = pair
        await driver.generate(
            f"Committing implementation for task {task.get('id')}. "
            "Marking as done."
        )

    async def escalate(
        self, pair: Tuple[BaseAgent, BaseAgent], task: Dict, implementation: str
    ):
        """Log escalation when pair cannot reach consensus."""
        driver, navigator = pair
        escalation_note = (
            f"ESCALATION: Task {task.get('id')} — pair "
            f"{driver.config.role_id}/{navigator.config.role_id} "
            "could not reach consensus."
        )
        if self.db is not None:
            await self.db.log_pairing_session(
                {
                    "sprint": task.get("sprint", 0),
                    "driver_id": driver.config.role_id,
                    "navigator_id": navigator.config.role_id,
                    "task_id": task.get("id"),
                    "outcome": "escalated",
                    "decisions": {"note": escalation_note},
                }
            )

    async def wait_for_completion(self):
        """Wait for all active pairing sessions to finish."""
        if self.active_sessions:
            await asyncio.gather(*self.active_sessions, return_exceptions=True)
            self.active_sessions.clear()
