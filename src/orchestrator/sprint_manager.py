"""
Sprint lifecycle manager - orchestrates planning, execution, retro.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from ..agents.base_agent import BaseAgent
from ..agents.pairing import PairingEngine
from ..tools.kanban import KanbanBoard
from ..tools.shared_context import SharedContextDB
from ..metrics.sprint_metrics import SprintMetrics

class SprintManager:
    def __init__(self, agents: List[BaseAgent], shared_db: SharedContextDB, config, output_dir: Path):
        self.agents = agents
        self.db = shared_db
        self.config = config
        self.output_dir = output_dir
        self.pairing_engine = PairingEngine(agents)
        self.kanban = KanbanBoard(shared_db)
        self.metrics = SprintMetrics()

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
        retro_results = await self.run_retrospective(sprint_num)

        # Phase 4: Generate Artifacts
        print("📦 Generating Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output)

        # Update metrics
        result = await self.metrics.calculate_sprint_results(sprint_num, self.db, self.kanban)

        return result

    async def run_planning(self, sprint_num: int):
        """Sprint planning meeting with full team."""
        # PO presents prioritized backlog
        # Team estimates and selects work
        # Decompose into tasks
        pass

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

    async def run_retrospective(self, sprint_num: int):
        """Team retrospective - Keep/Drop/Puzzle format."""
        # All agents participate
        # Generate retro notes
        # Update meta-learnings
        pass

    async def generate_sprint_artifacts(self, sprint_num: int, output_path: Path):
        """Generate all required sprint artifacts."""

        # 1. Kanban snapshot
        kanban_data = await self.kanban.get_snapshot()
        (output_path / "kanban.json").write_text(json.dumps(kanban_data, indent=2))

        # 2. Pairing log
        # 3. Retro notes  
        # 4. Test coverage
        # 5. ADRs
        pass

    async def stakeholder_review(self, sprint_num: int):
        """Every 5 sprints: comprehensive stakeholder review."""
        print(f"
🎯 STAKEHOLDER REVIEW (Sprint {sprint_num})")
        # Present velocity, quality, escalations, demos
        pass
