"""
Main orchestrator for running agile agent team sprints.
"""

import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from .sprint_manager import SprintManager
from .config import load_config
from ..agents.agent_factory import AgentFactory
from ..tools.shared_context import SharedContextDB
from ..metrics.prometheus_exporter import start_metrics_server

async def run_experiment(config_path: str, num_sprints: int, output_dir: str):
    """Run the complete experiment for N sprints."""

    # Load configuration
    config = load_config(config_path)

    # Initialize shared context database
    db = SharedContextDB(config.database_url)
    await db.initialize()

    # Start metrics server
    start_metrics_server(port=8080)

    # Create agent factory and load all agents
    factory = AgentFactory(config.team_config_dir, config.vllm_endpoint)
    agents = await factory.create_all_agents()

    print(f"Loaded {len(agents)} agents")
    for agent in agents:
        print(f"  - {agent.role_id}: {agent.name}")

    # Initialize sprint manager
    sprint_mgr = SprintManager(
        agents=agents,
        shared_db=db,
        config=config,
        output_dir=Path(output_dir)
    )

    # Run sprints
    for sprint_num in range(1, num_sprints + 1):
        print(f"
{'='*60}")
        print(f"SPRINT {sprint_num} - {datetime.now()}")
        print(f"{'='*60}
")

        result = await sprint_mgr.run_sprint(sprint_num)

        # Stakeholder review every 5 sprints
        if sprint_num % 5 == 0:
            await sprint_mgr.stakeholder_review(sprint_num)

        # Print summary
        print(f"
Sprint {sprint_num} Summary:")
        print(f"  Velocity: {result.velocity} points")
        print(f"  Features completed: {result.features_completed}")
        print(f"  Test coverage: {result.test_coverage}%")
        print(f"  Pairing sessions: {result.pairing_sessions}")

    # Final report
    await sprint_mgr.generate_final_report()

    print(f"
Experiment complete! Output: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Run agile agent team experiment")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--sprints", type=int, default=10, help="Number of sprints")
    parser.add_argument("--output", default="outputs/experiment", help="Output directory")

    args = parser.parse_args()

    asyncio.run(run_experiment(args.config, args.sprints, args.output))

if __name__ == "__main__":
    main()
