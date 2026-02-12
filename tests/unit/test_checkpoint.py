"""Unit tests for State Checkpointing (F-14)."""

import json

import pytest

from src.orchestrator.checkpoint import Checkpoint, CheckpointManager


# ── Minimal mocks ────────────────────────────────────────────────────


class _MockDecision:
    def __init__(self, decision_id, phase="dev"):
        self.decision_id = decision_id
        self.timestamp = "2026-01-01T00:00:00Z"
        self.phase = phase
        self.context = "ctx"
        self.action_type = "generate"
        self.action_content = "content"
        self.reasoning_trace = "trace"
        self.outcome = None
        self.metadata = {}


class _MockTracer:
    def __init__(self, decisions=None):
        self._decisions = list(decisions or [])

    @property
    def decisions(self):
        return list(self._decisions)

    def record(self, decision):
        self._decisions.append(decision)


class _MockAgent:
    def __init__(self, agent_id, conversation_history=None, tracer=None):
        self._agent_id = agent_id
        self.config = type(
            "C",
            (),
            {
                "role_id": agent_id,
                "name": agent_id,
                "seniority": "mid",
            },
        )()
        self.conversation_history = list(conversation_history or [])
        self.is_swapped = False
        self._swap_state = None
        self._tracer = tracer

    @property
    def agent_id(self):
        return self._agent_id


class _MockDB:
    def __init__(self):
        self._cards = []
        self._meta_learnings = [{"agent_id": "dev1", "learning": "test"}]


class _MockKanban:
    async def get_snapshot(self):
        return {"backlog": [], "ready": [], "in_progress": [], "review": [], "done": []}


class _MockBacklog:
    def __init__(self):
        self.remaining = 5
        self._selected_ids = {"US-1", "US-2"}


class _MockConfig:
    sprint_duration_minutes = 60
    name = "test"

    @property
    def __dict__(self):
        return {"sprint_duration_minutes": 60, "name": "test"}


class _MockSprintManager:
    def __init__(self, agents=None, tracer_decisions=None):
        self.agents = agents or [_MockAgent("dev1"), _MockAgent("dev2")]
        self.kanban = _MockKanban()
        self.db = _MockDB()
        self.backlog = _MockBacklog()
        self.config = _MockConfig()
        self._sprint_results = [{"sprint": 1, "velocity": 10}]


class TestCheckpointDataclass:
    def test_default_fields(self):
        cp = Checkpoint(
            episode_id="ep1", sprint_num=1, phase="dev", timestamp="2026-01-01"
        )
        assert cp.episode_id == "ep1"
        assert cp.kanban_snapshot == {}
        assert cp.agent_states == []
        assert cp.config_hash == ""


class TestCheckpointManager:
    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return tmp_path / "checkpoints"

    @pytest.fixture
    def mgr(self, tmp_dir):
        return CheckpointManager(tmp_dir)

    @pytest.fixture
    def sm(self):
        return _MockSprintManager()

    @pytest.mark.asyncio
    async def test_save_creates_file(self, mgr, sm, tmp_dir):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="development")
        assert path.exists()
        assert path.name == "s01-development.json"

    @pytest.mark.asyncio
    async def test_save_is_valid_json(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="planning")
        data = json.loads(path.read_text())
        assert data["episode_id"] == "ep-001"
        assert data["sprint_num"] == 1
        assert data["phase"] == "planning"

    @pytest.mark.asyncio
    async def test_save_captures_agent_states(self, mgr, sm):
        sm.agents[0].conversation_history = ["msg1", "msg2"]
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert len(data["agent_states"]) == 2
        assert data["agent_states"][0]["conversation_history"] == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_save_captures_sprint_results(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert data["sprint_results"] == [{"sprint": 1, "velocity": 10}]

    @pytest.mark.asyncio
    async def test_save_captures_backlog_state(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert data["backlog_state"]["remaining"] == 5
        assert set(data["backlog_state"]["selected"]) == {"US-1", "US-2"}

    @pytest.mark.asyncio
    async def test_save_captures_meta_learnings(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert len(data["meta_learnings"]) == 1

    @pytest.mark.asyncio
    async def test_save_captures_tracer_states(self, mgr, sm):
        tracer = _MockTracer([_MockDecision("d-001")])
        sm.agents[0]._tracer = tracer
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert "dev1" in data["tracer_states"]
        assert data["tracer_states"]["dev1"][0]["decision_id"] == "d-001"

    @pytest.mark.asyncio
    async def test_restore_kanban(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        # Clear cards
        sm.db._cards.clear()
        # Restore
        checkpoint = await mgr.restore(path, sm)
        assert checkpoint.episode_id == "ep-001"

    @pytest.mark.asyncio
    async def test_restore_agent_history(self, mgr, sm):
        sm.agents[0].conversation_history = ["hello"]
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        # Clear
        sm.agents[0].conversation_history = []
        # Restore
        await mgr.restore(path, sm)
        assert sm.agents[0].conversation_history == ["hello"]

    @pytest.mark.asyncio
    async def test_restore_sprint_results(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        sm._sprint_results = []
        await mgr.restore(path, sm)
        assert len(sm._sprint_results) == 1

    @pytest.mark.asyncio
    async def test_round_trip_equivalence(self, mgr, sm):
        sm.agents[0].conversation_history = ["msg1"]
        path = await mgr.save("ep-001", sm, sprint_num=2, phase="qa_review")
        # Reset
        sm.agents[0].conversation_history = []
        sm._sprint_results = []
        sm.db._meta_learnings = []
        sm.backlog._selected_ids = set()
        # Restore
        cp = await mgr.restore(path, sm)
        assert cp.sprint_num == 2
        assert cp.phase == "qa_review"
        assert sm.agents[0].conversation_history == ["msg1"]
        assert len(sm._sprint_results) == 1
        assert len(sm.db._meta_learnings) == 1
        assert sm.backlog._selected_ids == {"US-1", "US-2"}

    @pytest.mark.asyncio
    async def test_list_checkpoints_sorted(self, mgr, sm):
        await mgr.save("ep-001", sm, sprint_num=1, phase="planning")
        await mgr.save("ep-001", sm, sprint_num=1, phase="development")
        await mgr.save("ep-001", sm, sprint_num=2, phase="planning")
        paths = mgr.list_checkpoints("ep-001")
        assert len(paths) == 3
        names = [p.name for p in paths]
        assert names == sorted(names)

    def test_list_checkpoints_empty(self, mgr):
        assert mgr.list_checkpoints("nonexistent") == []

    @pytest.mark.asyncio
    async def test_config_hash_present(self, mgr, sm):
        path = await mgr.save("ep-001", sm, sprint_num=1, phase="dev")
        data = json.loads(path.read_text())
        assert len(data["config_hash"]) == 16
