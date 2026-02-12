"""Action space definition for RL environment integration.

Defines the set of actions dojo can take between sprint phases to
influence the AAT environment.  Each action dispatches to existing
SprintManager / agent APIs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .sprint_manager import SprintManager


@dataclass
class InjectDisturbance:
    """Inject a disturbance event into the sprint."""

    disturbance_type: str  # flaky_test, production_incident, etc.
    severity: float = 0.5


@dataclass
class SwapAgentRole:
    """Swap an agent to a different role."""

    agent_id: str
    target_role_id: str
    proficiency: float = 0.7


@dataclass
class ModifyBacklog:
    """Add or remove a story from the backlog."""

    action: str  # "add" or "remove"
    story: Dict[str, Any] = field(default_factory=dict)
    story_id: str = ""


@dataclass
class ModifyTeamComposition:
    """Add or remove an agent from the team."""

    action: str  # "depart" or "backfill"
    agent_id: str = ""
    backfill_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdjustSprintParams:
    """Adjust sprint parameters (duration, WIP limits)."""

    duration_minutes: Optional[int] = None
    wip_limits: Optional[Dict[str, int]] = None


# Union type for all actions
Action = Union[
    InjectDisturbance,
    SwapAgentRole,
    ModifyBacklog,
    ModifyTeamComposition,
    AdjustSprintParams,
]


# Metadata for dojo's gym.Space construction
ACTION_SPACE_SPEC: Dict[str, Dict[str, Any]] = {
    "inject_disturbance": {
        "class": "InjectDisturbance",
        "params": {
            "disturbance_type": {
                "type": "categorical",
                "values": [
                    "flaky_test",
                    "production_incident",
                    "scope_creep",
                    "merge_conflict",
                    "test_failures",
                    "technical_debt",
                    "dependency_break",
                ],
            },
            "severity": {"type": "continuous", "low": 0.0, "high": 1.0},
        },
    },
    "swap_agent_role": {
        "class": "SwapAgentRole",
        "params": {
            "agent_id": {"type": "agent_ref"},
            "target_role_id": {"type": "role_ref"},
            "proficiency": {"type": "continuous", "low": 0.1, "high": 1.0},
        },
    },
    "modify_backlog": {
        "class": "ModifyBacklog",
        "params": {
            "action": {"type": "categorical", "values": ["add", "remove"]},
            "story": {"type": "dict"},
            "story_id": {"type": "string"},
        },
    },
    "modify_team_composition": {
        "class": "ModifyTeamComposition",
        "params": {
            "action": {"type": "categorical", "values": ["depart", "backfill"]},
            "agent_id": {"type": "agent_ref"},
            "backfill_config": {"type": "dict"},
        },
    },
    "adjust_sprint_params": {
        "class": "AdjustSprintParams",
        "params": {
            "duration_minutes": {"type": "discrete", "low": 1, "high": 120},
            "wip_limits": {"type": "dict"},
        },
    },
}


class ActionExecutor:
    """Executes RL actions against a SprintManager.

    Dispatches each action type to the appropriate SprintManager / agent API.

    Usage::

        executor = ActionExecutor(sprint_manager)
        result = await executor.execute(InjectDisturbance("flaky_test", 0.8))
    """

    def __init__(self, sprint_manager: "SprintManager") -> None:
        self._sm = sprint_manager

    async def execute(self, action: Action) -> Dict[str, Any]:
        """Execute a single action and return a result dict.

        Args:
            action: One of the action dataclasses.

        Returns:
            Dict with at least ``{"action": ..., "success": bool}``.

        Raises:
            TypeError: If action type is unrecognised.
        """
        if isinstance(action, InjectDisturbance):
            return await self._inject_disturbance(action)
        elif isinstance(action, SwapAgentRole):
            return await self._swap_agent_role(action)
        elif isinstance(action, ModifyBacklog):
            return await self._modify_backlog(action)
        elif isinstance(action, ModifyTeamComposition):
            return await self._modify_team_composition(action)
        elif isinstance(action, AdjustSprintParams):
            return await self._adjust_sprint_params(action)
        else:
            raise TypeError(f"Unknown action type: {type(action).__name__}")

    async def execute_batch(self, actions: List[Action]) -> List[Dict[str, Any]]:
        """Execute multiple actions sequentially.

        Args:
            actions: Ordered list of actions.

        Returns:
            List of result dicts, one per action.
        """
        results: List[Dict[str, Any]] = []
        for action in actions:
            result = await self.execute(action)
            results.append(result)
        return results

    # ── Handlers ─────────────────────────────────────────────────────

    async def _inject_disturbance(self, action: InjectDisturbance) -> Dict[str, Any]:
        """Dispatch to disturbance engine."""
        engine = self._sm.disturbance_engine
        if engine is None:
            return {
                "action": "inject_disturbance",
                "success": False,
                "reason": "disturbance engine not configured",
            }
        try:
            result = await engine.apply(
                action.disturbance_type,
                self._sm.agents,
                self._sm.kanban,
                self._sm.db,
            )
            return {
                "action": "inject_disturbance",
                "success": True,
                "disturbance_type": action.disturbance_type,
                "severity": action.severity,
                "details": result,
            }
        except Exception as exc:
            return {
                "action": "inject_disturbance",
                "success": False,
                "reason": str(exc),
            }

    async def _swap_agent_role(self, action: SwapAgentRole) -> Dict[str, Any]:
        """Dispatch to agent's swap_to method."""
        agent = self._find_agent(action.agent_id)
        if agent is None:
            return {
                "action": "swap_agent_role",
                "success": False,
                "reason": f"agent {action.agent_id!r} not found",
            }
        try:
            agent.swap_to(
                target_role_id=action.target_role_id,
                domain=action.target_role_id,
                proficiency=action.proficiency,
                sprint=0,
            )
            return {
                "action": "swap_agent_role",
                "success": True,
                "agent_id": action.agent_id,
                "target_role_id": action.target_role_id,
            }
        except Exception as exc:
            return {
                "action": "swap_agent_role",
                "success": False,
                "reason": str(exc),
            }

    async def _modify_backlog(self, action: ModifyBacklog) -> Dict[str, Any]:
        """Add or remove a story from the backlog."""
        backlog = self._sm.backlog
        if backlog is None:
            return {
                "action": "modify_backlog",
                "success": False,
                "reason": "no backlog configured",
            }
        if action.action == "add":
            backlog.add_story(action.story)
            return {
                "action": "modify_backlog",
                "success": True,
                "operation": "add",
                "story": action.story,
            }
        elif action.action == "remove":
            backlog.mark_returned(action.story_id)
            return {
                "action": "modify_backlog",
                "success": True,
                "operation": "remove",
                "story_id": action.story_id,
            }
        return {
            "action": "modify_backlog",
            "success": False,
            "reason": f"unknown operation: {action.action!r}",
        }

    async def _modify_team_composition(
        self, action: ModifyTeamComposition
    ) -> Dict[str, Any]:
        """Add or remove an agent from the team."""
        if action.action == "depart":
            agent = self._find_agent(action.agent_id)
            if agent is None:
                return {
                    "action": "modify_team_composition",
                    "success": False,
                    "reason": f"agent {action.agent_id!r} not found",
                }
            self._sm.agents = [
                a for a in self._sm.agents if a.agent_id != action.agent_id
            ]
            return {
                "action": "modify_team_composition",
                "success": True,
                "operation": "depart",
                "agent_id": action.agent_id,
            }
        elif action.action == "backfill":
            # Create a lightweight mock agent for the backfill
            from ..agents.base_agent import AgentConfig, BaseAgent

            cfg = action.backfill_config
            agent_config = AgentConfig(
                role_id=cfg.get("role_id", "backfill_agent"),
                name=cfg.get("name", "Backfill Agent"),
                model=cfg.get("model", "mock"),
                temperature=cfg.get("temperature", 0.7),
                max_tokens=cfg.get("max_tokens", 4096),
                individual=cfg.get("individual", ""),
                seniority=cfg.get("seniority", "mid"),
                primary_specialization=cfg.get("primary_specialization", "backend"),
            )
            new_agent = BaseAgent(agent_config, vllm_endpoint="mock://")
            self._sm.agents.append(new_agent)
            return {
                "action": "modify_team_composition",
                "success": True,
                "operation": "backfill",
                "agent_id": agent_config.role_id,
            }
        return {
            "action": "modify_team_composition",
            "success": False,
            "reason": f"unknown operation: {action.action!r}",
        }

    async def _adjust_sprint_params(self, action: AdjustSprintParams) -> Dict[str, Any]:
        """Adjust sprint duration and/or WIP limits."""
        changes: Dict[str, Any] = {}
        if action.duration_minutes is not None:
            self._sm.config.sprint_duration_minutes = action.duration_minutes
            changes["duration_minutes"] = action.duration_minutes
        if action.wip_limits is not None:
            self._sm.kanban.wip_limits.update(action.wip_limits)
            changes["wip_limits"] = action.wip_limits
        return {
            "action": "adjust_sprint_params",
            "success": True,
            "changes": changes,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    def _find_agent(self, agent_id: str) -> Optional[Any]:
        """Find an agent by ID."""
        for agent in self._sm.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
