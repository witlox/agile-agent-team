"""Product backlog loader and tracker."""

from pathlib import Path
from typing import Dict, List, Optional

import yaml


class Backlog:
    """Loads and tracks user stories from backlog.yaml.

    Stories are sorted by priority and served in order.
    Once a story has been selected for a sprint it is not offered again.
    """

    def __init__(self, backlog_path: str):
        self.backlog_path = Path(backlog_path)
        self.product_name: str = ""
        self.product_description: str = ""
        self._stories: List[Dict] = []
        self._selected_ids: set = set()
        self._load()

    def _load(self):
        """Parse backlog YAML file."""
        with open(self.backlog_path) as f:
            data = yaml.safe_load(f)
        self.product_name = data.get("product", {}).get("name", "Unknown Product")
        self.product_description = data.get("product", {}).get("description", "")
        stories = data.get("stories", [])
        self._stories = sorted(stories, key=lambda s: s.get("priority", 999))

    def next_stories(self, n: int) -> List[Dict]:
        """Return up to n highest-priority stories not yet selected."""
        available = [s for s in self._stories if s["id"] not in self._selected_ids]
        selected = available[:n]
        for story in selected:
            self._selected_ids.add(story["id"])
        return selected

    def mark_returned(self, story_id: str):
        """Return a story to the pool (e.g. rejected by PO)."""
        self._selected_ids.discard(story_id)

    @property
    def remaining(self) -> int:
        """Number of stories not yet selected."""
        return len([s for s in self._stories if s["id"] not in self._selected_ids])

    def summary(self) -> str:
        """One-line product summary for use in PO prompts."""
        return f"{self.product_name}: {self.product_description.strip()}"
