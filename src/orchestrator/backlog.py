"""Product backlog loader and tracker."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

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
    # Stakeholder context
    mission: str = ""
    vision: str = ""
    goals: List[str] = field(default_factory=list)
    target_audience: str = ""
    success_metrics: List[str] = field(default_factory=list)


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
            repository_url=repository.get("url", ""),
            mission=product.get("mission", ""),
            vision=product.get("vision", ""),
            goals=product.get("goals", []),
            target_audience=product.get("target_audience", ""),
            success_metrics=product.get("success_metrics", []),
        )

    def get_project_context(self) -> str:
        """Build a stakeholder context brief from product metadata.

        Returns a formatted string with mission, vision, goals, target
        audience, and success metrics for use in PO prompts and agent
        context.  Returns empty string if no context fields are set.
        """
        meta = self.get_product_metadata()
        parts: List[str] = []

        parts.append(f"# {meta.name}\n")
        if meta.description:
            parts.append(f"{meta.description.strip()}\n")
        if meta.mission:
            parts.append(f"## Mission\n{meta.mission.strip()}\n")
        if meta.vision:
            parts.append(f"## Vision\n{meta.vision.strip()}\n")
        if meta.goals:
            parts.append("## Goals")
            for g in meta.goals:
                parts.append(f"- {g}")
            parts.append("")
        if meta.target_audience:
            parts.append(f"## Target Audience\n{meta.target_audience.strip()}\n")
        if meta.success_metrics:
            parts.append("## Success Metrics")
            for m in meta.success_metrics:
                parts.append(f"- {m}")
            parts.append("")

        # Only return if there is meaningful context beyond name/description
        if not (meta.mission or meta.vision or meta.goals):
            return ""
        return "\n".join(parts)
