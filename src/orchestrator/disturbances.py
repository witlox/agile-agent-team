"""Hybrid disturbance injection and detection engine.

Supports two modes:
1. INJECTION: Artificially inject disturbances (production_incidents, scope_creep)
2. DETECTION: Monitor for naturally occurring issues (flaky_tests, merge_conflicts, test_failures)
"""

import random
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent
    from ..tools.kanban import KanbanBoard
    from ..tools.shared_context import SharedContextDB


class DisturbanceEngine:
    """Hybrid disturbance injection and detection system.

    Injects: production_incidents, scope_creep (can't occur naturally)
    Detects: flaky_tests, merge_conflicts, test_failures, technical_debt (occur organically)
    """

    # Disturbances that require artificial injection
    INJECT_ONLY = {"production_incident", "scope_creep"}

    # Disturbances that occur naturally (detected, not injected)
    NATURAL_ONLY = {"flaky_test", "merge_conflict", "test_failures", "technical_debt"}

    def __init__(
        self,
        frequencies: Dict[str, float],
        blast_radius_controls: Dict[str, float],
        rng: Optional[random.Random] = None,
        natural_monitoring: bool = True,
    ):
        self.frequencies = frequencies
        self.natural_monitoring = natural_monitoring
        self.max_velocity_impact = blast_radius_controls.get(
            "max_velocity_impact", 0.30
        )
        self.max_quality_regression = blast_radius_controls.get(
            "max_quality_regression", 0.15
        )
        self._rng = rng or random.Random()
        self._previous_velocity: Optional[float] = None
        self._previous_coverage: Optional[float] = None

        # Track naturally detected disturbances this sprint
        self._detected_natural: Set[str] = set()

    def roll_for_sprint(self, sprint_num: int) -> List[str]:
        """Determine which INJECTABLE disturbances fire this sprint.

        Only rolls for disturbances that require injection (can't occur naturally).
        Natural disturbances are detected during sprint execution.
        """
        fired: List[str] = []
        for disturbance_type, probability in self.frequencies.items():
            # Only inject disturbances that can't occur naturally
            if disturbance_type in self.INJECT_ONLY:
                if self._rng.random() < probability:
                    fired.append(disturbance_type)
        return fired

    def reset_detection(self) -> None:
        """Reset natural disturbance detection for new sprint."""
        self._detected_natural.clear()

    def get_detected_natural(self) -> List[str]:
        """Get list of naturally detected disturbances this sprint."""
        return list(self._detected_natural)

    async def apply(
        self,
        disturbance_type: str,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Apply a disturbance and return an impact summary."""
        handlers = {
            "dependency_breaks": self._apply_dependency_break,
            "production_incident": self._apply_production_incident,
            "flaky_test": self._apply_flaky_test,
            "scope_creep": self._apply_scope_creep,
            "junior_misunderstanding": self._apply_junior_misunderstanding,
            "architectural_debt_surfaces": self._apply_architectural_debt,
            "merge_conflict": self._apply_merge_conflict,
        }
        handler = handlers.get(disturbance_type)
        if handler is None:
            return {
                "type": disturbance_type,
                "impact": "unknown",
                "affected_agents": [],
            }

        result = await handler(agents, kanban, db)
        result["type"] = disturbance_type
        await db.log_disturbance(result)
        return result

    async def _apply_dependency_break(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Block a random in-progress card by marking it as BLOCKED."""
        snapshot = await kanban.get_snapshot()
        in_progress = snapshot.get("in_progress", [])
        affected: List[str] = []
        if in_progress:
            card = self._rng.choice(in_progress)
            card_id = card.get("id")
            if card_id is not None:
                desc = card.get("description", "")
                card["description"] = f"[BLOCKED: dependency unavailable] {desc}"
                await db.update_card_field(card_id, "description", card["description"])
                affected = [str(card_id)]
        return {"impact": "blocked_card", "affected_agents": affected}

    async def _apply_production_incident(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Inject a hotfix task and inject urgent context into all agents."""
        hotfix_card = {
            "title": "HOTFIX: Production incident",
            "description": "[URGENT] Production system is down. Investigate and fix immediately.",
            "status": "ready",
            "story_points": 3,
            "sprint": 0,
        }
        card_id = await db.add_card(hotfix_card)
        # Inject urgency context into all agents
        for agent in agents:
            agent.conversation_history.append(
                {
                    "role": "system",
                    "content": "[INCIDENT ALERT] Production system is down. All hands on deck for hotfix.",
                }
            )
        affected = [a.config.role_id for a in agents]
        return {
            "impact": "hotfix_injected",
            "affected_agents": affected,
            "hotfix_card_id": card_id,
        }

    async def _apply_flaky_test(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Mark a random card's tests as flaky."""
        snapshot = await kanban.get_snapshot()
        review_cards = snapshot.get("review", [])
        in_progress = snapshot.get("in_progress", [])
        candidates = review_cards + in_progress
        affected: List[str] = []
        if candidates:
            card = self._rng.choice(candidates)
            card_id = card.get("id")
            if card_id is not None:
                desc = card.get("description", "")
                card[
                    "description"
                ] = f"[FLAKY TESTS: intermittent failures detected] {desc}"
                await db.update_card_field(card_id, "description", card["description"])
                affected = [str(card_id)]
        return {"impact": "flaky_tests_flagged", "affected_agents": affected}

    async def _apply_scope_creep(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """PO adds an unplanned card mid-sprint."""
        scope_card = {
            "title": "Scope creep: additional requirement from stakeholder",
            "description": "[ADDED MID-SPRINT] Stakeholder requests additional feature.",
            "status": "ready",
            "story_points": 2,
            "sprint": 0,
        }
        card_id = await db.add_card(scope_card)
        # Notify PO agent
        po_agents = [a for a in agents if a.config.role_id == "po"]
        for agent in po_agents:
            agent.conversation_history.append(
                {
                    "role": "system",
                    "content": "[SCOPE CHANGE] Stakeholder added a new requirement mid-sprint.",
                }
            )
        affected = [a.config.role_id for a in po_agents] or ["po"]
        return {
            "impact": "scope_creep_card_added",
            "affected_agents": affected,
            "card_id": card_id,
        }

    async def _apply_junior_misunderstanding(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Inject confused context into a junior developer."""
        juniors = [a for a in agents if "jr" in a.config.role_id]
        affected: List[str] = []
        if juniors:
            junior = self._rng.choice(juniors)
            junior.conversation_history.append(
                {
                    "role": "system",
                    "content": (
                        "[CONFUSION] You misunderstood the requirements. "
                        "Please re-read the task description carefully and ask clarifying questions."
                    ),
                }
            )
            affected = [junior.config.role_id]
        return {"impact": "junior_confused", "affected_agents": affected}

    async def _apply_architectural_debt(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Mark a random in-progress card as requiring refactoring."""
        snapshot = await kanban.get_snapshot()
        in_progress = snapshot.get("in_progress", [])
        affected: List[str] = []
        if in_progress:
            card = self._rng.choice(in_progress)
            card_id = card.get("id")
            if card_id is not None:
                desc = card.get("description", "")
                card[
                    "description"
                ] = f"[TECH DEBT: refactoring required before merge] {desc}"
                await db.update_card_field(card_id, "description", card["description"])
                affected = [str(card_id)]
        return {"impact": "architectural_debt_surfaced", "affected_agents": affected}

    async def _apply_merge_conflict(
        self,
        agents: List["BaseAgent"],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> Dict:
        """Inject merge conflict scenario into a random in-progress card.

        Simulates: Another pair merged to main touching the same files.
        The current pair must resolve conflicts when rebasing/merging.
        """
        snapshot = await kanban.get_snapshot()
        in_progress = snapshot.get("in_progress", [])
        affected: List[str] = []

        if in_progress:
            card = self._rng.choice(in_progress)
            card_id = card.get("id")
            if card_id is not None:
                desc = card.get("description", "")
                card["description"] = (
                    f"[MERGE CONFLICT: main branch updated with overlapping changes] {desc}\n\n"
                    "Another pair merged changes to the same files you're working on. "
                    "You'll need to rebase your feature branch on main and resolve conflicts. "
                    "Reach out to the other pair if needed to understand their changes."
                )
                await db.update_card_field(card_id, "description", card["description"])
                affected = [str(card_id)]

                # Notify the dev lead to be available for conflict resolution
                lead_devs = [
                    a
                    for a in agents
                    if "dev_lead" in a.config.role_id
                    or "lead" in a.config.role_archetype
                ]
                for lead in lead_devs:
                    lead.conversation_history.append(
                        {
                            "role": "system",
                            "content": (
                                f"[MERGE CONFLICT DETECTED] Card {card.get('title', 'Unknown')} has merge conflicts "
                                "with recent main branch changes. Be available to help the pair resolve conflicts."
                            ),
                        }
                    )
                    affected.append(lead.config.role_id)

        return {"impact": "merge_conflict_injected", "affected_agents": affected}

    # =========================================================================
    # Natural Disturbance Detection (Organic Issues)
    # =========================================================================

    async def detect_flaky_tests(
        self,
        card_id: str,
        test_results: List[Dict],
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> bool:
        """Detect flaky tests from inconsistent test results.

        Args:
            card_id: Card being tested
            test_results: List of test run results (from multiple attempts)
            kanban: Kanban board
            db: Database

        Returns:
            True if flaky tests detected
        """
        if not self.natural_monitoring or len(test_results) < 2:
            return False

        # Check for inconsistent results across runs
        pass_counts = [r.get("passed", 0) for r in test_results]
        fail_counts = [r.get("failed", 0) for r in test_results]

        # Flaky if results differ across runs
        is_flaky = len(set(pass_counts)) > 1 or len(set(fail_counts)) > 1

        if is_flaky and "flaky_test" not in self._detected_natural:
            # Mark card with flaky test detection
            snapshot = await kanban.get_snapshot()
            for status_cards in snapshot.values():
                for card in status_cards:
                    if card.get("id") == card_id:
                        desc = card.get("description", "")
                        if "[FLAKY TESTS" not in desc:
                            new_desc = f"[FLAKY TESTS: naturally detected - inconsistent test results] {desc}"
                            await db.update_card_field(card_id, "description", new_desc)

            self._detected_natural.add("flaky_test")
            await db.log_disturbance(
                {
                    "type": "flaky_test",
                    "impact": "flaky_tests_detected_natural",
                    "affected_agents": [card_id],
                    "natural": True,
                    "test_runs": len(test_results),
                }
            )

        return is_flaky

    async def detect_merge_conflict(
        self,
        card_id: str,
        git_error: str,
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> bool:
        """Detect merge conflict from git operation failure.

        Args:
            card_id: Card experiencing conflict
            git_error: Error message from git command
            kanban: Kanban board
            db: Database

        Returns:
            True if merge conflict detected
        """
        if not self.natural_monitoring:
            return False

        # Check if error indicates merge conflict
        is_conflict = "CONFLICT" in git_error or "conflict" in git_error.lower()

        if is_conflict and "merge_conflict" not in self._detected_natural:
            # Mark card with natural merge conflict
            snapshot = await kanban.get_snapshot()
            for status_cards in snapshot.values():
                for card in status_cards:
                    if card.get("id") == card_id:
                        desc = card.get("description", "")
                        if "[MERGE CONFLICT" not in desc:
                            new_desc = (
                                f"[MERGE CONFLICT: naturally occurred during git merge] {desc}\n\n"
                                f"Git error: {git_error[:200]}"
                            )
                            await db.update_card_field(card_id, "description", new_desc)

            self._detected_natural.add("merge_conflict")
            await db.log_disturbance(
                {
                    "type": "merge_conflict",
                    "impact": "merge_conflict_detected_natural",
                    "affected_agents": [card_id],
                    "natural": True,
                    "error": git_error[:500],
                }
            )

        return is_conflict

    async def detect_test_failures(
        self,
        card_id: str,
        iteration_count: int,
        final_result: Dict,
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> bool:
        """Detect persistent test failures requiring multiple iterations.

        Args:
            card_id: Card being developed
            iteration_count: Number of test-fix iterations
            final_result: Final test result
            kanban: Kanban board
            db: Database

        Returns:
            True if significant test failures detected
        """
        if not self.natural_monitoring:
            return False

        # Significant if required 3+ iterations or tests still failing
        is_significant = iteration_count >= 3 or not final_result.get("passed", False)

        if is_significant and "test_failures" not in self._detected_natural:
            self._detected_natural.add("test_failures")
            await db.log_disturbance(
                {
                    "type": "test_failures",
                    "impact": "test_failures_detected_natural",
                    "affected_agents": [card_id],
                    "natural": True,
                    "iterations": iteration_count,
                    "final_passed": final_result.get("passed", False),
                }
            )

        return is_significant

    async def detect_technical_debt(
        self,
        card_id: str,
        code_review_feedback: str,
        kanban: "KanbanBoard",
        db: "SharedContextDB",
    ) -> bool:
        """Detect technical debt from code review feedback.

        Args:
            card_id: Card under review
            code_review_feedback: Navigator's review comments
            kanban: Kanban board
            db: Database

        Returns:
            True if technical debt detected
        """
        if not self.natural_monitoring:
            return False

        # Detect debt keywords in review feedback
        debt_keywords = [
            "refactor",
            "technical debt",
            "code smell",
            "duplicate",
            "complex",
            "hard to maintain",
        ]
        has_debt = any(
            keyword in code_review_feedback.lower() for keyword in debt_keywords
        )

        if has_debt and "technical_debt" not in self._detected_natural:
            # Mark card with natural tech debt detection
            snapshot = await kanban.get_snapshot()
            for status_cards in snapshot.values():
                for card in status_cards:
                    if card.get("id") == card_id:
                        desc = card.get("description", "")
                        if "[TECH DEBT" not in desc:
                            new_desc = (
                                f"[TECH DEBT: naturally detected in code review] {desc}"
                            )
                            await db.update_card_field(card_id, "description", new_desc)

            self._detected_natural.add("technical_debt")
            await db.log_disturbance(
                {
                    "type": "technical_debt",
                    "impact": "technical_debt_detected_natural",
                    "affected_agents": [card_id],
                    "natural": True,
                    "review_feedback": code_review_feedback[:500],
                }
            )

        return has_debt
