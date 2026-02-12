"""Scenario catalog for RL training episodes.

Defines episode types and generates scenario configurations for
curriculum-based training in dojo's environment.
"""

import random as _random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ScenarioConfig:
    """Configuration for a single training scenario/episode."""

    episode_type: str
    stage: int
    difficulty: float
    target_agent_slot: str
    backlog_stories: List[Dict[str, Any]] = field(default_factory=list)
    disturbance_overrides: Dict[str, Any] = field(default_factory=dict)
    agent_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    expected_behaviors: List[str] = field(default_factory=list)
    duration_minutes: int = 10
    phases: List[str] = field(default_factory=list)


# 13 episode types from dojo's TRAINING_EPISODES spec
EPISODE_TYPES: Dict[str, Dict[str, Any]] = {
    # Stage 1: Foundation
    "elicitation": {
        "stage": 1,
        "phases": ["planning"],
        "target_behaviors": ["B-01", "B-02", "B-03"],
        "duration_minutes": 5,
        "description": "Story elicitation and requirements clarification",
    },
    "decomposition": {
        "stage": 1,
        "phases": ["planning"],
        "target_behaviors": ["B-04", "B-05", "B-06"],
        "duration_minutes": 5,
        "description": "Task decomposition and estimation",
    },
    "implementation": {
        "stage": 1,
        "phases": ["development"],
        "target_behaviors": ["B-07", "B-08", "B-09"],
        "duration_minutes": 10,
        "description": "Code implementation with pairing",
    },
    "self_monitoring": {
        "stage": 1,
        "phases": ["development", "qa_review"],
        "target_behaviors": ["B-10", "B-11"],
        "duration_minutes": 8,
        "description": "Self-monitoring and quality checks",
    },
    # Stage 2: Advanced
    "research": {
        "stage": 2,
        "phases": ["planning", "development"],
        "target_behaviors": ["B-12", "B-13", "B-14"],
        "duration_minutes": 10,
        "description": "Technical research and spike work",
    },
    "triage": {
        "stage": 2,
        "phases": ["planning", "development"],
        "target_behaviors": ["B-15", "B-16"],
        "duration_minutes": 8,
        "description": "Bug triage and prioritization under pressure",
    },
    "recovery": {
        "stage": 2,
        "phases": ["development", "qa_review"],
        "target_behaviors": ["B-17", "B-18", "B-19"],
        "duration_minutes": 10,
        "description": "Recovery from disturbances (flaky tests, incidents)",
    },
    "scope_change": {
        "stage": 2,
        "phases": ["planning", "development"],
        "target_behaviors": ["B-20", "B-21"],
        "duration_minutes": 8,
        "description": "Handling mid-sprint scope changes",
    },
    # Stage 3: Expert
    "borrowing_arrival": {
        "stage": 3,
        "phases": ["planning", "development", "retro"],
        "target_behaviors": ["B-22", "B-23"],
        "duration_minutes": 10,
        "description": "Cross-team agent borrowing and adaptation",
    },
    "cross_team_dependency": {
        "stage": 3,
        "phases": ["planning", "development"],
        "target_behaviors": ["B-24", "B-25"],
        "duration_minutes": 10,
        "description": "Cross-team dependency resolution",
    },
    "knowledge_handoff": {
        "stage": 3,
        "phases": ["development", "retro", "meta_learning"],
        "target_behaviors": ["B-26", "B-27"],
        "duration_minutes": 8,
        "description": "Knowledge transfer during agent departure",
    },
    # Stage 4: Transfer
    "onboarding_support": {
        "stage": 4,
        "phases": ["planning", "development", "retro"],
        "target_behaviors": ["B-28", "B-29"],
        "duration_minutes": 10,
        "description": "Supporting new team member onboarding",
    },
    "compensation": {
        "stage": 4,
        "phases": ["planning", "development", "qa_review", "retro"],
        "target_behaviors": ["B-30"],
        "duration_minutes": 10,
        "description": "Compensating for team gaps after departure",
    },
}


class ScenarioCatalog:
    """Generates scenario configurations for RL training episodes.

    Usage::

        catalog = ScenarioCatalog()
        scenario = catalog.generate("implementation", difficulty=0.5,
                                     target_slot="dev_mid_backend")
    """

    def __init__(self, backlog_path: Optional[str] = None) -> None:
        self._story_pool: List[Dict[str, Any]] = []
        if backlog_path:
            self._story_pool = self._load_story_pool(backlog_path)

    def list_episode_types(self, stage: Optional[int] = None) -> List[str]:
        """List available episode types, optionally filtered by stage.

        Args:
            stage: If provided, return only types for that stage (1-4).

        Returns:
            Sorted list of episode type names.
        """
        if stage is not None:
            return sorted(
                name for name, info in EPISODE_TYPES.items() if info["stage"] == stage
            )
        return sorted(EPISODE_TYPES.keys())

    def generate(
        self,
        episode_type: str,
        difficulty: float = 0.5,
        target_slot: str = "dev_mid_backend",
        seed: Optional[int] = None,
    ) -> ScenarioConfig:
        """Generate a scenario configuration for an episode type.

        Args:
            episode_type: One of EPISODE_TYPES keys.
            difficulty: 0.0 (easy) to 1.0 (hard).
            target_slot: role_id where training candidate is placed.
            seed: Optional RNG seed for deterministic output.

        Returns:
            ScenarioConfig ready for use with ConfigBuilder/PhaseRunner.

        Raises:
            ValueError: If episode_type is unknown.
        """
        if episode_type not in EPISODE_TYPES:
            raise ValueError(
                f"Unknown episode type: {episode_type!r}. "
                f"Available: {sorted(EPISODE_TYPES.keys())}"
            )

        rng = _random.Random(seed)
        ep = EPISODE_TYPES[episode_type]

        stories = self._generate_stories_for_type(episode_type, difficulty, rng)
        disturbances = self._generate_disturbances_for_type(
            episode_type, difficulty, rng
        )

        agent_overrides: Dict[str, Dict[str, Any]] = {
            target_slot: {"is_training_candidate": True}
        }

        return ScenarioConfig(
            episode_type=episode_type,
            stage=ep["stage"],
            difficulty=difficulty,
            target_agent_slot=target_slot,
            backlog_stories=stories,
            disturbance_overrides=disturbances,
            agent_overrides=agent_overrides,
            expected_behaviors=list(ep["target_behaviors"]),
            duration_minutes=ep["duration_minutes"],
            phases=list(ep["phases"]),
        )

    def generate_curriculum(
        self,
        stage: int,
        num_episodes: int = 100,
        seed: Optional[int] = None,
    ) -> List[ScenarioConfig]:
        """Generate a batch of episodes for a curriculum stage.

        Args:
            stage: Training stage (1-4).
            num_episodes: Number of episodes to generate.
            seed: Optional RNG seed for deterministic output.

        Returns:
            List of ScenarioConfig for the given stage.
        """
        rng = _random.Random(seed)
        types = self.list_episode_types(stage)
        if not types:
            return []

        scenarios: List[ScenarioConfig] = []
        for i in range(num_episodes):
            ep_type = types[i % len(types)]
            difficulty = rng.uniform(0.2, 0.9)
            scenario = self.generate(
                ep_type,
                difficulty=difficulty,
                seed=rng.randint(0, 2**31),
            )
            scenarios.append(scenario)
        return scenarios

    def _load_story_pool(self, path: str) -> List[Dict[str, Any]]:
        """Load stories from a backlog YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            return list(data.get("stories", []))
        except Exception:
            return []

    def _generate_stories_for_type(
        self,
        episode_type: str,
        difficulty: float,
        rng: _random.Random,
    ) -> List[Dict[str, Any]]:
        """Generate stories appropriate for an episode type.

        If a story pool is loaded, sample from it. Otherwise generate
        synthetic stories.
        """
        num_stories = max(1, int(1 + difficulty * 3))

        if self._story_pool:
            pool = list(self._story_pool)
            rng.shuffle(pool)
            return pool[:num_stories]

        # Synthetic stories
        stories: List[Dict[str, Any]] = []
        for i in range(num_stories):
            complexity = "simple" if difficulty < 0.4 else "moderate"
            if difficulty > 0.7:
                complexity = "complex"
            stories.append(
                {
                    "id": f"EP-{episode_type[:4].upper()}-{i + 1:03d}",
                    "title": f"{episode_type.replace('_', ' ').title()} task {i + 1}",
                    "description": (
                        f"Synthetic {complexity} story for {episode_type} training"
                    ),
                    "story_points": int(2 + difficulty * 6),
                    "acceptance_criteria": [
                        f"Criterion {j + 1}" for j in range(1 + int(difficulty * 3))
                    ],
                }
            )
        return stories

    def _generate_disturbances_for_type(
        self,
        episode_type: str,
        difficulty: float,
        rng: _random.Random,
    ) -> Dict[str, Any]:
        """Generate disturbance settings appropriate for an episode type."""
        # No disturbances at low difficulty or for planning-only episodes
        if difficulty < 0.3:
            return {"enabled": False}

        # Map episode types to relevant disturbance types
        type_disturbances: Dict[str, List[str]] = {
            "recovery": ["flaky_test", "production_incident", "build_failure"],
            "triage": ["production_incident", "scope_creep"],
            "scope_change": ["scope_creep", "requirement_change"],
            "compensation": ["agent_departure"],
        }

        relevant = type_disturbances.get(episode_type, [])
        if not relevant and difficulty > 0.5:
            relevant = ["flaky_test"]

        frequencies: Dict[str, float] = {}
        for dist_type in relevant:
            frequencies[dist_type] = rng.uniform(0.2, difficulty)

        return {
            "enabled": bool(frequencies),
            "frequencies": frequencies,
        }
