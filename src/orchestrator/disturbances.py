"""Disturbance injection engine for resilience testing."""

import random
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent
    from ..tools.kanban import KanbanBoard
    from ..tools.shared_context import SharedContextDB


class DisturbanceEngine:
    """Injects controlled failures and disruptions into sprint execution."""

    def __init__(
        self,
        frequencies: Dict[str, float],
        blast_radius_controls: Dict[str, float],
        rng: Optional[random.Random] = None,
    ):
        self.frequencies = frequencies
        self.max_velocity_impact = blast_radius_controls.get("max_velocity_impact", 0.30)
        self.max_quality_regression = blast_radius_controls.get("max_quality_regression", 0.15)
        self._rng = rng or random.Random()
        self._previous_velocity: Optional[float] = None
        self._previous_coverage: Optional[float] = None

    def roll_for_sprint(self, sprint_num: int) -> List[str]:
        """Determine which disturbances fire this sprint via probability rolls."""
        fired: List[str] = []
        for disturbance_type, probability in self.frequencies.items():
            if self._rng.random() < probability:
                fired.append(disturbance_type)
        return fired

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
            return {"type": disturbance_type, "impact": "unknown", "affected_agents": []}

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
            agent.conversation_history.append({
                "role": "system",
                "content": "[INCIDENT ALERT] Production system is down. All hands on deck for hotfix.",
            })
        affected = [a.config.role_id for a in agents]
        return {"impact": "hotfix_injected", "affected_agents": affected, "hotfix_card_id": card_id}

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
                card["description"] = f"[FLAKY TESTS: intermittent failures detected] {desc}"
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
            agent.conversation_history.append({
                "role": "system",
                "content": "[SCOPE CHANGE] Stakeholder added a new requirement mid-sprint.",
            })
        affected = [a.config.role_id for a in po_agents] or ["po"]
        return {"impact": "scope_creep_card_added", "affected_agents": affected, "card_id": card_id}

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
            junior.conversation_history.append({
                "role": "system",
                "content": (
                    "[CONFUSION] You misunderstood the requirements. "
                    "Please re-read the task description carefully and ask clarifying questions."
                ),
            })
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
                card["description"] = f"[TECH DEBT: refactoring required before merge] {desc}"
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
                lead_devs = [a for a in agents if "dev_lead" in a.config.role_id or "lead" in a.config.role_archetype]
                for lead in lead_devs:
                    lead.conversation_history.append({
                        "role": "system",
                        "content": (
                            f"[MERGE CONFLICT DETECTED] Card {card.get('title', 'Unknown')} has merge conflicts "
                            "with recent main branch changes. Be available to help the pair resolve conflicts."
                        ),
                    })
                    affected.append(lead.config.role_id)

        return {"impact": "merge_conflict_injected", "affected_agents": affected}
