"""Kanban board management."""

from typing import List, Dict, Optional
from .shared_context import SharedContextDB

class KanbanBoard:
    def __init__(self, db: SharedContextDB):
        self.db = db
        self.wip_limits = {"in_progress": 4, "review": 2}
    
    async def pull_ready_task(self) -> Optional[Dict]:
        """Pull highest priority task from Ready column."""
        # Check WIP limits
        # Get top priority ready task
        # Move to in_progress
        pass
    
    async def get_snapshot(self) -> Dict:
        """Get current state of board."""
        pass
    
    async def move_card(self, card_id: int, new_status: str):
        """Move card to new column."""
        # Check WIP limits
        # Update status
        pass
