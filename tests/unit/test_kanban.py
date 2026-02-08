"""Unit tests for the KanbanBoard."""

import pytest
import pytest_asyncio

from src.tools.kanban import KanbanBoard, WipLimitExceeded
from src.tools.shared_context import SharedContextDB


@pytest_asyncio.fixture
async def board():
    db = SharedContextDB("mock://")
    await db.initialize()
    return KanbanBoard(db, wip_limits={"in_progress": 4, "review": 2})


async def _seed_cards(board: KanbanBoard, status: str, count: int):
    """Helper to add multiple cards with a given status."""
    for i in range(count):
        await board.add_card(
            {"title": f"Card {status} {i}", "status": status, "story_points": 1}
        )


@pytest.mark.asyncio
async def test_pull_ready_task(board: KanbanBoard):
    """Adding a ready card and pulling it moves it to in_progress."""
    await board.add_card({"title": "Task A", "status": "ready", "story_points": 2})
    task = await board.pull_ready_task()
    assert task is not None
    assert task["status"] == "in_progress"
    assert task["title"] == "Task A"


@pytest.mark.asyncio
async def test_wip_limit_enforced(board: KanbanBoard):
    """When in_progress is at WIP limit, pull_ready_task returns None."""
    await _seed_cards(board, "in_progress", 4)
    await board.add_card({"title": "Ready Task", "status": "ready"})
    task = await board.pull_ready_task()
    assert task is None


@pytest.mark.asyncio
async def test_move_card_respects_wip_limit(board: KanbanBoard):
    """Moving a card to review when at limit raises WipLimitExceeded."""
    card_id = await board.add_card({"title": "Card", "status": "in_progress"})
    await _seed_cards(board, "review", 2)  # Fill review WIP limit
    with pytest.raises(WipLimitExceeded):
        await board.move_card(card_id, "review")


@pytest.mark.asyncio
async def test_get_snapshot(board: KanbanBoard):
    """Snapshot contains all expected columns."""
    await board.add_card({"title": "Backlog item", "status": "backlog"})
    await board.add_card({"title": "Ready item", "status": "ready"})
    snapshot = await board.get_snapshot()
    assert set(snapshot.keys()) == {"backlog", "ready", "in_progress", "review", "done"}
    assert len(snapshot["backlog"]) == 1
    assert len(snapshot["ready"]) == 1


@pytest.mark.asyncio
async def test_move_card_valid(board: KanbanBoard):
    """Moving a card to an empty column succeeds."""
    card_id = await board.add_card({"title": "Card", "status": "ready"})
    await board.move_card(card_id, "in_progress")
    cards = await board.db.get_cards_by_status("in_progress")
    assert any(c["id"] == card_id for c in cards)
