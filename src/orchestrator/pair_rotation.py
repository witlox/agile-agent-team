"""Pair rotation algorithm ensuring all engineers pair with each other."""

from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class PairRotationManager:
    """Manages round-robin pair rotation to ensure everyone pairs with everyone."""

    # Track pairing history
    pairing_history: Dict[Tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int)
    )

    # Current sprint's rotations
    daily_pairs: Dict[int, List[Tuple[str, str]]] = field(default_factory=dict)

    def get_rotation_for_day(
        self,
        day_num: int,
        task_owners: List[str],
        available_partners: List[str],
        sprint_num: int,
    ) -> Dict[str, str]:
        """Generate pair assignments for a given day.

        Args:
            day_num: Day number in sprint (1-10)
            task_owners: List of agent IDs who own tasks (continuity)
            available_partners: List of agent IDs available for pairing (navigators)
            sprint_num: Current sprint number

        Returns:
            Dictionary mapping task_owner -> navigator
        """
        # Ensure we have enough partners
        if len(available_partners) < len(task_owners):
            raise ValueError(
                f"Not enough partners ({len(available_partners)}) "
                f"for task owners ({len(task_owners)})"
            )

        # Use round-robin with history to ensure variety
        pairs = self._round_robin_with_history(
            task_owners, available_partners, day_num, sprint_num
        )

        # Record this day's pairs
        self.daily_pairs[day_num] = pairs

        # Update pairing history
        for owner, navigator in pairs:
            pair_key = self._normalize_pair(owner, navigator)
            self.pairing_history[pair_key] += 1

        # Return as dictionary for easy lookup
        return {owner: navigator for owner, navigator in pairs}

    def _round_robin_with_history(
        self, owners: List[str], partners: List[str], day_num: int, sprint_num: int
    ) -> List[Tuple[str, str]]:
        """Round-robin algorithm that prefers least-paired combinations.

        Strategy:
        1. For each owner, find partners they've paired with least
        2. Prefer partners from different specializations (diversity)
        3. Ensure no one is assigned twice in same day
        """
        pairs = []
        assigned_navigators = set()

        # Create working list of partners (remove owners who are also partners)
        available = [p for p in partners if p not in owners]

        # Handle edge case: if we removed too many, use all partners
        if len(available) < len(owners):
            available = partners.copy()

        for owner in owners:
            # Find best navigator for this owner
            navigator = self._find_best_navigator(owner, available, assigned_navigators)

            if navigator:
                pairs.append((owner, navigator))
                assigned_navigators.add(navigator)

        return pairs

    def _find_best_navigator(
        self, owner: str, candidates: List[str], already_assigned: Set[str]
    ) -> str:
        """Find best navigator for owner based on pairing history.

        Prefer:
        1. Not already assigned today
        2. Least paired with owner historically
        3. Different from owner (if owner is also in candidates)
        """
        # Filter out already assigned and owner themselves
        available = [c for c in candidates if c not in already_assigned and c != owner]

        if not available:
            # Fallback: allow reassignment if necessary
            available = [c for c in candidates if c != owner]

        if not available:
            # Last resort: pair with themselves (shouldn't happen)
            return owner

        # Score each candidate by pairing history (lower = better)
        scored = []
        for candidate in available:
            pair_key = self._normalize_pair(owner, candidate)
            pair_count = self.pairing_history.get(pair_key, 0)
            scored.append((pair_count, candidate))

        # Sort by score (ascending) and pick best
        scored.sort(key=lambda x: x[0])
        return scored[0][1]

    def _normalize_pair(self, agent1: str, agent2: str) -> Tuple[str, str]:
        """Normalize pair to canonical form (alphabetical order)."""
        return tuple(sorted([agent1, agent2]))

    def get_pairing_statistics(self) -> Dict:
        """Get statistics about pairing coverage.

        Returns:
            Dictionary with pairing statistics:
            - total_unique_pairs: Number of unique pairs formed
            - most_frequent_pair: Pair that paired most often
            - least_frequent_pair: Pair that paired least often
            - average_pairings_per_pair: Average times each pair worked together
        """
        if not self.pairing_history:
            return {
                "total_unique_pairs": 0,
                "most_frequent_pair": None,
                "least_frequent_pair": None,
                "average_pairings_per_pair": 0.0,
            }

        pairs_list = [(pair, count) for pair, count in self.pairing_history.items()]
        pairs_list.sort(key=lambda x: x[1], reverse=True)

        total = len(pairs_list)
        total_pairings = sum(count for _, count in pairs_list)

        return {
            "total_unique_pairs": total,
            "most_frequent_pair": {
                "agents": pairs_list[0][0],
                "count": pairs_list[0][1],
            },
            "least_frequent_pair": {
                "agents": pairs_list[-1][0],
                "count": pairs_list[-1][1],
            },
            "average_pairings_per_pair": total_pairings / total if total > 0 else 0.0,
        }

    def get_agent_pairing_coverage(self, agent_id: str) -> Dict:
        """Get statistics about who an agent has paired with.

        Args:
            agent_id: Agent ID to analyze

        Returns:
            Dictionary with:
            - paired_with: List of agents paired with and count
            - total_pairings: Total number of pairing sessions
        """
        paired_with = defaultdict(int)

        for (a1, a2), count in self.pairing_history.items():
            if a1 == agent_id:
                paired_with[a2] += count
            elif a2 == agent_id:
                paired_with[a1] += count

        return {
            "paired_with": dict(paired_with),
            "total_pairings": sum(paired_with.values()),
        }


def create_initial_pairs(
    tasks: List[Dict], developers: List, testers: List
) -> List[Tuple[str, str]]:
    """Create initial Day 1 pairs based on task requirements.

    Args:
        tasks: List of task dictionaries with 'owner' field
        developers: List of developer agents
        testers: List of tester agents (including QA lead)

    Returns:
        List of (owner_id, navigator_id) tuples
    """
    all_team = developers + testers
    pairs = []
    assigned = set()

    for task in tasks:
        owner_id = task.get("owner")
        if not owner_id:
            continue

        # Find a navigator (prefer someone not yet assigned)
        for agent in all_team:
            if agent.agent_id != owner_id and agent.agent_id not in assigned:
                pairs.append((owner_id, agent.agent_id))
                assigned.add(agent.agent_id)
                assigned.add(owner_id)  # Mark owner as paired
                break

    return pairs


def ensure_pairing_diversity(
    rotation_manager: PairRotationManager,
    num_days: int,
    owners: List[str],
    partners: List[str],
    sprint_num: int,
) -> Dict[int, Dict[str, str]]:
    """Generate rotation schedule for entire sprint ensuring diversity.

    Args:
        rotation_manager: PairRotationManager instance
        num_days: Number of days in sprint (typically 10)
        owners: List of task owners (provide continuity)
        partners: List of all team members available for pairing
        sprint_num: Current sprint number

    Returns:
        Dictionary mapping day_num -> {owner: navigator}
    """
    schedule = {}

    for day in range(1, num_days + 1):
        pairs = rotation_manager.get_rotation_for_day(day, owners, partners, sprint_num)
        schedule[day] = pairs

    return schedule
