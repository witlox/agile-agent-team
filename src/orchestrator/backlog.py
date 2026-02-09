"""Product backlog loader and tracker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class ProductMetadata:
    """Product-level metadata extracted from backlog."""
    name: str
    description: str
    languages: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    repository_type: str = "greenfield"
    repository_url: str = ""


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
        self.data: Dict = {}  # Store full data for metadata access
        self._load()

    def _load(self):
        """Parse backlog YAML file."""
        with open(self.backlog_path) as f:
            self.data = yaml.safe_load(f)
        self.product_name = self.data.get("product", {}).get("name", "Unknown Product")
        self.product_description = self.data.get("product", {}).get("description", "")
        stories = self.data.get("stories", [])
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

    def get_product_metadata(self) -> ProductMetadata:
        """Extract product-level metadata from backlog."""
        product = self.data.get("product", {})
        repository = product.get("repository", {})
        return ProductMetadata(
            name=product.get("name", "Unknown Project"),
            description=product.get("description", ""),
            languages=product.get("languages", []),
            tech_stack=product.get("tech_stack", []),
            repository_type=repository.get("type", "greenfield"),
            repository_url=repository.get("url", "")
        )
