"""Cross-team coordination loop — evaluates health, dependencies, borrows."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent
    from ..agents.messaging import MessageBus
    from ..metrics.sprint_metrics import SprintResult
    from ..tools.shared_context import SharedContextDB
    from .config import CoordinationConfig, TeamConfig


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TeamHealthSnapshot:
    """Point-in-time health metrics for a single team."""

    team_id: str
    velocity: float
    wip_count: int
    blocked_count: int
    agent_count: int
    borrowed_in: List[str] = field(default_factory=list)
    borrowed_out: List[str] = field(default_factory=list)


@dataclass
class CrossTeamDependency:
    """A dependency between cards on different teams."""

    source_team: str
    target_team: str
    card_id: int
    dependency_type: str  # "blocks" | "needs_api" | "shared_component"
    status: str  # "open" | "resolved"


@dataclass
class BorrowRequest:
    """Request to temporarily move an agent between teams."""

    from_team: str
    to_team: str
    agent_id: str
    reason: str
    duration_sprints: int = 1


@dataclass
class CoordinationOutcome:
    """Result of a full coordination loop."""

    borrows: List[BorrowRequest] = field(default_factory=list)
    dependency_updates: List[CrossTeamDependency] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw_evaluation: str = ""


# ---------------------------------------------------------------------------
# CoordinationLoop
# ---------------------------------------------------------------------------


class CoordinationLoop:
    """Runs between-sprint and mid-sprint coordination across teams.

    The coordination loop uses designated coordinator agents (e.g. staff
    engineer, enablement lead) to evaluate cross-team health, detect
    dependencies, and recommend borrows or other actions.
    """

    def __init__(
        self,
        coordinators: List["BaseAgent"],
        team_configs: List["TeamConfig"],
        shared_db: "SharedContextDB",
        message_bus: "MessageBus",
        coordination_config: "CoordinationConfig",
    ):
        self.coordinators = coordinators
        self.team_configs = team_configs
        self.shared_db = shared_db
        self.message_bus = message_bus
        self.config = coordination_config

        # Map team_id → TeamConfig for quick lookup
        self._team_map: Dict[str, "TeamConfig"] = {tc.id: tc for tc in team_configs}

        # Track agents currently on loan per team
        self._agent_team_map: Dict[str, str] = {}  # agent_id → current team_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_full_loop(
        self,
        sprint_num: int,
        team_results: Dict[str, "SprintResult"],
        deadline: Optional[datetime] = None,
    ) -> CoordinationOutcome:
        """Between-sprint coordination: evaluate → reflect → plan."""
        snapshots = await self._gather_team_health(sprint_num, team_results)
        deps = await self._detect_dependencies(sprint_num)
        evaluation = await self._evaluate(snapshots, deps, team_results, deadline)
        outcome = await self._plan(evaluation, snapshots, deadline)
        await self._broadcast_outcome(outcome, sprint_num)
        return outcome

    async def run_mid_sprint_checkin(
        self,
        sprint_num: int,
        deadline: Optional[datetime] = None,
    ) -> List[str]:
        """Mid-sprint: lightweight health check, returns recommendations."""
        snapshots = await self._gather_team_health(sprint_num)
        return await self._checkin(snapshots, deadline)

    # ------------------------------------------------------------------
    # Internal: gather data
    # ------------------------------------------------------------------

    async def _gather_team_health(
        self,
        sprint_num: int,
        team_results: Optional[Dict[str, "SprintResult"]] = None,
    ) -> List[TeamHealthSnapshot]:
        """Query SharedContextDB per team and build health snapshots."""
        snapshots: List[TeamHealthSnapshot] = []

        for tc in self.team_configs:
            # WIP and blocked counts
            wip_count = await self.shared_db.get_wip_count_for_team(
                "in_progress", tc.id
            )
            blocked_count = await self.shared_db.get_wip_count_for_team(
                "blocked", tc.id
            )

            # Velocity from last sprint result
            velocity = 0.0
            if team_results and tc.id in team_results:
                velocity = float(team_results[tc.id].velocity)

            # Borrowed agents (scan AgentConfig.original_team_id)
            borrowed_in: List[str] = []
            borrowed_out: List[str] = []
            for aid in tc.agent_ids:
                orig = self._agent_team_map.get(aid, "")
                if orig and orig != tc.id:
                    borrowed_in.append(aid)
            # Agents whose original_team_id == tc.id but current team != tc.id
            for aid, orig_team in self._agent_team_map.items():
                if orig_team == tc.id and aid not in tc.agent_ids:
                    borrowed_out.append(aid)

            snapshots.append(
                TeamHealthSnapshot(
                    team_id=tc.id,
                    velocity=velocity,
                    wip_count=wip_count,
                    blocked_count=blocked_count,
                    agent_count=len(tc.agent_ids),
                    borrowed_in=borrowed_in,
                    borrowed_out=borrowed_out,
                )
            )

        return snapshots

    async def _detect_dependencies(self, sprint_num: int) -> List[CrossTeamDependency]:
        """Scan kanban cards for cross-team dependency metadata."""
        deps: List[CrossTeamDependency] = []
        cards = await self.shared_db.get_cards_with_dependency()

        for card in cards:
            metadata = card.get("metadata") or {}
            if isinstance(metadata, str):
                import json

                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    continue

            target_team = metadata.get("depends_on_team", "")
            if not target_team:
                continue

            source_team = card.get("team_id", "")
            deps.append(
                CrossTeamDependency(
                    source_team=source_team,
                    target_team=target_team,
                    card_id=card.get("id", 0),
                    dependency_type=metadata.get("dependency_type", "blocks"),
                    status=metadata.get("dependency_status", "open"),
                )
            )

        return deps

    # ------------------------------------------------------------------
    # Internal: coordinator LLM calls
    # ------------------------------------------------------------------

    async def _evaluate(
        self,
        snapshots: List[TeamHealthSnapshot],
        deps: List[CrossTeamDependency],
        team_results: Dict[str, "SprintResult"],
        deadline: Optional[datetime] = None,
    ) -> str:
        """Use first coordinator (staff engineer) to analyze cross-team state."""
        if not self.coordinators:
            return self._mock_evaluation(snapshots, deps)

        coordinator = self.coordinators[0]

        # Build prompt with structured data
        team_lines: List[str] = []
        for s in snapshots:
            team_lines.append(
                f"- {s.team_id}: velocity={s.velocity}, "
                f"WIP={s.wip_count}, blocked={s.blocked_count}, "
                f"agents={s.agent_count}, "
                f"borrowed_in={s.borrowed_in}, borrowed_out={s.borrowed_out}"
            )

        dep_lines: List[str] = []
        for d in deps:
            dep_lines.append(
                f"- Card #{d.card_id}: {d.source_team} → {d.target_team} "
                f"({d.dependency_type}, {d.status})"
            )

        result_lines: List[str] = []
        for tid, res in team_results.items():
            result_lines.append(
                f"- {tid}: velocity={res.velocity}, "
                f"features_completed={res.features_completed}"
            )

        time_context = self._build_time_context(deadline)

        prompt = (
            "You are the cross-team coordination analyst. Evaluate the state "
            "of all teams and identify issues.\n\n"
            + time_context
            + "## Team Health\n"
            + "\n".join(team_lines)
            + "\n\n"
            "## Cross-Team Dependencies\n"
            + ("\n".join(dep_lines) if dep_lines else "None detected")
            + "\n\n"
            "## Last Sprint Results\n"
            + ("\n".join(result_lines) if result_lines else "No prior results")
            + "\n\n"
            "Provide a structured analysis:\n"
            "1. Which teams are struggling?\n"
            "2. Are there blocking dependencies?\n"
            "3. Should any agents be borrowed between teams?\n"
            "4. General recommendations."
        )

        response = await coordinator.generate(prompt)
        return response

    async def _plan(
        self,
        evaluation: str,
        snapshots: List[TeamHealthSnapshot],
        deadline: Optional[datetime] = None,
    ) -> CoordinationOutcome:
        """Use second coordinator (enablement lead) to create action plan."""
        outcome = CoordinationOutcome(raw_evaluation=evaluation)

        if len(self.coordinators) < 2:
            # Single coordinator or none: parse from evaluation
            outcome.recommendations = self._extract_recommendations(evaluation)
            return outcome

        coordinator = self.coordinators[1]

        team_summary = "\n".join(
            f"- {s.team_id}: velocity={s.velocity}, blocked={s.blocked_count}, "
            f"agents={s.agent_count}"
            for s in snapshots
        )

        time_context = self._build_time_context(deadline)

        prompt = (
            "Based on the following cross-team evaluation, create an action plan.\n\n"
            + time_context
            + f"## Evaluation\n{evaluation}\n\n"
            f"## Team Summary\n{team_summary}\n\n"
            "List concrete actions:\n"
            "- BORROW: <agent_id> from <team> to <team> because <reason>\n"
            "- RECOMMEND: <recommendation text>\n"
            "Reply with one action per line."
        )

        response = await coordinator.generate(prompt)

        # Parse actions from response
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("BORROW:"):
                borrow = self._parse_borrow_line(line)
                if borrow:
                    outcome.borrows.append(borrow)
            elif line.upper().startswith("RECOMMEND:"):
                rec = line[len("RECOMMEND:") :].strip()
                if rec:
                    outcome.recommendations.append(rec)

        # If no structured output, extract recommendations from raw text
        if not outcome.recommendations and not outcome.borrows:
            outcome.recommendations = self._extract_recommendations(response)

        return outcome

    async def _checkin(
        self,
        snapshots: List[TeamHealthSnapshot],
        deadline: Optional[datetime] = None,
    ) -> List[str]:
        """Lightweight mid-sprint check using first coordinator."""
        if not self.coordinators:
            return self._mock_checkin_recommendations(snapshots)

        coordinator = self.coordinators[0]

        team_lines = "\n".join(
            f"- {s.team_id}: WIP={s.wip_count}, blocked={s.blocked_count}"
            for s in snapshots
        )

        time_context = self._build_time_context(deadline)

        prompt = (
            "Mid-sprint health check. Brief status:\n\n"
            + time_context
            + f"{team_lines}\n\n"
            "Any urgent issues? Reply with brief recommendations (one per line)."
        )

        response = await coordinator.generate(prompt)
        return self._extract_recommendations(response)

    async def _broadcast_outcome(
        self,
        outcome: CoordinationOutcome,
        sprint_num: int,
    ) -> None:
        """Publish coordination outcome to the message bus."""
        try:
            await self.message_bus.publish(
                "coordination",
                "coordination_outcome",
                {
                    "sprint": sprint_num,
                    "borrows": len(outcome.borrows),
                    "recommendations": outcome.recommendations[:5],
                    "dependency_updates": len(outcome.dependency_updates),
                },
            )
        except Exception:
            pass  # bus may not be running

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_time_context(deadline: Optional[datetime]) -> str:
        """Build a ``## Time Context`` prompt section when a deadline exists."""
        if deadline is None:
            return ""
        remaining = (deadline - datetime.now()).total_seconds()
        remaining_min = max(remaining / 60.0, 0.0)
        return (
            f"## Time Context\n"
            f"- Remaining overhead budget: ~{remaining_min:.1f} minutes\n"
            f"- Be concise. Focus on the most critical issues.\n\n"
        )

    def _parse_borrow_line(self, line: str) -> Optional[BorrowRequest]:
        """Parse a BORROW: line into a BorrowRequest.

        Expected format: BORROW: <agent_id> from <team> to <team> because <reason>
        """
        text = line[len("BORROW:") :].strip()
        parts = text.split()
        if len(parts) < 6:
            return None

        agent_id = parts[0]
        try:
            from_idx = parts.index("from")
            to_idx = parts.index("to")
            from_team = parts[from_idx + 1]
            to_team = parts[to_idx + 1]
        except (ValueError, IndexError):
            return None

        # Extract reason (everything after "because" or after to_team)
        reason = "coordinator recommendation"
        try:
            because_idx = parts.index("because")
            reason = " ".join(parts[because_idx + 1 :])
        except ValueError:
            pass

        return BorrowRequest(
            from_team=from_team,
            to_team=to_team,
            agent_id=agent_id,
            reason=reason,
            duration_sprints=self.config.borrow_duration_sprints,
        )

    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract non-empty lines as recommendations."""
        recs: List[str] = []
        for line in text.splitlines():
            line = line.strip().lstrip("-•*").strip()
            if line and len(line) > 5:
                recs.append(line)
        return recs[:10]  # cap at 10

    def _mock_evaluation(
        self,
        snapshots: List[TeamHealthSnapshot],
        deps: List[CrossTeamDependency],
    ) -> str:
        """Return a deterministic evaluation for mock/test mode."""
        team_ids = [s.team_id for s in snapshots]
        blocked = [s for s in snapshots if s.blocked_count > 0]
        parts = [f"Evaluated {len(snapshots)} teams: {', '.join(team_ids)}."]
        if blocked:
            parts.append(
                f"Teams with blocked work: " f"{', '.join(s.team_id for s in blocked)}."
            )
        if deps:
            parts.append(f"{len(deps)} cross-team dependencies detected.")
        parts.append("RECOMMEND: Continue monitoring team health.")
        return " ".join(parts)

    def _mock_checkin_recommendations(
        self,
        snapshots: List[TeamHealthSnapshot],
    ) -> List[str]:
        """Return deterministic mid-sprint recommendations for mock mode."""
        recs: List[str] = []
        for s in snapshots:
            if s.blocked_count > 0:
                recs.append(
                    f"Team {s.team_id} has {s.blocked_count} blocked items — "
                    "investigate blockers."
                )
        if not recs:
            recs.append("All teams healthy, no action needed.")
        return recs

    def update_agent_team_map(self, agent_id: str, original_team: str) -> None:
        """Track an agent's original team for borrow detection."""
        self._agent_team_map[agent_id] = original_team

    def clear_agent_team_map(self, agent_id: str) -> None:
        """Remove agent from the borrow tracking map."""
        self._agent_team_map.pop(agent_id, None)
