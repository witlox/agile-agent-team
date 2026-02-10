"""Main orchestrator for running agile agent team sprints."""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

from .sprint_manager import SprintManager
from .multi_team import MultiTeamOrchestrator
from .config import load_config
from .backlog import Backlog
from .experiment_resume import (
    detect_last_sprint,
    detect_last_sprint_multi_team,
    restore_selected_story_ids,
    restore_selected_story_ids_multi_team,
    restore_sprint_results,
    restore_team_results,
)
from .overhead_budget import OverheadBudgetTracker
from ..agents.agent_factory import AgentFactory
from ..agents.messaging import create_message_bus
from ..tools.shared_context import SharedContextDB
from ..metrics.prometheus_exporter import start_metrics_server


def _print_sprint_header(sprint_num: int) -> None:
    """Print the banner for a sprint."""
    sprint_label = (
        "SPRINT 0 (Infrastructure)" if sprint_num == 0 else f"SPRINT {sprint_num}"
    )
    print(f"\n{'='*60}")
    print(f"{sprint_label}  [{datetime.now().strftime('%H:%M:%S')}]")
    print(f"{'='*60}")


async def run_experiment(
    config_path: str,
    num_sprints: int,
    output_dir: str,
    backlog_path: str,
    database_url: str = "",
    duration_minutes: int = 0,
    continue_sprints: int = 0,
) -> None:
    """Run the complete experiment for N sprints.

    When *continue_sprints* > 0, resumes a previous experiment from its
    output artifacts and runs that many additional sprints.
    """

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
        team_type=config.team_type,
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

    if config.teams:
        await _run_multi_team(
            config=config,
            agents=agents,
            db=db,
            backlog=backlog,
            output_dir=output_dir,
            num_sprints=num_sprints,
            continue_sprints=continue_sprints,
        )
    else:
        await _run_single_team(
            config=config,
            agents=agents,
            db=db,
            backlog=backlog,
            output_dir=output_dir,
            num_sprints=num_sprints,
            continue_sprints=continue_sprints,
        )


async def _run_single_team(
    config: "object",
    agents: list,
    db: SharedContextDB,
    backlog: "Backlog | None",
    output_dir: str,
    num_sprints: int,
    continue_sprints: int,
) -> None:
    """Single-team experiment path (fresh or resume)."""
    sprint_mgr = SprintManager(
        agents=agents,
        shared_db=db,
        config=config,  # type: ignore[arg-type]
        output_dir=Path(output_dir),
        backlog=backlog,
    )

    if continue_sprints > 0:
        # ---- Resume path ----
        last_sprint = detect_last_sprint(output_dir)
        if last_sprint == 0:
            print("Error: nothing to continue — no completed sprints found")
            sys.exit(1)

        print(f"\nResuming from sprint {last_sprint}, running {continue_sprints} more")

        # Restore backlog progress
        if backlog:
            selected = restore_selected_story_ids(output_dir)
            backlog.mark_selected(selected)
            print(f"  Restored {len(selected)} selected story IDs")

        # Restore prior sprint results
        prior_results = restore_sprint_results(output_dir)
        sprint_mgr._sprint_results = prior_results
        print(f"  Restored {len(prior_results)} sprint result(s)")

        start = last_sprint + 1
        end = last_sprint + continue_sprints
    else:
        # ---- Fresh path ----
        start = 0 if config.sprint_zero_enabled else 1  # type: ignore[attr-defined]
        end = num_sprints

    for sprint_num in range(start, end + 1):
        _print_sprint_header(sprint_num)
        result = await sprint_mgr.run_sprint(sprint_num)

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

        review_cadence = (
            config.stakeholder_review_cadence  # type: ignore[attr-defined]
            or config.sprints_per_stakeholder_review  # type: ignore[attr-defined]
        )
        if sprint_num > 0 and sprint_num % review_cadence == 0:
            await sprint_mgr.stakeholder_review(sprint_num)

    await sprint_mgr.generate_final_report()
    print(f"\nExperiment complete. Output: {output_dir}")


async def _run_multi_team(
    config: "object",
    agents: list,
    db: SharedContextDB,
    backlog: "Backlog | None",
    output_dir: str,
    num_sprints: int,
    continue_sprints: int,
) -> None:
    """Multi-team experiment path (fresh or resume)."""
    print(f"\nMulti-team mode: {len(config.teams)} teams")  # type: ignore[attr-defined]
    for tc in config.teams:  # type: ignore[attr-defined]
        print(f"  - {tc.id}: {tc.name} ({len(tc.agent_ids)} agents)")

    message_bus = create_message_bus(
        {
            "backend": getattr(config, "messaging_backend", "asyncio"),
            "redis_url": getattr(
                config, "messaging_redis_url", "redis://localhost:6379"
            ),
            "history_size": getattr(config, "messaging_history_size", 1000),
        }
    )

    # Separate coordinator agents from team agents when coordination enabled
    coordinator_ids = set(config.coordination.coordinator_agent_ids)  # type: ignore[attr-defined]
    if coordinator_ids:
        team_agents = [a for a in agents if a.agent_id not in coordinator_ids]
        coordinators = [a for a in agents if a.agent_id in coordinator_ids]
        print(f"  Coordinators: {[c.agent_id for c in coordinators]}")
    else:
        team_agents = agents
        coordinators = []

    for agent in agents:
        agent.attach_message_bus(message_bus)

    orchestrator = MultiTeamOrchestrator(
        team_configs=config.teams,  # type: ignore[attr-defined]
        all_agents=team_agents,
        shared_db=db,
        experiment_config=config,  # type: ignore[arg-type]
        portfolio_backlog=backlog,
        message_bus=message_bus,
        output_dir=Path(output_dir),
    )
    await orchestrator.setup_teams()

    team_ids = [tc.id for tc in config.teams]  # type: ignore[attr-defined]

    if continue_sprints > 0:
        # ---- Resume path ----
        last_sprint = detect_last_sprint_multi_team(output_dir, team_ids)
        if last_sprint == 0:
            print("Error: nothing to continue — no completed sprints found")
            sys.exit(1)

        print(f"\nResuming from sprint {last_sprint}, running {continue_sprints} more")

        # Restore backlog progress
        if backlog:
            selected = restore_selected_story_ids_multi_team(output_dir, team_ids)
            backlog.mark_selected(selected)
            print(f"  Restored {len(selected)} selected story IDs")

        # Restore prior team results
        prior_team_results = restore_team_results(output_dir)
        for tid, results in prior_team_results.items():
            if tid in orchestrator._team_results:
                orchestrator._team_results[tid] = results
            # Also restore per-manager sprint results
            if tid in orchestrator._team_managers:
                orchestrator._team_managers[tid]._sprint_results = results

        total_restored = sum(len(r) for r in prior_team_results.values())
        print(f"  Restored {total_restored} team sprint result(s)")

        # Set up coordination if configured, but skip iteration zero
        if config.coordination.enabled and coordinators:  # type: ignore[attr-defined]
            await orchestrator.setup_coordination(
                coordinators, config.coordination  # type: ignore[attr-defined]
            )
            ob = config.coordination.overhead_budget  # type: ignore[attr-defined]
            total_budget_minutes = (
                config.sprint_duration_minutes  # type: ignore[attr-defined]
                * continue_sprints
                * ob.overhead_budget_pct
            )
            tracker = OverheadBudgetTracker(
                total_budget_minutes=total_budget_minutes,
                iteration_zero_share=0.0,  # skip iter-0 on resume
                step_weights={
                    "coordination": ob.coordination_step_weight,
                    "distribution": ob.distribution_step_weight,
                    "checkin": ob.checkin_step_weight,
                },
                num_sprints=continue_sprints,
                min_step_timeout_seconds=ob.min_step_timeout_seconds,
            )
            orchestrator.set_budget_tracker(tracker)

        start = last_sprint + 1
        end = last_sprint + continue_sprints
    else:
        # ---- Fresh path ----
        # Set up cross-team coordination if configured
        if config.coordination.enabled and coordinators:  # type: ignore[attr-defined]
            await orchestrator.setup_coordination(
                coordinators, config.coordination  # type: ignore[attr-defined]
            )

            ob = config.coordination.overhead_budget  # type: ignore[attr-defined]
            total_budget_minutes = (
                config.sprint_duration_minutes * num_sprints * ob.overhead_budget_pct  # type: ignore[attr-defined]
            )
            tracker = OverheadBudgetTracker(
                total_budget_minutes=total_budget_minutes,
                iteration_zero_share=ob.iteration_zero_share,
                step_weights={
                    "coordination": ob.coordination_step_weight,
                    "distribution": ob.distribution_step_weight,
                    "checkin": ob.checkin_step_weight,
                },
                num_sprints=num_sprints,
                min_step_timeout_seconds=ob.min_step_timeout_seconds,
            )
            orchestrator.set_budget_tracker(tracker)

            print(
                f"\n  Overhead budget: {total_budget_minutes:.1f} min "
                f"({ob.overhead_budget_pct:.0%} of "
                f"{config.sprint_duration_minutes * num_sprints} min)"  # type: ignore[attr-defined]
            )
            print("  Running iteration 0 (initial portfolio setup)...")
            await orchestrator.run_iteration_zero()

        start = 0 if config.sprint_zero_enabled else 1  # type: ignore[attr-defined]
        end = num_sprints

    # ---- Sprint loop (shared by fresh + resume) ----
    for sprint_num in range(start, end + 1):
        _print_sprint_header(sprint_num)

        team_results = await orchestrator.run_sprint(sprint_num)
        for team_id, result in team_results.items():
            print(
                f"  [{team_id}] velocity={result.velocity}pts "
                f"done={result.features_completed}"
            )

        review_cadence = (
            config.stakeholder_review_cadence  # type: ignore[attr-defined]
            or config.sprints_per_stakeholder_review  # type: ignore[attr-defined]
        )
        if sprint_num > 0 and sprint_num % review_cadence == 0:
            await orchestrator.stakeholder_review(sprint_num)

    await orchestrator.generate_final_report()
    print(f"\nExperiment complete (multi-team). Output: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agile agent team experiment")
    parser.add_argument("--config", default="config.yaml")

    sprint_group = parser.add_mutually_exclusive_group()
    sprint_group.add_argument(
        "--sprints",
        type=int,
        default=10,
        help="Number of sprints for a fresh experiment (default: 10)",
    )
    sprint_group.add_argument(
        "--continue",
        type=int,
        default=0,
        dest="continue_sprints",
        metavar="N",
        help="Continue a previous experiment for N additional sprints",
    )

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
            args.continue_sprints,
        )
    )


if __name__ == "__main__":
    main()
