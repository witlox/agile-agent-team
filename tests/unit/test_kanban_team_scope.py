"""Unit tests for team-scoped KanbanBoard."""

import asyncio

import pytest

from src.tools.kanban import KanbanBoard
from src.tools.shared_context import SharedContextDB


@pytest.fixture
def db():
    return SharedContextDB("mock://")


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def run(coro):
    """Run a coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Existing behavior preserved
# ---------------------------------------------------------------------------


def test_kanban_no_team_id_unchanged(db):
    """KanbanBoard without team_id behaves identically to before."""
    board = KanbanBoard(db)
    assert board.team_id == ""

    card_id = run(board.add_card({"title": "Task 1", "status": "ready", "sprint": 1}))
    assert card_id == 1

    snapshot = run(board.get_snapshot())
    assert len(snapshot["ready"]) == 1


# ---------------------------------------------------------------------------
# Team-scoped operations
# ---------------------------------------------------------------------------


def test_kanban_add_card_injects_team_id(db):
    """When team_id is set, add_card injects team_id into card_data."""
    board = KanbanBoard(db, team_id="team-a")
    run(board.add_card({"title": "Task A", "status": "ready", "sprint": 1}))

    # Card should have team_id stored
    all_cards = run(db.get_cards_by_status("ready"))
    assert len(all_cards) == 1
    assert all_cards[0]["team_id"] == "team-a"


def test_kanban_pull_ready_task_team_scoped(db):
    """pull_ready_task only pulls cards belonging to the team."""
    # Add cards for two teams directly via db
    run(
        db.add_card(
            {"title": "A1", "status": "ready", "sprint": 1, "team_id": "team-a"}
        )
    )
    run(
        db.add_card(
            {"title": "B1", "status": "ready", "sprint": 1, "team_id": "team-b"}
        )
    )

    board_a = KanbanBoard(db, team_id="team-a")
    card = run(board_a.pull_ready_task())
    assert card is not None
    assert card["title"] == "A1"

    # team-b card should still be ready
    board_b = KanbanBoard(db, team_id="team-b")
    card_b = run(board_b.pull_ready_task())
    assert card_b is not None
    assert card_b["title"] == "B1"


def test_kanban_snapshot_team_scoped(db):
    """get_snapshot only returns cards for the board's team."""
    run(
        db.add_card(
            {"title": "A1", "status": "ready", "sprint": 1, "team_id": "team-a"}
        )
    )
    run(
        db.add_card(
            {"title": "B1", "status": "ready", "sprint": 1, "team_id": "team-b"}
        )
    )
    run(
        db.add_card({"title": "B2", "status": "done", "sprint": 1, "team_id": "team-b"})
    )

    board_a = KanbanBoard(db, team_id="team-a")
    snap_a = run(board_a.get_snapshot())
    assert len(snap_a["ready"]) == 1
    assert snap_a["ready"][0]["title"] == "A1"
    assert len(snap_a["done"]) == 0

    board_b = KanbanBoard(db, team_id="team-b")
    snap_b = run(board_b.get_snapshot())
    assert len(snap_b["ready"]) == 1
    assert len(snap_b["done"]) == 1


def test_kanban_wip_limit_team_scoped(db):
    """WIP limits are enforced per-team, not globally."""
    board_a = KanbanBoard(
        db, wip_limits={"in_progress": 1, "review": 1}, team_id="team-a"
    )
    board_b = KanbanBoard(
        db, wip_limits={"in_progress": 1, "review": 1}, team_id="team-b"
    )

    # Add one in_progress card per team
    run(
        db.add_card(
            {
                "title": "A-WIP",
                "status": "in_progress",
                "sprint": 1,
                "team_id": "team-a",
            }
        )
    )
    run(
        db.add_card(
            {
                "title": "B-WIP",
                "status": "in_progress",
                "sprint": 1,
                "team_id": "team-b",
            }
        )
    )

    # Add a ready card for team-a
    run(
        db.add_card(
            {"title": "A-Ready", "status": "ready", "sprint": 1, "team_id": "team-a"}
        )
    )

    # Team A should NOT be able to pull (WIP=1 already reached)
    card = run(board_a.pull_ready_task())
    assert card is None

    # Team B should also not pull since it has no ready cards
    run(
        db.add_card(
            {"title": "B-Ready", "status": "ready", "sprint": 1, "team_id": "team-b"}
        )
    )
    card_b = run(board_b.pull_ready_task())
    assert card_b is None  # WIP limit reached for team-b too


def test_kanban_get_cards_by_status_team_scoped(db):
    """get_cards_by_status returns only team's cards."""
    run(
        db.add_card({"title": "A1", "status": "done", "sprint": 1, "team_id": "team-a"})
    )
    run(
        db.add_card({"title": "B1", "status": "done", "sprint": 1, "team_id": "team-b"})
    )
    run(
        db.add_card({"title": "A2", "status": "done", "sprint": 1, "team_id": "team-a"})
    )

    board_a = KanbanBoard(db, team_id="team-a")
    done_a = run(board_a.get_cards_by_status("done"))
    assert len(done_a) == 2

    board_b = KanbanBoard(db, team_id="team-b")
    done_b = run(board_b.get_cards_by_status("done"))
    assert len(done_b) == 1
