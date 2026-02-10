"""Multi-team orchestration — runs concurrent sprints across teams."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..agents.base_agent import BaseAgent
from ..agents.messaging import MessageBus
from ..tools.shared_context import SharedContextDB
from ..metrics.sprint_metrics import SprintResult
from .backlog import Backlog
from .config import CoordinationConfig, ExperimentConfig, TeamConfig
from .coordination_loop import BorrowRequest, CoordinationLoop, CoordinationOutcome
from .overhead_budget import OverheadBudgetTracker, StepTiming
from .sprint_manager import SprintManager
from .story_distributor import (
    build_team_profiles,
    build_triage_prompt,
    heuristic_distribute,
    parse_assignments,
)


class MultiTeamOrchestrator:
    """Coordinates multiple teams running concurrent sprints."""

    def __init__(
        self,
        team_configs: List[TeamConfig],
        all_agents: List[BaseAgent],
        shared_db: SharedContextDB,
        experiment_config: ExperimentConfig,
        portfolio_backlog: Optional[Backlog],
        message_bus: MessageBus,
        output_dir: Path,
    ):
        self.team_configs = team_configs
        self.all_agents = all_agents
        self.shared_db = shared_db
        self.config = experiment_config
        self.portfolio_backlog = portfolio_backlog
        self.message_bus = message_bus
        self.output_dir = output_dir

        # Populated by setup_teams()
        self._team_agents: Dict[str, List[BaseAgent]] = {}
        self._team_managers: Dict[str, SprintManager] = {}
        self._team_backlogs: Dict[str, Optional[Backlog]] = {}
        self._team_results: Dict[str, List[Dict[str, Any]]] = {}

        # Coordination (populated by setup_coordination)
        self._coordination_loop: Optional[CoordinationLoop] = None
        self._coordination_config: Optional[CoordinationConfig] = None
        self._last_results: Optional[Dict[str, SprintResult]] = None

        # Overhead budget (populated by set_budget_tracker)
        self._budget_tracker: Optional[OverheadBudgetTracker] = None

    async def setup_teams(self) -> None:
        """Partition agents into teams, create per-team SprintManagers + channels."""
        agent_map = {a.agent_id: a for a in self.all_agents}

        for tc in self.team_configs:
            # Partition agents
            team_agents = [agent_map[aid] for aid in tc.agent_ids if aid in agent_map]
            self._team_agents[tc.id] = team_agents

            # Assign team_id to each agent
            for agent in team_agents:
                agent.config.team_id = tc.id

            # Load team-specific backlog (or None to use portfolio)
            team_backlog: Optional[Backlog] = None
            if tc.backlog_path and Path(tc.backlog_path).exists():
                team_backlog = Backlog(tc.backlog_path)

            self._team_backlogs[tc.id] = team_backlog

            # Create per-team output directory
            team_output = self.output_dir / tc.id
            team_output.mkdir(parents=True, exist_ok=True)

            # Override WIP limits if team specifies them
            team_config = self.config
            if tc.wip_limits:
                # Create a shallow copy of config with overridden wip_limits
                from dataclasses import replace

                team_config = replace(self.config, wip_limits=tc.wip_limits)

            # Create per-team SprintManager (shares parent message bus)
            manager = SprintManager(
                agents=team_agents,
                shared_db=self.shared_db,
                config=team_config,
                output_dir=team_output,
                backlog=team_backlog,
                team_id=tc.id,
                message_bus=self.message_bus,
            )
            self._team_managers[tc.id] = manager
            self._team_results[tc.id] = []

            # Create team channel on message bus
            try:
                team_member_ids = {a.agent_id for a in team_agents}
                self.message_bus.create_channel(
                    f"team:{tc.id}", members=team_member_ids
                )
            except ValueError:
                pass  # channel already exists

        # Create portfolio channel for cross-team messages
        try:
            all_member_ids = {a.agent_id for a in self.all_agents}
            self.message_bus.create_channel("portfolio", members=all_member_ids)
        except ValueError:
            pass  # channel already exists

    def set_budget_tracker(self, tracker: OverheadBudgetTracker) -> None:
        """Attach an overhead budget tracker for timebox enforcement."""
        self._budget_tracker = tracker

    async def run_iteration_zero(self) -> None:
        """Pre-sprint portfolio setup with timebox.

        Distributes the full portfolio to teams using coordinator triage
        (if available) or heuristic fallback.  On timeout, falls back to
        instant heuristic distribution.
        """
        tracker = self._budget_tracker
        if tracker is None:
            # No budget tracker — run unbounded
            await self.distribute_portfolio_stories(1)
            return

        timeout = tracker.get_iteration_zero_timeout()
        deadline = tracker.get_deadline(timeout)
        started = datetime.now()
        timed_out = False

        try:
            await asyncio.wait_for(
                self.distribute_portfolio_stories(1, deadline=deadline),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed_out = True
            print("  [BUDGET] Iteration 0 timed out — falling back to heuristic")
            self._heuristic_distribute_all()

        timing = StepTiming(
            step_name="iteration_zero",
            sprint_num=0,
            started=started,
            ended=datetime.now(),
            timeout_seconds=timeout,
            timed_out=timed_out,
        )
        tracker.record_step(timing)

    def _heuristic_distribute_all(self) -> None:
        """Emergency fallback: distribute all remaining portfolio stories via heuristic."""
        if not self.portfolio_backlog or self.portfolio_backlog.remaining == 0:
            return

        stories_per_team = {
            tc.id: max(2, min(5, len(self._team_agents.get(tc.id, []))))
            for tc in self.team_configs
        }
        total_needed = sum(stories_per_team.values())
        stories = self.portfolio_backlog.next_stories(total_needed)
        if not stories:
            return

        profiles = build_team_profiles(self.team_configs, self._team_agents)
        is_brownfield = bool(
            self.config.repo_config and self.config.repo_config.get("url")
        )
        team_stories = heuristic_distribute(stories, profiles, is_brownfield)

        for tid, assigned_stories in team_stories.items():
            if assigned_stories:
                team_backlog = Backlog.from_stories(
                    assigned_stories,
                    product_name=(
                        self.portfolio_backlog.product_name
                        if self.portfolio_backlog
                        else ""
                    ),
                    product_description=(
                        self.portfolio_backlog.product_description
                        if self.portfolio_backlog
                        else ""
                    ),
                )
                self._team_managers[tid].backlog = team_backlog

    async def run_sprint(self, sprint_num: int) -> Dict[str, SprintResult]:
        """Run one sprint concurrently across all teams via asyncio.gather."""
        # Return borrowed agents from previous sprint
        if self._coordination_config is not None:
            returned = await self.return_borrowed_agents()
            if returned:
                print(f"  Returned {returned} borrowed agent(s) to home teams")

        # Pre-sprint coordination (full loop)
        if (
            self._coordination_loop is not None
            and self._coordination_config is not None
            and self._coordination_config.enabled
            and sprint_num > 1
            and sprint_num % self._coordination_config.full_loop_cadence == 0
        ):
            print("  Running cross-team coordination loop...")
            outcome = await self._run_timed_coordination(sprint_num)
            if outcome is not None:
                # Process borrows (respect max_borrows_per_sprint)
                for borrow in outcome.borrows[
                    : self._coordination_config.max_borrows_per_sprint
                ]:
                    success = await self.borrow_agent(borrow)
                    if success:
                        print(
                            f"  [BORROW] {borrow.agent_id}: "
                            f"{borrow.from_team} → {borrow.to_team}"
                        )
                if outcome.recommendations:
                    for rec in outcome.recommendations[:3]:
                        print(f"  [COORD] {rec}")

        # Distribute portfolio stories before the sprint
        await self._run_timed_distribution(sprint_num)

        # Run all teams concurrently
        team_ids = list(self._team_managers.keys())

        async def _run_team_sprint(team_id: str) -> Optional[SprintResult]:
            manager = self._team_managers[team_id]
            try:
                result = await manager.run_sprint(sprint_num)
                return result
            except Exception as exc:
                print(f"  [{team_id}] Sprint {sprint_num} failed: {exc}")
                return None

        results = await asyncio.gather(
            *[_run_team_sprint(tid) for tid in team_ids],
            return_exceptions=False,
        )

        team_results: Dict[str, SprintResult] = {}
        for tid, result in zip(team_ids, results):
            if result is not None:
                team_results[tid] = result
                self._team_results[tid].append(
                    {
                        "sprint": sprint_num,
                        "velocity": result.velocity,
                        "features_completed": result.features_completed,
                    }
                )

        self._last_results = team_results
        return team_results

    async def distribute_portfolio_stories(
        self,
        sprint_num: int,
        deadline: Optional[datetime] = None,
    ) -> None:
        """Distribute stories from portfolio backlog to all teams.

        Uses intelligent heuristic scoring by default.  When coordination is
        enabled with ``portfolio_triage``, the coordinator agent is called
        first and the heuristic is used as a fallback for any unassigned
        stories.
        """
        if not self.portfolio_backlog or self.portfolio_backlog.remaining == 0:
            return

        # In multi-team mode ALL teams participate (portfolio is the source)
        participating_teams = [tc for tc in self.team_configs]

        if not participating_teams:
            return

        # Velocity-aware: max(2, min(5, agent_count)) stories per team
        stories_per_team = {
            tc.id: max(2, min(5, len(self._team_agents.get(tc.id, []))))
            for tc in participating_teams
        }
        total_needed = sum(stories_per_team.values())
        stories = self.portfolio_backlog.next_stories(total_needed)

        if not stories:
            return

        # Build team capability profiles
        profiles = build_team_profiles(participating_teams, self._team_agents)

        # Determine brownfield
        is_brownfield = bool(
            self.config.repo_config and self.config.repo_config.get("url")
        )

        # Try coordinator triage first, fall back to heuristic
        team_stories: Optional[Dict[str, List[Dict]]] = None
        method = "heuristic"

        if (
            self._coordination_config is not None
            and self._coordination_config.enabled
            and self._coordination_config.portfolio_triage
            and self._coordination_loop is not None
            and self._coordination_loop.coordinators
        ):
            team_stories = await self._coordinator_distribute(
                stories, profiles, deadline=deadline
            )
            if team_stories:
                method = "coordinator"

        if team_stories is None:
            team_stories = heuristic_distribute(stories, profiles, is_brownfield)

        # Assign stories to team SprintManagers
        for tid, assigned_stories in team_stories.items():
            if assigned_stories:
                team_backlog = Backlog.from_stories(
                    assigned_stories,
                    product_name=self.portfolio_backlog.product_name,
                    product_description=self.portfolio_backlog.product_description,
                )
                self._team_managers[tid].backlog = team_backlog

        # Log distribution summary
        total_assigned = sum(len(s) for s in team_stories.values())
        print(
            f"  Portfolio distribution ({method}): "
            + ", ".join(f"{tid}={len(s)}" for tid, s in team_stories.items() if s)
            + f" ({total_assigned} total)"
        )

    async def _coordinator_distribute(
        self,
        stories: List[Dict],
        profiles: Dict[str, Any],
        deadline: Optional[datetime] = None,
    ) -> Optional[Dict[str, List[Dict]]]:
        """Use coordinator agent for portfolio triage.

        Returns None if the coordinator fails or returns unusable output,
        so the caller can fall back to heuristic distribution.
        """
        if self._coordination_loop is None or not self._coordination_loop.coordinators:
            return None

        coordinator = self._coordination_loop.coordinators[0]
        product_metadata: Optional[Dict] = None
        if self.portfolio_backlog:
            product_metadata = {
                "name": self.portfolio_backlog.product_name,
                "description": self.portfolio_backlog.product_description,
            }

        prompt = build_triage_prompt(stories, profiles, product_metadata)

        # Inject time context when deadline is set
        if deadline is not None:
            remaining = (deadline - datetime.now()).total_seconds()
            remaining_min = max(remaining / 60.0, 0.0)
            prompt += (
                f"\n## Time Context\n"
                f"- Remaining overhead budget: ~{remaining_min:.1f} minutes\n"
                f"- Be concise. Assign quickly.\n"
            )

        try:
            response = await coordinator.generate(prompt)
        except Exception:
            return None

        valid_team_ids = list(profiles.keys())
        assignments = parse_assignments(response, stories, valid_team_ids)

        # Check that at least some stories were assigned
        total_assigned = sum(len(s) for s in assignments.values())
        if total_assigned == 0:
            return None

        # For any unassigned stories, fall back to heuristic
        assigned_ids = {
            s["id"] for stories_list in assignments.values() for s in stories_list
        }
        unassigned = [s for s in stories if s.get("id") not in assigned_ids]
        if unassigned:
            fallback = heuristic_distribute(unassigned, profiles)
            for tid, extra in fallback.items():
                assignments[tid].extend(extra)

        return assignments

    # ------------------------------------------------------------------
    # Timed wrappers (use budget tracker when available)
    # ------------------------------------------------------------------

    async def _run_timed_coordination(
        self, sprint_num: int
    ) -> Optional[CoordinationOutcome]:
        """Run coordination loop with optional timebox."""
        if self._coordination_loop is None:
            return None

        tracker = self._budget_tracker
        if tracker is None:
            # No budget tracker — run unbounded
            return await self._coordination_loop.run_full_loop(
                sprint_num, self._last_results or {}
            )

        timeout = tracker.get_step_timeout("coordination", sprint_num)
        deadline = tracker.get_deadline(timeout)
        started = datetime.now()
        timed_out = False
        result: Optional[CoordinationOutcome] = None

        try:
            result = await asyncio.wait_for(
                self._coordination_loop.run_full_loop(
                    sprint_num, self._last_results or {}, deadline=deadline
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed_out = True
            print("  [BUDGET] Coordination loop timed out — skipping borrows")

        tracker.record_step(
            StepTiming(
                step_name="coordination",
                sprint_num=sprint_num,
                started=started,
                ended=datetime.now(),
                timeout_seconds=timeout,
                timed_out=timed_out,
            )
        )
        return result

    async def _run_timed_distribution(self, sprint_num: int) -> None:
        """Run portfolio distribution with optional timebox."""
        tracker = self._budget_tracker
        if tracker is None:
            await self.distribute_portfolio_stories(sprint_num)
            return

        timeout = tracker.get_step_timeout("distribution", sprint_num)
        deadline = tracker.get_deadline(timeout)
        started = datetime.now()
        timed_out = False

        try:
            await asyncio.wait_for(
                self.distribute_portfolio_stories(sprint_num, deadline=deadline),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed_out = True
            print("  [BUDGET] Distribution timed out — falling back to heuristic")
            self._heuristic_distribute_all()

        tracker.record_step(
            StepTiming(
                step_name="distribution",
                sprint_num=sprint_num,
                started=started,
                ended=datetime.now(),
                timeout_seconds=timeout,
                timed_out=timed_out,
            )
        )

    # ------------------------------------------------------------------
    # Coordination setup + agent borrowing
    # ------------------------------------------------------------------

    async def setup_coordination(
        self,
        coordinators: List[BaseAgent],
        coordination_config: CoordinationConfig,
    ) -> None:
        """Initialize CoordinationLoop with coordinator agents."""
        self._coordination_loop = CoordinationLoop(
            coordinators=coordinators,
            team_configs=self.team_configs,
            shared_db=self.shared_db,
            message_bus=self.message_bus,
            coordination_config=coordination_config,
        )
        self._coordination_config = coordination_config

        # Create coordination channel (coordinators + all team agents)
        coord_ids = {a.agent_id for a in coordinators}
        all_ids = {a.agent_id for a in self.all_agents} | coord_ids
        try:
            self.message_bus.create_channel("coordination", members=all_ids)
        except ValueError:
            pass  # channel already exists

        # Set mid-sprint callback on team managers when enabled
        if coordination_config.mid_sprint_checkin:
            for manager in self._team_managers.values():
                manager._mid_sprint_callback = self._mid_sprint_checkin_callback

    async def _mid_sprint_checkin_callback(self, sprint_num: int) -> None:
        """Called by SprintManager mid-sprint for lightweight coordination."""
        if self._coordination_loop is None:
            return

        tracker = self._budget_tracker
        if tracker is None:
            recs = await self._coordination_loop.run_mid_sprint_checkin(sprint_num)
            for rec in recs[:3]:
                print(f"  [MID-SPRINT] {rec}")
            return

        timeout = tracker.get_step_timeout("checkin", sprint_num)
        deadline = tracker.get_deadline(timeout)
        started = datetime.now()
        timed_out = False
        recs = []

        try:
            recs = await asyncio.wait_for(
                self._coordination_loop.run_mid_sprint_checkin(
                    sprint_num, deadline=deadline
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            timed_out = True
            print("  [BUDGET] Mid-sprint checkin timed out — skipping")

        tracker.record_step(
            StepTiming(
                step_name="checkin",
                sprint_num=sprint_num,
                started=started,
                ended=datetime.now(),
                timeout_seconds=timeout,
                timed_out=timed_out,
            )
        )

        for rec in recs[:3]:
            print(f"  [MID-SPRINT] {rec}")

    async def borrow_agent(self, request: BorrowRequest) -> bool:
        """Move agent from one team to another for borrow_duration sprints."""
        from_agents = self._team_agents.get(request.from_team, [])
        to_agents = self._team_agents.get(request.to_team, [])

        if request.to_team not in self._team_agents:
            return False

        # Find the agent in the source team
        agent = next((a for a in from_agents if a.agent_id == request.agent_id), None)
        if agent is None:
            return False

        # Set original_team_id if not already set (first borrow)
        if not agent.config.original_team_id:
            agent.config.original_team_id = request.from_team

        # Move agent between teams
        agent.config.team_id = request.to_team
        self._team_agents[request.from_team] = [
            a for a in from_agents if a.agent_id != request.agent_id
        ]
        self._team_agents[request.to_team] = to_agents + [agent]

        # Update SprintManager agent lists
        if request.from_team in self._team_managers:
            mgr = self._team_managers[request.from_team]
            mgr.agents = [a for a in mgr.agents if a.agent_id != request.agent_id]
        if request.to_team in self._team_managers:
            mgr = self._team_managers[request.to_team]
            mgr.agents = mgr.agents + [agent]

        # Track in coordination loop
        if self._coordination_loop is not None:
            self._coordination_loop.update_agent_team_map(
                request.agent_id, request.from_team
            )

        return True

    async def return_borrowed_agents(self) -> int:
        """Return all agents with original_team_id set back to their home teams."""
        count = 0
        # Collect all agents across all teams
        all_team_agents = [a for agents in self._team_agents.values() for a in agents]

        for agent in all_team_agents:
            if not agent.config.original_team_id:
                continue

            original_team = agent.config.original_team_id
            current_team = agent.config.team_id

            if original_team == current_team:
                # Already home, just clear the flag
                agent.config.original_team_id = ""
                continue

            # Move back to original team
            self._team_agents[current_team] = [
                a
                for a in self._team_agents.get(current_team, [])
                if a.agent_id != agent.agent_id
            ]
            self._team_agents.setdefault(original_team, []).append(agent)

            # Update SprintManager agent lists
            if current_team in self._team_managers:
                mgr = self._team_managers[current_team]
                mgr.agents = [a for a in mgr.agents if a.agent_id != agent.agent_id]
            if original_team in self._team_managers:
                mgr = self._team_managers[original_team]
                if agent not in mgr.agents:
                    mgr.agents = mgr.agents + [agent]

            agent.config.team_id = original_team
            agent.config.original_team_id = ""

            # Clear from coordination loop tracking
            if self._coordination_loop is not None:
                self._coordination_loop.clear_agent_team_map(agent.agent_id)

            count += 1

        return count

    async def stakeholder_review(self, sprint_num: int) -> None:
        """Portfolio-level stakeholder review (delegates to first team's notifier)."""
        # Use the first team's sprint manager for the stakeholder review
        first_manager = next(iter(self._team_managers.values()), None)
        if first_manager is None:
            return

        # Aggregate results across teams for the review
        print(f"\n  PORTFOLIO STAKEHOLDER REVIEW (Sprint {sprint_num})")
        for tid, results in self._team_results.items():
            if results:
                velocities = [r["velocity"] for r in results]
                avg_vel = sum(velocities) / len(velocities)
                print(f"    [{tid}] avg velocity={avg_vel:.1f}")

        await first_manager.stakeholder_review(sprint_num)

    async def generate_final_report(self) -> None:
        """Generate per-team + aggregated portfolio report."""
        report: Dict[str, Any] = {
            "experiment": getattr(self.config, "name", "experiment"),
            "mode": "multi_team",
            "teams": {},
            "portfolio": {},
        }

        total_velocity = 0
        total_features = 0

        for tid, manager in self._team_managers.items():
            # Generate per-team report
            await manager.generate_final_report()

            team_results = self._team_results.get(tid, [])
            velocities = [r["velocity"] for r in team_results]
            features = [r["features_completed"] for r in team_results]

            team_report = {
                "total_sprints": len(team_results),
                "sprints": team_results,
                "avg_velocity": (
                    sum(velocities) / len(velocities) if velocities else 0
                ),
                "total_features": sum(features),
            }
            report["teams"][tid] = team_report
            total_velocity += sum(velocities)
            total_features += sum(features)

        # Portfolio-level aggregation
        num_sprints = max((len(r) for r in self._team_results.values()), default=0)
        report["portfolio"] = {
            "total_sprints": num_sprints,
            "total_velocity": total_velocity,
            "total_features": total_features,
            "num_teams": len(self._team_managers),
        }

        # Overhead budget report
        if self._budget_tracker is not None:
            report["overhead_budget"] = self._budget_tracker.to_report()

        report_path = self.output_dir / "final_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nPortfolio report: {report_path}")
