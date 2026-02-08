"""
Sprint lifecycle manager - orchestrates planning, execution, retro.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from ..agents.base_agent import BaseAgent
from ..agents.pairing import PairingEngine
from ..tools.kanban import KanbanBoard
from ..tools.shared_context import SharedContextDB
from ..metrics.sprint_metrics import SprintMetrics


class SprintManager:
    """Manages the full lifecycle of each sprint."""

    def __init__(
        self,
        agents: List[BaseAgent],
        shared_db: SharedContextDB,
        config,
        output_dir: Path,
    ):
        self.agents = agents
        self.db = shared_db
        self.config = config
        self.output_dir = output_dir
        self.pairing_engine = PairingEngine(agents, db=shared_db)
        self.kanban = KanbanBoard(
            shared_db,
            wip_limits=getattr(config, "wip_limits", {"in_progress": 4, "review": 2}),
        )
        self.metrics = SprintMetrics()
        self._sprint_results: List[Dict] = []

    async def run_sprint(self, sprint_num: int):
        """Execute one complete sprint (20 min wall-clock)."""

        sprint_start = datetime.now()
        sprint_output = self.output_dir / f"sprint-{sprint_num:02d}"
        sprint_output.mkdir(parents=True, exist_ok=True)

        # Phase 1: Planning (not in 20min)
        print("📋 Sprint Planning...")
        await self.run_planning(sprint_num)

        # Phase 2: Development (20 minutes)
        print("💻 Development Phase (20 minutes)...")
        await self.run_development(sprint_num, duration_minutes=20)

        # Phase 3: Retrospective
        print("🔄 Retrospective...")
        await self.run_retrospective(sprint_num)

        # Phase 4: Generate Artifacts
        print("📦 Generating Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output)

        # Update metrics
        result = await self.metrics.calculate_sprint_results(sprint_num, self.db, self.kanban)

        self._sprint_results.append(
            {
                "sprint": sprint_num,
                "velocity": result.velocity,
                "features_completed": result.features_completed,
                "test_coverage": result.test_coverage,
                "pairing_sessions": result.pairing_sessions,
                "cycle_time_avg": result.cycle_time_avg,
            }
        )

        return result

    async def run_planning(self, sprint_num: int):
        """Sprint planning meeting with full team.

        PO presents prioritized backlog; team selects tasks for the sprint.
        """
        # Find PO agent
        po = next((a for a in self.agents if a.config.role_id == "po"), None)

        if po is not None:
            backlog_prompt = (
                f"Sprint {sprint_num} planning: propose 3-5 user stories "
                "from the backlog for the team to work on this sprint."
            )
            stories_text = await po.generate(backlog_prompt)
        else:
            stories_text = f"Sprint {sprint_num} default backlog items."

        # Seed kanban with sprint tasks parsed from PO response
        # For simulation we create one generic task per sprint
        sample_tasks = [
            {
                "title": f"Sprint {sprint_num} Task {i}",
                "description": f"Implement feature {i} for sprint {sprint_num}",
                "status": "ready",
                "story_points": 2,
                "sprint": sprint_num,
            }
            for i in range(1, 4)
        ]
        for task in sample_tasks:
            await self.kanban.add_card(task)

    async def run_development(self, sprint_num: int, duration_minutes: int):
        """Main development phase with pairing."""

        end_time = datetime.now() + timedelta(minutes=duration_minutes)

        while datetime.now() < end_time:
            # Get available pairs
            available_pairs = self.pairing_engine.get_available_pairs()

            # Assign work from Kanban
            for pair in available_pairs:
                task = await self.kanban.pull_ready_task()
                if task:
                    asyncio.create_task(
                        self.pairing_engine.run_pairing_session(pair, task)
                    )

            # Tick simulation forward
            await asyncio.sleep(1)  # 1 second real = ~4 minutes simulated

        # Wait for all pairing sessions to complete
        await self.pairing_engine.wait_for_completion()

    async def run_retrospective(self, sprint_num: int) -> Dict:
        """Team retrospective — Keep/Drop/Puzzle format.

        Each agent contributes observations; results saved to output dir.
        """
        retro: Dict = {"sprint": sprint_num, "keep": [], "drop": [], "puzzle": []}

        prompt = (
            f"Sprint {sprint_num} retrospective. "
            "Provide one KEEP, one DROP, and one PUZZLE item."
        )
        for agent in self.agents:
            response = await agent.generate(prompt)
            retro["keep"].append(f"{agent.config.role_id}: {response}")

        return retro

    async def generate_sprint_artifacts(self, sprint_num: int, output_path: Path):
        """Generate all required sprint artifacts."""

        # 1. Kanban snapshot
        kanban_data = await self.kanban.get_snapshot()
        (output_path / "kanban.json").write_text(json.dumps(kanban_data, indent=2))
        await self.db.save_kanban_snapshot(sprint_num, kanban_data)

        # 2. Pairing log
        sessions = await self.db.get_pairing_sessions_for_sprint(sprint_num)
        (output_path / "pairing_log.json").write_text(json.dumps(sessions, indent=2))

        # 3. Retro notes
        retro_data = await self.run_retrospective(sprint_num)
        (output_path / "retro.json").write_text(json.dumps(retro_data, indent=2))

    async def stakeholder_review(self, sprint_num: int):
        """Every N sprints: comprehensive stakeholder review."""
        print(f"\n🎯 STAKEHOLDER REVIEW (Sprint {sprint_num})")
        if self._sprint_results:
            velocities = [r["velocity"] for r in self._sprint_results]
            avg_velocity = sum(velocities) / len(velocities)
            print(f"  Average velocity: {avg_velocity:.1f} points/sprint")
            print(f"  Sprints completed: {len(self._sprint_results)}")
            latest = self._sprint_results[-1]
            print(f"  Latest test coverage: {latest['test_coverage']}%")

    async def generate_final_report(self):
        """Aggregate all sprint results and write final JSON report."""
        report = {
            "experiment": getattr(self.config, "name", "experiment"),
            "total_sprints": len(self._sprint_results),
            "sprints": self._sprint_results,
        }
        if self._sprint_results:
            velocities = [r["velocity"] for r in self._sprint_results]
            report["avg_velocity"] = sum(velocities) / len(velocities)
            report["total_features"] = sum(r["features_completed"] for r in self._sprint_results)

        report_path = self.output_dir / "final_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nFinal report written to {report_path}")
