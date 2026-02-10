"""Main orchestrator for running agile agent team sprints."""

import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from .sprint_manager import SprintManager
from .config import load_config
from .backlog import Backlog
from ..agents.agent_factory import AgentFactory
from ..tools.shared_context import SharedContextDB
from ..metrics.prometheus_exporter import start_metrics_server


async def run_experiment(
    config_path: str,
    num_sprints: int,
    output_dir: str,
    backlog_path: str,
    database_url: str = "",
    duration_minutes: int = 0,
):
    """Run the complete experiment for N sprints."""

    config = load_config(config_path, database_url=database_url or None)

    # CLI --duration overrides config file value
    if duration_minutes > 0:
        config.sprint_duration_minutes = duration_minutes

    db = SharedContextDB(config.database_url)
    await db.initialize()

    start_metrics_server(port=8080)

    factory = AgentFactory(
        config.team_config_dir,
        config.vllm_endpoint,
        agent_model_configs=config.agent_configs,
        runtime_configs=config.runtime_configs,
    )
    agents = await factory.create_all_agents()

    print(f"Loaded {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.config.role_id}: {agent.config.name}")

    # Load product backlog if file exists
    backlog = None
    bp = Path(backlog_path)
    if bp.exists():
        backlog = Backlog(str(bp))
        print(f"Backlog: {backlog.product_name} ({backlog.remaining} stories)")
    else:
        print(f"No backlog file found at {bp}; using generated tasks")

    sprint_mgr = SprintManager(
        agents=agents,
        shared_db=db,
        config=config,
        output_dir=Path(output_dir),
        backlog=backlog,
    )

    # Determine sprint range based on sprint_zero_enabled
    start_sprint = 0 if config.sprint_zero_enabled else 1
    end_sprint = num_sprints if config.sprint_zero_enabled else num_sprints

    for sprint_num in range(start_sprint, end_sprint + 1):
        sprint_label = (
            "SPRINT 0 (Infrastructure)" if sprint_num == 0 else f"SPRINT {sprint_num}"
        )
        print(f"\n{'='*60}")
        print(f"{sprint_label}  [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"{'='*60}")

        result = await sprint_mgr.run_sprint(sprint_num)

        # Sprint 0 specific reporting
        if sprint_num == 0:
            ci_validated = getattr(result, "ci_validated", True)
            if ci_validated:
                print("  ✓ Sprint 0 complete: Infrastructure validated")
            else:
                print("  ✗ Sprint 0 incomplete: CI validation failed")
        else:
            print(
                f"  velocity={result.velocity}pts  "
                f"done={result.features_completed}  "
                f"sessions={result.pairing_sessions}"
            )

        if sprint_num % config.sprints_per_stakeholder_review == 0:
            await sprint_mgr.stakeholder_review(sprint_num)

    await sprint_mgr.generate_final_report()
    print(f"\nExperiment complete. Output: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agile agent team experiment")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--sprints", type=int, default=10)
    parser.add_argument("--output", default="outputs/experiment")
    parser.add_argument("--backlog", default="backlog.yaml")
    parser.add_argument(
        "--db-url", default="", help="Override database URL (use mock:// for local dev)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Wall-clock minutes per sprint (default: 60, overrides config)",
    )
    args = parser.parse_args()

    asyncio.run(
        run_experiment(
            args.config,
            args.sprints,
            args.output,
            args.backlog,
            args.db_url,
            args.duration,
        )
    )


if __name__ == "__main__":
    main()
