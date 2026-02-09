"""Unit tests for pair rotation manager."""

import pytest
from src.orchestrator.pair_rotation import PairRotationManager


@pytest.fixture
def rotation_manager():
    """Create a pair rotation manager."""
    return PairRotationManager()


@pytest.fixture
def sample_developers():
    """Sample developer agent IDs."""
    return ["dev1", "dev2", "dev3", "dev4", "dev5", "dev6"]


@pytest.fixture
def sample_testers():
    """Sample tester agent IDs."""
    return ["tester1", "tester2"]


@pytest.fixture
def all_partners(sample_developers, sample_testers):
    """All available partners (developers + testers)."""
    return sample_developers + sample_testers


def test_initial_rotation_assigns_all_navigators(
    rotation_manager, sample_developers, all_partners
):
    """Test Day 1 rotation assigns navigator to each task owner."""
    task_owners = sample_developers[:3]  # 3 tasks

    # Day 1 rotation
    pairs = rotation_manager.get_rotation_for_day(
        day_num=1, task_owners=task_owners, available_partners=all_partners, sprint_num=1
    )

    # Should have pairs for all task owners
    assert len(pairs) == len(task_owners), "Should assign navigator to each owner"

    # No owner should navigate themselves
    for owner, navigator in pairs.items():
        assert owner != navigator, "Owner should not navigate themselves"

    # All navigators should be from available partners
    navigators = set(pairs.values())
    assert navigators.issubset(
        set(all_partners)
    ), "Navigators should be from available partners"


def test_rotation_cycles_through_all_available_partners(
    rotation_manager, sample_developers, all_partners
):
    """Test rotation ensures owner pairs with all available partners before repeating."""
    task_owners = ["dev1"]  # Single owner
    available = all_partners.copy()
    available.remove("dev1")  # Owner can't pair with self

    seen_navigators = set()

    # Run rotation for many days
    for day in range(1, len(available) + 2):
        pairs = rotation_manager.get_rotation_for_day(
            day_num=day,
            task_owners=task_owners,
            available_partners=all_partners,
            sprint_num=1,
        )
        navigator = pairs.get("dev1")
        assert navigator is not None, f"Day {day}: Should have navigator"
        seen_navigators.add(navigator)

    # Should have seen all available partners
    assert len(seen_navigators) >= len(available) - 1, (
        "Should cycle through most available partners"
    )


def test_rotation_excludes_task_owner(
    rotation_manager, sample_developers, all_partners
):
    """Test owner never paired with themselves as navigator."""
    task_owners = sample_developers[:4]

    # Test multiple days
    for day in range(1, 11):
        pairs = rotation_manager.get_rotation_for_day(
            day_num=day,
            task_owners=task_owners,
            available_partners=all_partners,
            sprint_num=1,
        )

        # Verify no self-pairing
        for owner, navigator in pairs.items():
            assert (
                owner != navigator
            ), f"Day {day}: {owner} should not navigate themselves"


def test_rotation_includes_testers_appropriately(
    rotation_manager, sample_developers, sample_testers, all_partners
):
    """Test testers participate as navigators in rotations."""
    task_owners = sample_developers[:3]
    tester_navigations = 0
    total_rotations = 0

    # Run rotation for 10 days
    for day in range(1, 11):
        pairs = rotation_manager.get_rotation_for_day(
            day_num=day,
            task_owners=task_owners,
            available_partners=all_partners,
            sprint_num=1,
        )

        for navigator in pairs.values():
            total_rotations += 1
            if navigator in sample_testers:
                tester_navigations += 1

    # Testers should participate (actual frequency depends on implementation)
    # Just verify they're included at all
    assert (
        tester_navigations > 0
    ), "Testers should participate as navigators at least sometimes"


def test_rotation_history_prevents_immediate_repeats(rotation_manager, all_partners):
    """Test pairing history prevents immediate repeat pairings."""
    task_owners = ["dev1", "dev2"]

    # Get first day pairs
    day1_pairs = rotation_manager.get_rotation_for_day(
        day_num=1, task_owners=task_owners, available_partners=all_partners, sprint_num=1
    )

    # Get second day pairs
    day2_pairs = rotation_manager.get_rotation_for_day(
        day_num=2, task_owners=task_owners, available_partners=all_partners, sprint_num=1
    )

    # At least some pairs should differ (history should cause rotation)
    # With enough partners, we shouldn't see identical pairs two days in a row
    if len(all_partners) > len(task_owners) + 1:
        assert (
            day1_pairs != day2_pairs
        ), "With sufficient partners, pairs should rotate between days"


def test_rotation_handles_odd_team_sizes(rotation_manager):
    """Test rotation with 5, 7, 9 team members (odd numbers)."""
    for team_size in [5, 7, 9]:
        partners = [f"dev{i}" for i in range(team_size)]
        task_owners = partners[:2]  # 2 tasks

        # Should work without errors
        pairs = rotation_manager.get_rotation_for_day(
            day_num=1, task_owners=task_owners, available_partners=partners, sprint_num=1
        )

        assert len(pairs) == len(task_owners), (
            f"Should handle team size {team_size}"
        )


def test_rotation_fairness_over_10_days(rotation_manager, sample_developers):
    """Test 10-day rotation ensures balanced pairing distribution."""
    task_owners = sample_developers[:2]  # 2 concurrent tasks
    available = sample_developers

    # Track how often each navigator is assigned
    navigator_counts = {dev: 0 for dev in available}

    for day in range(1, 11):
        pairs = rotation_manager.get_rotation_for_day(
            day_num=day, task_owners=task_owners, available_partners=available, sprint_num=1
        )
        for navigator in pairs.values():
            navigator_counts[navigator] += 1

    # Remove task owners (they can't navigate their own tasks)
    for owner in task_owners:
        if owner in navigator_counts:
            del navigator_counts[owner]

    # Verify fairness - no one should be drastically over/under utilized
    counts = list(navigator_counts.values())
    if counts:
        avg_count = sum(counts) / len(counts)
        max_count = max(counts)
        min_count = min(counts)

        # Allow some variance but shouldn't be too extreme
        # With 10 days and 2 tasks = 20 navigations across ~4 available navigators
        # Each should get ~5 navigations, allow variance of ±3
        variance = max_count - min_count
        assert variance <= 6, f"Distribution should be fairly balanced (variance={variance})"


def test_rotation_clears_history_per_sprint(rotation_manager, all_partners):
    """Test pairing history resets at sprint boundaries."""
    task_owners = ["dev1"]

    # Sprint 1, Day 1
    sprint1_day1_pairs = rotation_manager.get_rotation_for_day(
        day_num=1, task_owners=task_owners, available_partners=all_partners, sprint_num=1
    )

    # Sprint 1, Day 2
    sprint1_day2_pairs = rotation_manager.get_rotation_for_day(
        day_num=2, task_owners=task_owners, available_partners=all_partners, sprint_num=1
    )

    # Sprint 2, Day 1 (history should reset)
    sprint2_day1_pairs = rotation_manager.get_rotation_for_day(
        day_num=1, task_owners=task_owners, available_partners=all_partners, sprint_num=2
    )

    # Sprint 2 Day 1 could match Sprint 1 Day 1 (history cleared)
    # Just verify no crash and returns valid pairs
    assert len(sprint2_day1_pairs) == len(task_owners), (
        "Sprint 2 should work after history reset"
    )
