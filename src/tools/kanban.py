"""Kanban board management."""

from typing import Dict, List, Optional

from .shared_context import SharedContextDB

# Valid board column statuses in workflow order
STATUSES = ["backlog", "ready", "in_progress", "review", "done"]


class WipLimitExceeded(Exception):
    """Raised when moving a card would exceed the WIP limit for a column."""


class KanbanBoard:
    """Kanban board backed by SharedContextDB."""

    def __init__(
        self,
        db: SharedContextDB,
        wip_limits: Optional[Dict[str, int]] = None,
        team_id: str = "",
    ):
        self.db = db
        self.wip_limits: Dict[str, int] = wip_limits or {"in_progress": 4, "review": 2}
        self.team_id = team_id

    async def add_card(self, card_data: Dict) -> int:
        """Add a new card to the board and return its id."""
        if self.team_id:
            card_data = dict(card_data)
            card_data["team_id"] = self.team_id
        return await self.db.add_card(card_data)

    async def pull_ready_task(self) -> Optional[Dict]:
        """Pull highest priority task from Ready column.

        Returns the card dict if one was moved to in_progress, else None.
        """
        wip = await self._get_wip_count("in_progress")
        if wip >= self.wip_limits.get("in_progress", 4):
            return None

        ready_cards = await self.get_cards_by_status("ready")
        if not ready_cards:
            return None

        # Take the first (highest priority = lowest id) ready card
        card = ready_cards[0]
        await self.db.update_card_status(card["id"], "in_progress")
        card["status"] = "in_progress"
        return card

    async def get_cards_by_status(self, status: str) -> List[Dict]:
        """Return cards for given status, scoped to team_id when set."""
        if self.team_id:
            return await self.db.get_cards_by_status_for_team(status, self.team_id)
        return await self.db.get_cards_by_status(status)

    async def _get_wip_count(self, status: str) -> int:
        """Return WIP count, scoped to team_id when set."""
        if self.team_id:
            return await self.db.get_wip_count_for_team(status, self.team_id)
        return await self.db.get_wip_count(status)

    async def get_snapshot(self) -> Dict:
        """Get current state of board grouped by status column."""
        snapshot: Dict[str, List[Dict]] = {s: [] for s in STATUSES}
        for status in STATUSES:
            snapshot[status] = await self.get_cards_by_status(status)
        return snapshot

    async def move_card(self, card_id: int, new_status: str):
        """Move card to new column, respecting WIP limits.

        Raises WipLimitExceeded if the target column is at capacity.
        """
        if new_status not in STATUSES:
            raise ValueError(
                f"Unknown status '{new_status}'. Must be one of {STATUSES}"
            )

        if new_status in self.wip_limits:
            current_wip = await self._get_wip_count(new_status)
            if current_wip >= self.wip_limits[new_status]:
                raise WipLimitExceeded(
                    f"WIP limit for '{new_status}' is {self.wip_limits[new_status]}, "
                    f"currently at {current_wip}"
                )

        await self.db.update_card_status(card_id, new_status)
