"""Multi-team orchestration — runs concurrent sprints across teams."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..agents.base_agent import BaseAgent
from ..agents.messaging import MessageBus
from ..tools.shared_context import SharedContextDB
from ..metrics.sprint_metrics import SprintResult
from .backlog import Backlog
from .config import CoordinationConfig, ExperimentConfig, TeamConfig
from .coordination_loop import BorrowRequest, CoordinationLoop
from .sprint_manager import SprintManager


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
            outcome = await self._coordination_loop.run_full_loop(
                sprint_num, self._last_results or {}
            )
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
        await self.distribute_portfolio_stories(sprint_num)

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

    async def distribute_portfolio_stories(self, sprint_num: int) -> None:
        """Round-robin allocate stories from portfolio backlog to teams without own backlogs."""
        if not self.portfolio_backlog or self.portfolio_backlog.remaining == 0:
            return

        # Find teams that don't have their own backlog
        teams_needing_stories = [
            tc.id for tc in self.team_configs if self._team_backlogs.get(tc.id) is None
        ]

        if not teams_needing_stories:
            return

        # Estimate stories per team (3 per team is a reasonable default)
        stories_per_team = 3
        total_needed = stories_per_team * len(teams_needing_stories)
        stories = self.portfolio_backlog.next_stories(total_needed)

        if not stories:
            return

        # Round-robin distribution
        team_stories: Dict[str, List[Dict]] = {tid: [] for tid in teams_needing_stories}
        for i, story in enumerate(stories):
            tid = teams_needing_stories[i % len(teams_needing_stories)]
            team_stories[tid].append(story)

        # Create in-memory Backlog for each team and assign to SprintManager
        for tid, assigned_stories in team_stories.items():
            if assigned_stories:
                team_backlog = Backlog.from_stories(
                    assigned_stories,
                    product_name=self.portfolio_backlog.product_name,
                    product_description=self.portfolio_backlog.product_description,
                )
                self._team_managers[tid].backlog = team_backlog

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
        recs = await self._coordination_loop.run_mid_sprint_checkin(sprint_num)
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

        report_path = self.output_dir / "final_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nPortfolio report: {report_path}")
