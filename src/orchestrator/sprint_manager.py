"""Sprint lifecycle manager — orchestrates planning, execution, retro."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..agents.base_agent import BaseAgent
from ..agents.pairing import PairingEngine
from ..agents.pairing_codegen import CodeGenPairingEngine
from ..codegen.workspace import WorkspaceManager
from ..tools.kanban import KanbanBoard
from ..tools.shared_context import SharedContextDB
from ..tools.agent_tools.remote_git import create_provider
from ..metrics.sprint_metrics import SprintMetrics
from ..metrics.prometheus_exporter import update_sprint_metrics
from .backlog import Backlog
from .config import ExperimentConfig
from .disturbances import DisturbanceEngine
from .sprint_zero import SprintZeroGenerator, BrownfieldAnalyzer
from .story_refinement import StoryRefinementSession
from .technical_planning import TechnicalPlanningSession
from .daily_standup import DailyStandupSession
from .sprint_review import SprintReviewSession
from .pair_rotation import PairRotationManager
from .specialist_consultant import SpecialistConsultantSystem


class SprintManager:
    """Manages the full lifecycle of each sprint."""

    def __init__(
        self,
        agents: List[BaseAgent],
        shared_db: SharedContextDB,
        config: "ExperimentConfig",
        output_dir: Path,
        backlog: Optional[Backlog] = None,
    ):
        self.agents = agents
        self.db = shared_db
        self.config = config
        self.output_dir = output_dir
        self.backlog = backlog
        self.kanban = KanbanBoard(
            shared_db,
            wip_limits=getattr(config, "wip_limits", {"in_progress": 4, "review": 2}),
        )

        # Setup workspace manager for code generation
        workspace_root = getattr(config, "tools_workspace_root", "/tmp/agent-workspace")
        repo_config = getattr(config, "repo_config", None)
        workspace_mode = getattr(config, "workspace_mode", "per_story")
        # Disturbance engine (only active when configured) - init before workspace manager
        if getattr(config, "disturbances_enabled", False):
            self.disturbance_engine: Optional[DisturbanceEngine] = DisturbanceEngine(
                frequencies=getattr(config, "disturbance_frequencies", {}),
                blast_radius_controls=getattr(config, "blast_radius_controls", {}),
            )
        else:
            self.disturbance_engine = None

        self.workspace_manager = WorkspaceManager(
            workspace_root,
            repo_config,
            workspace_mode,
            disturbance_engine=self.disturbance_engine,
            kanban=self.kanban,
            db=shared_db,
        )

        # Use CodeGenPairingEngine if agents have runtimes, else fallback to PairingEngine
        if self._agents_have_runtimes():
            self.pairing_engine = CodeGenPairingEngine(
                agents,
                self.workspace_manager,
                db=shared_db,
                kanban=self.kanban,
                config=config,
                remote_git_config={
                    "enabled": getattr(config, "remote_git_enabled", False),
                    "provider": getattr(config, "remote_git_provider", "github"),
                    **getattr(config, "remote_git_config", {}),
                },
                disturbance_engine=self.disturbance_engine,
            )
        else:
            self.pairing_engine = PairingEngine(
                agents, db=shared_db, kanban=self.kanban
            )

        self.metrics = SprintMetrics()
        self._sprint_results: List[Dict] = []

        # Agile ceremony managers
        po = self._agent("po")
        dev_lead = self._agent("dev_lead") or self._agent("lead")
        qa_lead = self._agent("qa_lead")

        self.story_refinement = StoryRefinementSession(po, agents, dev_lead)
        self.technical_planning = TechnicalPlanningSession(
            [
                a
                for a in agents
                if hasattr(a.config, "role_archetype")
                and "developer" in a.config.role_archetype
            ],
            dev_lead,
            qa_lead,
        )
        self.daily_standup = DailyStandupSession(dev_lead, qa_lead, shared_db)
        self.sprint_review = SprintReviewSession(
            po, dev_lead, qa_lead, self.kanban, shared_db
        )
        self.pair_rotation_manager = PairRotationManager()

        # Specialist consultant system
        team_config_dir = Path(__file__).parent.parent.parent / "team_config"
        self.specialist_consultant = SpecialistConsultantSystem(
            team_config_dir=str(team_config_dir),
            db=shared_db,
            max_per_sprint=getattr(config, "max_specialist_consultations", 3),
            velocity_penalty_per_consultation=getattr(
                config, "specialist_velocity_penalty", 2.0
            ),
        )

    def _agent(self, role_id: str) -> Optional[BaseAgent]:
        """Find an agent by role_id."""
        return next((a for a in self.agents if a.config.role_id == role_id), None)

    def _agents_have_runtimes(self) -> bool:
        """Check if any agent has a runtime configured."""
        return any(a.runtime is not None for a in self.agents)

    async def _check_swap_triggers(
        self, disturbances_fired: List[str], sprint_num: int
    ):
        """Trigger profile swaps when disturbances warrant it."""
        swap_mode = getattr(self.config, "profile_swap_mode", "none")
        if swap_mode == "none":
            return

        penalties = getattr(self.config, "profile_swap_penalties", {})
        proficiency = penalties.get("proficiency_reduction", 0.70)

        if "production_incident" in disturbances_fired:
            # Find a senior devops or networking agent to cover the incident
            specialist = self._agent("dev_sr_devops") or self._agent(
                "dev_sr_networking"
            )
            if specialist and not specialist.is_swapped:
                specialist.swap_to(
                    target_role_id="incident_responder",
                    domain="production incident response",
                    proficiency=proficiency,
                    sprint=sprint_num,
                )
                print(f"  [SWAP] {specialist.config.role_id} → incident responder")

    def _decay_swaps(self, current_sprint: int):
        """Apply swap decay for all agents after sprint completes."""
        decay_sprints = getattr(self.config, "profile_swap_penalties", {}).get(
            "knowledge_decay_sprints", 1
        )
        for agent in self.agents:
            if agent.is_swapped:
                agent.decay_swap(
                    current_sprint, knowledge_decay_sprints=int(decay_sprints)
                )

    async def run_sprint(self, sprint_num: int):
        """Execute one complete sprint."""

        # Special handling for Sprint 0 (infrastructure setup)
        if sprint_num == 0:
            return await self._run_sprint_zero()

        sprint_output = self.output_dir / f"sprint-{sprint_num:02d}"
        sprint_output.mkdir(parents=True, exist_ok=True)

        print("  Planning...")
        await self.run_planning(sprint_num)

        # Disturbances fire after planning, before development
        disturbances_fired: List[str] = []
        if self.disturbance_engine is not None:
            disturbances_fired = self.disturbance_engine.roll_for_sprint(sprint_num)
            for dtype in disturbances_fired:
                print(f"  [DISTURBANCE] {dtype}")
                await self.disturbance_engine.apply(
                    dtype, self.agents, self.kanban, self.db
                )
            # Check whether a production incident warrants a profile swap
            await self._check_swap_triggers(disturbances_fired, sprint_num)

        print("  Development...")
        await self.run_development(sprint_num)

        print("  QA review...")
        await self.run_qa_review(sprint_num)

        print("  Sprint Review/Demo...")
        completed_cards = await self.kanban.get_cards_by_status("done")
        completed_stories = [
            c for c in completed_cards if c.get("sprint") == sprint_num
        ]
        _review_outcome = await self.sprint_review.run_review(
            sprint_num, completed_stories
        )

        print("  Retrospective...")
        retro_data = await self.run_retrospective(sprint_num)

        print("  Meta-learning...")
        await self.apply_meta_learning(sprint_num, retro_data)

        print("  Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output, retro_data)

        # Decay swaps for the just-completed sprint
        self._decay_swaps(sprint_num)

        result = await self.metrics.calculate_sprint_results(
            sprint_num, self.db, self.kanban
        )
        self._sprint_results.append(
            {
                "sprint": sprint_num,
                "velocity": result.velocity,
                "features_completed": result.features_completed,
                "test_coverage": result.test_coverage,
                "pairing_sessions": result.pairing_sessions,
                "cycle_time_avg": result.cycle_time_avg,
                "disturbances": disturbances_fired,
            }
        )

        # Update Prometheus metrics
        try:
            sessions = await self.db.get_pairing_sessions_for_sprint(sprint_num)
            update_sprint_metrics(result, session_details=sessions)
        except Exception:
            pass  # metrics server may not be running in all environments

        return result

    # -------------------------------------------------------------------------
    # Sprint 0: Infrastructure Setup
    # -------------------------------------------------------------------------

    async def _run_sprint_zero(self):
        """Run Sprint 0 - infrastructure setup.

        Flow:
        1. Planning: Generate/select infrastructure stories
        2. Development: Agents create config files (normal pairing)
        3. QA: Validate configs are syntactically correct
        4. CI Validation: Actually run CI pipeline validation
        5. Retrospective: Discuss infrastructure decisions
        """
        sprint_num = 0

        sprint_output = self.output_dir / f"sprint-{sprint_num:02d}"
        sprint_output.mkdir(parents=True, exist_ok=True)

        print("  Planning (Sprint 0)...")
        await self._run_planning_sprint_zero()

        # Skip disturbances for Sprint 0 (not relevant for infrastructure)

        print("  Development...")
        await self.run_development(sprint_num)

        print("  QA review...")
        await self.run_qa_review(sprint_num)

        print("  CI Validation...")
        ci_passed = await self._validate_ci_pipeline()

        print("  Retrospective...")
        retro_data = await self.run_retrospective(sprint_num)

        print("  Meta-learning...")
        await self.apply_meta_learning(sprint_num, retro_data)

        print("  Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output, retro_data)

        result = await self.metrics.calculate_sprint_results(
            sprint_num, self.db, self.kanban
        )

        # Add CI validation status to result
        result.ci_validated = ci_passed

        self._sprint_results.append(
            {
                "sprint": sprint_num,
                "velocity": result.velocity,
                "features_completed": result.features_completed,
                "test_coverage": result.test_coverage,
                "pairing_sessions": result.pairing_sessions,
                "cycle_time_avg": result.cycle_time_avg,
                "ci_validated": ci_passed,
                "status": "complete" if ci_passed else "incomplete",
            }
        )

        # Update Prometheus metrics
        try:
            sessions = await self.db.get_pairing_sessions_for_sprint(sprint_num)
            update_sprint_metrics(result, session_details=sessions)
        except Exception:
            pass

        return result

    async def _run_planning_sprint_zero(self):
        """Sprint 0 planning: Generate/select infrastructure stories."""
        if not self.backlog:
            print("    No backlog configured, skipping Sprint 0")
            return

        # Get product metadata from backlog
        product_meta = self.backlog.get_product_metadata()

        # Check if stakeholder provided explicit Sprint 0 stories
        backlog_sprint_zero_stories = [
            s for s in self.backlog.data.get("stories", []) if s.get("sprint") == 0
        ]

        if backlog_sprint_zero_stories:
            # Use explicitly provided Sprint 0 stories
            stories_to_use = backlog_sprint_zero_stories
            print(f"    Using {len(stories_to_use)} Sprint 0 stories from backlog")
        else:
            # Generate infrastructure stories
            print(
                f"    Generating infrastructure stories for: {', '.join(product_meta.languages)}"
            )

            # Detect project type and generate stories
            if (
                product_meta.repository_type == "brownfield"
                and product_meta.repository_url
            ):
                # Brownfield: Clone repo, analyze gaps
                workspace = self.workspace_manager.create_sprint_workspace(
                    0, "analysis"
                )
                analyzer = BrownfieldAnalyzer(workspace)
                analysis = analyzer.analyze()

                print(
                    f"    Brownfield analysis: {sum(analysis.values())}/{len(analysis)} components exist"
                )

                # Generate stories for missing pieces
                generator = SprintZeroGenerator(product_meta, {})
                all_stories = generator.generate_stories()
                infrastructure_stories = analyzer.generate_gap_stories(
                    analysis, all_stories
                )
            else:
                # Greenfield: Generate all infrastructure stories
                generator = SprintZeroGenerator(product_meta, {})
                infrastructure_stories = generator.generate_stories()

            # Convert to backlog format
            stories_to_use = [
                generator.convert_to_backlog_format(s) for s in infrastructure_stories
            ]
            print(f"    Generated {len(stories_to_use)} infrastructure stories")

        # Add stories to Kanban as "ready"
        for story in stories_to_use:
            card_data = {
                "title": story["title"],
                "description": story["description"],
                "status": "ready",
                "story_points": story.get("story_points", 3),
                "sprint": 0,
            }
            # Store infrastructure metadata if present
            if "_infrastructure" in story:
                card_data["metadata"] = story["_infrastructure"]

            _card_id = await self.kanban.add_card(card_data)

        print(f"    Added {len(stories_to_use)} stories to Sprint 0 backlog")

    async def _validate_ci_pipeline(self) -> bool:
        """Validate that CI pipeline actually works.

        Returns:
            True if CI runs successfully, False otherwise.
        """
        # Get Sprint 0 workspace
        workspace = self.workspace_manager.base_dir / "sprint-0"
        if not workspace.exists():
            print("    No Sprint 0 workspace found")
            return True  # OK if no workspace created yet

        # Check for CI config
        gh_actions = workspace / ".github" / "workflows"
        gitlab_ci = workspace / ".gitlab-ci.yml"

        if gh_actions.exists():
            # Validate GitHub Actions workflow syntax
            import subprocess

            try:
                result = subprocess.run(
                    ["gh", "workflow", "list"],
                    cwd=workspace,
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    print("    ✓ GitHub Actions workflow validated")
                    return True
                else:
                    print(
                        f"    ✗ GitHub Actions validation failed: {result.stderr.decode()}"
                    )
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(
                    f"    ⚠ Cannot validate GitHub Actions (gh CLI not available): {e}"
                )
                # If gh CLI not available, just check file exists
                return True

        elif gitlab_ci.exists():
            # For GitLab CI, just check file exists and is valid YAML
            import yaml

            try:
                with open(gitlab_ci) as f:
                    yaml.safe_load(f)
                print("    ✓ GitLab CI configuration validated")
                return True
            except yaml.YAMLError as e:
                print(f"    ✗ GitLab CI validation failed: {e}")
                return False

        # No CI configured - check if it was expected
        product_meta = self.backlog.get_product_metadata() if self.backlog else None
        if product_meta and (
            "github-actions" in product_meta.tech_stack
            or "gitlab-ci" in product_meta.tech_stack
        ):
            print("    ✗ CI pipeline expected but not found")
            return False

        # No CI required
        print("    ⊘ No CI pipeline required")
        return True

    # -------------------------------------------------------------------------
    # Phase 1: Planning
    # -------------------------------------------------------------------------

    async def run_planning(self, sprint_num: int):
        """Sprint planning — 2-phase process: Story refinement + Technical planning."""

        # Get candidate stories from backlog
        if self.backlog and self.backlog.remaining > 0:
            candidates = self.backlog.next_stories(
                8
            )  # Get more candidates for refinement
        else:
            # Fallback: generic tasks
            candidates = [
                {
                    "id": f"GEN-{sprint_num:02d}-{i}",
                    "title": f"Sprint {sprint_num} Task {i}",
                    "description": f"Implement feature {i} for sprint {sprint_num}",
                    "story_points": 3,
                    "acceptance_criteria": ["Feature works as described"],
                }
                for i in range(1, 4)
            ]

        # Calculate team capacity (developers only, half team = max concurrent tasks)
        num_developers = len(
            [
                a
                for a in self.agents
                if hasattr(a.config, "role_archetype")
                and "developer" in a.config.role_archetype
            ]
        )
        team_capacity = num_developers * 3  # ~3 story points per developer per sprint

        # Phase 1: Story Refinement (PO + Team)
        refined_stories = await self.story_refinement.refine_stories(
            candidates, sprint_num, team_capacity
        )

        # Return unselected candidates to backlog pool
        if self.backlog:
            selected_ids = {s.id for s in refined_stories}
            for c in candidates:
                if c["id"] not in selected_ids:
                    self.backlog.mark_returned(c["id"])

        # Phase 2: Technical Planning (Team only)
        tasks, dependency_graph = await self.technical_planning.plan_implementation(
            refined_stories, sprint_num
        )

        # Add tasks to Kanban with dependencies and initial pairs
        for task in tasks:
            await self.kanban.add_card(
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": "ready",
                    "story_points": task.estimated_hours
                    // 8,  # Convert hours to story points
                    "sprint": sprint_num,
                    "story_id": task.story_id,
                    "owner": task.owner,
                    "initial_navigator": task.initial_navigator,
                    "depends_on": task.depends_on,
                }
            )

    def _parse_story_ids(self, response: str, candidates: List[Dict]) -> List[Dict]:
        """Extract story IDs from PO response; fall back to first 3 candidates."""
        found_ids = re.findall(r"US-\d+", response.upper())
        id_map = {s["id"]: s for s in candidates}
        selected = [id_map[sid] for sid in found_ids if sid in id_map]
        return selected if selected else candidates[:3]

    # -------------------------------------------------------------------------
    # Phase 2: Development
    # -------------------------------------------------------------------------

    async def run_development(self, sprint_num: int):
        """Development phase with daily standups and pair rotation.

        Wall-clock duration (default 60 min) = 10 simulated days (2 weeks).
        Each day: standup (except Day 1) + pairing sessions + rotation prep.
        At 60 min each simulated day gets ~6 min of wall-clock, enough for
        ~160 code-generation LLM calls across up to 4 parallel pairs.
        """
        duration = getattr(self.config, "sprint_duration_minutes", 60)
        num_days = 10  # 2-week sprint = 10 working days
        time_per_day = duration / num_days  # ~6 minutes per day

        # Get initial task assignments and pairs
        snapshot = await self.kanban.get_snapshot()
        in_progress_tasks = snapshot.get("in_progress", [])

        # Extract task owners and available partners
        task_owners = [t.get("owner") for t in in_progress_tasks if t.get("owner")]
        all_developers = [
            a.agent_id
            for a in self.agents
            if hasattr(a.config, "role_archetype")
            and "developer" in a.config.role_archetype
        ]
        all_testers = [
            a.agent_id
            for a in self.agents
            if hasattr(a.config, "role_archetype")
            and "tester" in a.config.role_archetype
        ]
        all_partners = all_developers + all_testers

        # Track current day's pairs
        current_pairs = {}  # owner_id -> navigator_id

        for day_num in range(1, num_days + 1):
            print(f"\n  === Day {day_num} of {num_days} ===")
            day_start = datetime.now()
            day_end = day_start + timedelta(minutes=time_per_day)

            # Morning standup (except Day 1)
            if day_num > 1:
                active_pair_tuples = [(o, n) for o, n in current_pairs.items()]
                await self.daily_standup.run_standup(
                    sprint_num, day_num, active_pair_tuples, in_progress_tasks
                )

            # Get today's pair assignments (Day 1 uses initial, others rotate)
            if day_num == 1:
                # Use initial pairs from planning
                for task in in_progress_tasks:
                    owner = task.get("owner")
                    navigator = task.get("initial_navigator")
                    if owner and navigator:
                        current_pairs[owner] = navigator
            else:
                # Rotate pairs
                if task_owners and all_partners:
                    current_pairs = self.pair_rotation_manager.get_rotation_for_day(
                        day_num, task_owners, all_partners, sprint_num
                    )

            print(f"  Pairs today: {len(current_pairs)}")

            # Run pairing sessions for the day
            await self._run_day_pairing_sessions(
                sprint_num, day_num, current_pairs, day_end
            )

            # Update in-progress tasks for next day
            snapshot = await self.kanban.get_snapshot()
            in_progress_tasks = snapshot.get("in_progress", [])
            task_owners = [t.get("owner") for t in in_progress_tasks if t.get("owner")]

            # Exit early if no more work
            if not in_progress_tasks and not snapshot.get("ready"):
                print(f"  All work complete on Day {day_num}")
                break

        await self.pairing_engine.wait_for_completion()

    async def _run_day_pairing_sessions(
        self,
        sprint_num: int,
        day_num: int,
        pairs: Dict[str, str],  # owner_id -> navigator_id
        day_end: datetime,
    ):
        """Run pairing sessions for one day."""

        while datetime.now() < day_end:
            # Prune completed tasks
            self.pairing_engine.active_sessions = [
                t for t in self.pairing_engine.active_sessions if not t.done()
            ]

            # Get available pairs (match against today's rotation)
            available_pairs = self.pairing_engine.get_available_pairs()

            for owner, navigator in pairs.items():
                # Find agents for this pair
                owner_agent = next(
                    (a for a in self.agents if a.agent_id == owner), None
                )
                navigator_agent = next(
                    (a for a in self.agents if a.agent_id == navigator), None
                )

                if not owner_agent or not navigator_agent:
                    continue

                pair = (owner_agent, navigator_agent)

                # Check if this pair is available
                if pair not in available_pairs:
                    continue

                # Pull task assigned to this owner (respect dependencies)
                task = await self._pull_task_for_owner(owner)
                if task:
                    # Run pairing session
                    if isinstance(self.pairing_engine, CodeGenPairingEngine):
                        t = asyncio.create_task(
                            self.pairing_engine.run_pairing_session(
                                pair, task, sprint_num
                            )
                        )
                    else:
                        t = asyncio.create_task(
                            self.pairing_engine.run_pairing_session(pair, task)
                        )
                    self.pairing_engine.active_sessions.append(t)

            # Exit if no active work
            if not self.pairing_engine.active_sessions:
                snapshot = await self.kanban.get_snapshot()
                if not snapshot.get("ready") and not snapshot.get("in_progress"):
                    break

            await asyncio.sleep(0.1)

    async def _pull_task_for_owner(self, owner_id: str) -> Optional[Dict]:
        """Pull a ready task assigned to specific owner, respecting dependencies."""
        snapshot = await self.kanban.get_snapshot()
        ready_tasks = snapshot.get("ready", [])

        for task in ready_tasks:
            if task.get("owner") != owner_id:
                continue

            # Check dependencies
            depends_on = task.get("depends_on", [])
            if depends_on:
                # Check if all dependencies are done
                done_tasks = snapshot.get("done", [])
                done_ids = {t.get("id") for t in done_tasks}

                if not all(dep_id in done_ids for dep_id in depends_on):
                    # Task is blocked by dependencies
                    continue

            # Task is ready and belongs to this owner
            return await self.kanban.pull_ready_task()

        return None

    # -------------------------------------------------------------------------
    # Phase 3: QA review gate
    # -------------------------------------------------------------------------

    async def run_qa_review(self, sprint_num: int):
        """QA lead reviews each card in 'review'; approved → done, rejected → in_progress."""
        qa = self._agent("qa_lead")
        snapshot = await self.kanban.get_snapshot()
        review_cards = snapshot.get("review", [])

        for card in review_cards:
            if qa:
                prompt = (
                    f"QA review for: {card['title']}\n"
                    f"Description: {card.get('description', '')}\n"
                    "Does this meet the Definition of Done? "
                    "Reply 'approve' or 'reject' with brief reasoning."
                )
                response = await qa.generate(prompt)
                approved = "approve" in response.lower()
            else:
                approved = True  # auto-approve if no QA agent

            # Approve PR if remote git enabled and card approved
            if approved and self.config.remote_git_enabled:
                await self._approve_pr_if_exists(
                    card, qa, response if qa else "Auto-approved"
                )

            new_status = "done" if approved else "in_progress"
            try:
                await self.kanban.move_card(card["id"], new_status)

                # Merge PR if moving to done and remote git enabled
                if new_status == "done" and self.config.remote_git_enabled:
                    await self._merge_pr_if_exists(card)
            except Exception:
                pass  # WIP limit may block; leave card where it is

    async def _approve_pr_if_exists(
        self, card: Dict, qa_agent: Optional[BaseAgent], review_comment: str
    ):
        """Approve PR/MR if it exists in card metadata."""
        try:
            # Extract PR URL from metadata
            metadata = card.get("metadata")
            if not metadata:
                return

            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            pr_url = metadata.get("pr_url")
            if not pr_url:
                return

            # Extract PR number from URL
            pr_number = None
            if "/pull/" in pr_url:  # GitHub
                pr_number = int(pr_url.split("/pull/")[-1].split("/")[0])
            elif "!" in pr_url:  # GitLab MR
                pr_number = int(pr_url.split("!")[-1].split("/")[0])

            if not pr_number:
                return

            # Create provider and approve
            provider_type = self.config.remote_git_provider
            provider_config = self.config.remote_git_config.get(
                provider_type, {}
            ).copy()

            # Add QA agent's metadata
            if qa_agent:
                author_name = qa_agent.config.name.split(" (")[0]
                author_email = f"{qa_agent.config.role_id}@{self.config.remote_git_config.get('author_email_domain', 'agent.local')}"
                provider_config["author_name"] = author_name
                provider_config["author_email"] = author_email

                # Handle per-agent tokens for GitLab
                if provider_type == "gitlab":
                    token_pattern = provider_config.get(
                        "token_env_pattern", "GITLAB_TOKEN_{role_id}"
                    )
                    token_env = token_pattern.replace(
                        "{role_id}", qa_agent.config.role_id
                    )
                    provider_config["token_env"] = token_env

            # Workspace path (approximate - may need adjustment based on actual workspace structure)
            workspace = (
                Path(self.config.tools_workspace_root)
                / f"sprint-{self.current_sprint if hasattr(self, 'current_sprint') else 'current'}"
            )

            provider = create_provider(provider_type, workspace, provider_config)
            if provider:
                await provider.approve_pull_request(
                    pr_number, review_comment[:500]
                )  # Truncate comment

        except Exception:
            # Don't fail QA review if PR approval fails
            pass

    async def _merge_pr_if_exists(self, card: Dict):
        """Merge PR/MR if it exists in card metadata."""
        try:
            # Extract PR URL from metadata
            metadata = card.get("metadata")
            if not metadata:
                return

            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            pr_url = metadata.get("pr_url")
            if not pr_url:
                return

            # Extract PR number
            pr_number = None
            if "/pull/" in pr_url:  # GitHub
                pr_number = int(pr_url.split("/pull/")[-1].split("/")[0])
            elif "!" in pr_url:  # GitLab MR
                pr_number = int(pr_url.split("!")[-1].split("/")[0])

            if not pr_number:
                return

            # Create provider and merge
            provider_type = self.config.remote_git_provider
            provider_config = self.config.remote_git_config.get(
                provider_type, {}
            ).copy()

            # Use dev lead or first available agent for merge
            merge_agent = self._agent("dev_lead") or (
                self.agents[0] if self.agents else None
            )
            if merge_agent:
                author_name = merge_agent.config.name.split(" (")[0]
                author_email = f"{merge_agent.config.role_id}@{self.config.remote_git_config.get('author_email_domain', 'agent.local')}"
                provider_config["author_name"] = author_name
                provider_config["author_email"] = author_email

                # Handle per-agent tokens for GitLab
                if provider_type == "gitlab":
                    token_pattern = provider_config.get(
                        "token_env_pattern", "GITLAB_TOKEN_{role_id}"
                    )
                    token_env = token_pattern.replace(
                        "{role_id}", merge_agent.config.role_id
                    )
                    provider_config["token_env"] = token_env

            workspace = (
                Path(self.config.tools_workspace_root)
                / f"sprint-{self.current_sprint if hasattr(self, 'current_sprint') else 'current'}"
            )

            provider = create_provider(provider_type, workspace, provider_config)
            if provider:
                merge_method = provider_config.get("merge_method", "squash")
                await provider.merge_pull_request(pr_number, merge_method)

        except Exception:
            # Don't fail card transition if PR merge fails
            pass

    # -------------------------------------------------------------------------
    # Phase 4: Retrospective
    # -------------------------------------------------------------------------

    async def run_retrospective(self, sprint_num: int) -> Dict:
        """Structured Keep/Drop/Puzzle retro with all agents."""
        retro: Dict = {"sprint": sprint_num, "keep": [], "drop": [], "puzzle": []}

        prompt = (
            f"Sprint {sprint_num} retrospective.\n"
            "Reply in exactly this format (one item each):\n"
            "KEEP: <what went well>\n"
            "DROP: <what to stop doing>\n"
            "PUZZLE: <open question or challenge>"
        )

        for agent in self.agents:
            response = await agent.generate(prompt)
            keep, drop, puzzle = self._parse_retro_response(response)
            if keep:
                retro["keep"].append({"agent": agent.config.role_id, "text": keep})
            if drop:
                retro["drop"].append({"agent": agent.config.role_id, "text": drop})
            if puzzle:
                retro["puzzle"].append({"agent": agent.config.role_id, "text": puzzle})

        return retro

    def _parse_retro_response(self, text: str) -> Tuple[str, str, str]:
        """Extract KEEP / DROP / PUZZLE from agent response."""
        keep = drop = puzzle = ""
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("KEEP:"):
                keep = line[5:].strip()
            elif line.upper().startswith("DROP:"):
                drop = line[5:].strip()
            elif line.upper().startswith("PUZZLE:"):
                puzzle = line[7:].strip()
        # Fallback: if format not followed, use whole response as keep
        if not keep and not drop and not puzzle:
            keep = text.strip()
        return keep, drop, puzzle

    # -------------------------------------------------------------------------
    # Phase 5: Meta-learning
    # -------------------------------------------------------------------------

    async def apply_meta_learning(self, sprint_num: int, retro: Dict):
        """Store retro learnings in JSONL and reload agent prompts.

        Meta-learnings are stored in 07_meta/meta_learnings.jsonl and dynamically
        loaded at prompt composition time, so they don't pollute the base profile files.
        """
        team_config = Path(self.config.team_config_dir)
        jsonl_path = team_config / "07_meta" / "meta_learnings.jsonl"

        # Ensure directory exists
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        # Process all retrospective items (keep, drop, puzzle)
        learning_types = {
            "keep": retro.get("keep", []),
            "drop": retro.get("drop", []),
            "puzzle": retro.get("puzzle", []),
        }

        learnings_added = False
        for learning_type, items in learning_types.items():
            for item in items:
                agent_id = item.get("agent", "")
                learning_text = item.get("text", "").strip()

                if not agent_id or not learning_text:
                    continue

                # Store learning in JSONL
                entry = {
                    "sprint": sprint_num,
                    "agent_id": agent_id,
                    "learning_type": learning_type,
                    "content": {"text": learning_text},
                    "applied": True,
                }
                with open(jsonl_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")

                learnings_added = True

        # Reload prompts for all agents so next sprint sees the new learnings
        if learnings_added:
            for agent in self.agents:
                agent.prompt = agent._load_prompt()

    # -------------------------------------------------------------------------
    # Phase 6: Artifacts
    # -------------------------------------------------------------------------

    async def generate_sprint_artifacts(
        self, sprint_num: int, output_path: Path, retro_data: Dict
    ):
        """Write sprint artifacts to disk."""

        # 1. Kanban snapshot
        kanban_data = await self.kanban.get_snapshot()
        (output_path / "kanban.json").write_text(json.dumps(kanban_data, indent=2))
        await self.db.save_kanban_snapshot(sprint_num, kanban_data)

        # 2. Pairing log
        sessions = await self.db.get_pairing_sessions_for_sprint(sprint_num)
        (output_path / "pairing_log.json").write_text(json.dumps(sessions, indent=2))

        # 3. Retro notes (Markdown)
        retro_md = self._format_retro_md(sprint_num, retro_data)
        (output_path / "retro.md").write_text(retro_md)

    def _format_retro_md(self, sprint_num: int, retro: Dict) -> str:
        """Format retro data as Markdown (Keep/Drop/Puzzle)."""
        lines = [f"# Sprint {sprint_num} Retrospective\n"]

        lines.append("## Keep\n")
        for item in retro.get("keep", []):
            lines.append(f"- **{item['agent']}**: {item['text']}")

        lines.append("\n## Drop\n")
        for item in retro.get("drop", []):
            lines.append(f"- **{item['agent']}**: {item['text']}")

        lines.append("\n## Puzzle\n")
        for item in retro.get("puzzle", []):
            lines.append(f"- **{item['agent']}**: {item['text']}")

        return "\n".join(lines) + "\n"

    # -------------------------------------------------------------------------
    # Stakeholder review (every N sprints)
    # -------------------------------------------------------------------------

    async def stakeholder_review(self, sprint_num: int):
        """PO + dev_lead review completed stories; PO accepts or rejects."""
        print(f"\n  STAKEHOLDER REVIEW (Sprint {sprint_num})")

        if self._sprint_results:
            velocities = [r["velocity"] for r in self._sprint_results]
            avg_velocity = sum(velocities) / len(velocities)
            print(f"  Average velocity: {avg_velocity:.1f} pts/sprint")
            print(f"  Sprints completed: {len(self._sprint_results)}")

        # PO reviews done cards
        po = self._agent("po")
        if po:
            snapshot = await self.kanban.get_snapshot()
            done_cards = snapshot.get("done", [])
            if done_cards:
                titles = "\n".join(f"- {c['title']}" for c in done_cards)
                response = await po.generate(
                    f"Stakeholder review after sprint {sprint_num}.\n"
                    f"Completed stories:\n{titles}\n\n"
                    "Provide brief acceptance feedback."
                )
                print(f"  PO feedback: {response[:200]}")

    # -------------------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------------------

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
            report["total_features"] = sum(
                r["features_completed"] for r in self._sprint_results
            )

        report_path = self.output_dir / "final_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nFinal report: {report_path}")
