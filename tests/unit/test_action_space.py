"""Unit tests for Action Space Definition (F-13)."""

import pytest

from src.orchestrator.action_space import (
    ACTION_SPACE_SPEC,
    ActionExecutor,
    AdjustSprintParams,
    InjectDisturbance,
    ModifyBacklog,
    ModifyTeamComposition,
    SwapAgentRole,
)


class TestActionDataclasses:
    def test_inject_disturbance_defaults(self):
        a = InjectDisturbance(disturbance_type="flaky_test")
        assert a.disturbance_type == "flaky_test"
        assert a.severity == 0.5

    def test_swap_agent_role_fields(self):
        a = SwapAgentRole(agent_id="dev1", target_role_id="qa_tester", proficiency=0.6)
        assert a.agent_id == "dev1"
        assert a.target_role_id == "qa_tester"
        assert a.proficiency == 0.6

    def test_modify_backlog_add(self):
        a = ModifyBacklog(action="add", story={"id": "US-1", "title": "Test"})
        assert a.action == "add"
        assert a.story["id"] == "US-1"

    def test_modify_backlog_remove(self):
        a = ModifyBacklog(action="remove", story_id="US-1")
        assert a.action == "remove"
        assert a.story_id == "US-1"

    def test_modify_team_composition_depart(self):
        a = ModifyTeamComposition(action="depart", agent_id="dev1")
        assert a.action == "depart"

    def test_modify_team_composition_backfill(self):
        a = ModifyTeamComposition(
            action="backfill",
            backfill_config={"role_id": "new_dev", "name": "New Dev"},
        )
        assert a.action == "backfill"
        assert a.backfill_config["role_id"] == "new_dev"

    def test_adjust_sprint_params(self):
        a = AdjustSprintParams(duration_minutes=30, wip_limits={"in_progress": 6})
        assert a.duration_minutes == 30
        assert a.wip_limits == {"in_progress": 6}

    def test_adjust_sprint_params_defaults(self):
        a = AdjustSprintParams()
        assert a.duration_minutes is None
        assert a.wip_limits is None


class TestActionSpaceSpec:
    def test_five_action_types(self):
        assert len(ACTION_SPACE_SPEC) == 5

    def test_all_have_class_and_params(self):
        for name, spec in ACTION_SPACE_SPEC.items():
            assert "class" in spec, f"{name} missing 'class'"
            assert "params" in spec, f"{name} missing 'params'"

    def test_disturbance_types_listed(self):
        values = ACTION_SPACE_SPEC["inject_disturbance"]["params"]["disturbance_type"][
            "values"
        ]
        assert "flaky_test" in values
        assert "production_incident" in values
        assert len(values) >= 5


class _MockBacklog:
    """Minimal backlog for action executor tests."""

    def __init__(self):
        self.stories = []
        self._selected = set()

    def add_story(self, story):
        self.stories.append(story)

    def mark_returned(self, story_id):
        self._selected.discard(story_id)


class _MockAgent:
    """Minimal agent mock."""

    def __init__(self, agent_id):
        self._agent_id = agent_id
        self.swapped_to = None

    @property
    def agent_id(self):
        return self._agent_id

    def swap_to(self, target_role_id, domain, proficiency, sprint):
        self.swapped_to = target_role_id


class _MockDisturbanceEngine:
    """Minimal disturbance engine mock."""

    async def apply(self, disturbance_type, agents, kanban, db):
        return {"type": disturbance_type, "applied": True}


class _MockKanban:
    wip_limits = {"in_progress": 4, "review": 2}


class _MockConfig:
    sprint_duration_minutes = 60

    def __init__(self):
        pass

    @property
    def __dict__(self):
        return {"sprint_duration_minutes": self.sprint_duration_minutes}


class _MockSprintManager:
    """Minimal SprintManager for testing ActionExecutor."""

    def __init__(self):
        self.agents = [_MockAgent("dev1"), _MockAgent("dev2")]
        self.backlog = _MockBacklog()
        self.disturbance_engine = _MockDisturbanceEngine()
        self.kanban = _MockKanban()
        self.db = None
        self.config = _MockConfig()


class TestActionExecutor:
    @pytest.fixture
    def sm(self):
        return _MockSprintManager()

    @pytest.fixture
    def executor(self, sm):
        return ActionExecutor(sm)

    @pytest.mark.asyncio
    async def test_inject_disturbance(self, executor):
        result = await executor.execute(InjectDisturbance("flaky_test", 0.8))
        assert result["success"] is True
        assert result["disturbance_type"] == "flaky_test"

    @pytest.mark.asyncio
    async def test_inject_disturbance_no_engine(self, sm, executor):
        sm.disturbance_engine = None
        result = await executor.execute(InjectDisturbance("flaky_test"))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_swap_agent_role(self, sm, executor):
        result = await executor.execute(SwapAgentRole("dev1", "qa_tester", 0.6))
        assert result["success"] is True
        assert sm.agents[0].swapped_to == "qa_tester"

    @pytest.mark.asyncio
    async def test_swap_agent_not_found(self, executor):
        result = await executor.execute(SwapAgentRole("nonexistent", "qa_tester"))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_modify_backlog_add(self, sm, executor):
        result = await executor.execute(
            ModifyBacklog("add", story={"id": "US-99", "title": "New story"})
        )
        assert result["success"] is True
        assert len(sm.backlog.stories) == 1

    @pytest.mark.asyncio
    async def test_modify_backlog_remove(self, sm, executor):
        sm.backlog._selected.add("US-1")
        result = await executor.execute(ModifyBacklog("remove", story_id="US-1"))
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_modify_backlog_no_backlog(self, sm, executor):
        sm.backlog = None
        result = await executor.execute(ModifyBacklog("add", story={}))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_team_depart(self, sm, executor):
        result = await executor.execute(
            ModifyTeamComposition("depart", agent_id="dev1")
        )
        assert result["success"] is True
        assert len(sm.agents) == 1

    @pytest.mark.asyncio
    async def test_team_backfill(self, sm, executor):
        result = await executor.execute(
            ModifyTeamComposition(
                "backfill",
                backfill_config={"role_id": "new_dev", "name": "Newbie"},
            )
        )
        assert result["success"] is True
        assert len(sm.agents) == 3

    @pytest.mark.asyncio
    async def test_adjust_sprint_params(self, sm, executor):
        result = await executor.execute(
            AdjustSprintParams(duration_minutes=30, wip_limits={"in_progress": 8})
        )
        assert result["success"] is True
        assert sm.config.sprint_duration_minutes == 30
        assert sm.kanban.wip_limits["in_progress"] == 8

    @pytest.mark.asyncio
    async def test_batch_execution(self, executor):
        results = await executor.execute_batch(
            [
                InjectDisturbance("flaky_test"),
                AdjustSprintParams(duration_minutes=15),
            ]
        )
        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_unknown_action_type_raises(self, executor):
        with pytest.raises(TypeError, match="Unknown action type"):
            await executor.execute("not_an_action")  # type: ignore[arg-type]
