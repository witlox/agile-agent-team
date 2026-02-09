"""Sprint lifecycle manager — orchestrates planning, execution, retro."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

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
from .disturbances import DisturbanceEngine


class SprintManager:
    """Manages the full lifecycle of each sprint."""

    def __init__(
        self,
        agents: List[BaseAgent],
        shared_db: SharedContextDB,
        config,
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
        self.workspace_manager = WorkspaceManager(workspace_root, repo_config)

        # Use CodeGenPairingEngine if agents have runtimes, else fallback to PairingEngine
        if self._agents_have_runtimes():
            self.pairing_engine = CodeGenPairingEngine(
                agents,
                self.workspace_manager,
                db=shared_db,
                kanban=self.kanban,
                config=config,
                remote_git_config={
                    'enabled': getattr(config, 'remote_git_enabled', False),
                    'provider': getattr(config, 'remote_git_provider', 'github'),
                    **getattr(config, 'remote_git_config', {})
                }
            )
        else:
            self.pairing_engine = PairingEngine(agents, db=shared_db, kanban=self.kanban)

        self.metrics = SprintMetrics()
        self._sprint_results: List[Dict] = []

        # Disturbance engine (only active when configured)
        if getattr(config, "disturbances_enabled", False):
            self.disturbance_engine: Optional[DisturbanceEngine] = DisturbanceEngine(
                frequencies=getattr(config, "disturbance_frequencies", {}),
                blast_radius_controls=getattr(config, "blast_radius_controls", {}),
            )
        else:
            self.disturbance_engine = None

    def _agent(self, role_id: str) -> Optional[BaseAgent]:
        """Find an agent by role_id."""
        return next((a for a in self.agents if a.config.role_id == role_id), None)

    def _agents_have_runtimes(self) -> bool:
        """Check if any agent has a runtime configured."""
        return any(a.runtime is not None for a in self.agents)

    async def _check_swap_triggers(self, disturbances_fired: List[str], sprint_num: int):
        """Trigger profile swaps when disturbances warrant it."""
        swap_mode = getattr(self.config, "profile_swap_mode", "none")
        if swap_mode == "none":
            return

        penalties = getattr(self.config, "profile_swap_penalties", {})
        proficiency = penalties.get("proficiency_reduction", 0.70)

        if "production_incident" in disturbances_fired:
            # Find a senior devops or networking agent to cover the incident
            specialist = self._agent("dev_sr_devops") or self._agent("dev_sr_networking")
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
                agent.decay_swap(current_sprint, knowledge_decay_sprints=int(decay_sprints))

    async def run_sprint(self, sprint_num: int):
        """Execute one complete sprint."""

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
                await self.disturbance_engine.apply(dtype, self.agents, self.kanban, self.db)
            # Check whether a production incident warrants a profile swap
            await self._check_swap_triggers(disturbances_fired, sprint_num)

        print("  Development...")
        await self.run_development(sprint_num)

        print("  QA review...")
        await self.run_qa_review(sprint_num)

        print("  Retrospective...")
        retro_data = await self.run_retrospective(sprint_num)

        print("  Meta-learning...")
        await self.apply_meta_learning(sprint_num, retro_data)

        print("  Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output, retro_data)

        # Decay swaps for the just-completed sprint
        self._decay_swaps(sprint_num)

        result = await self.metrics.calculate_sprint_results(sprint_num, self.db, self.kanban)
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
    # Phase 1: Planning
    # -------------------------------------------------------------------------

    async def run_planning(self, sprint_num: int):
        """Sprint planning — PO selects stories from backlog, team seeds Kanban."""
        po = self._agent("po")

        if self.backlog and self.backlog.remaining > 0:
            candidates = self.backlog.next_stories(5)
            candidate_text = "\n".join(
                f"- {s['id']}: {s['title']} ({s['story_points']} pts) — {s['description']}"
                for s in candidates
            )
            if po:
                prompt = (
                    f"Sprint {sprint_num} planning for {self.backlog.summary()}.\n"
                    f"Candidate stories:\n{candidate_text}\n\n"
                    "Select 3-4 stories for this sprint. "
                    "Reply with the story IDs on separate lines, e.g.:\nUS-001\nUS-002"
                )
                response = await po.generate(prompt)
                selected = self._parse_story_ids(response, candidates)
            else:
                selected = candidates[:3]

            # Return unselected candidates to pool
            selected_ids = {s["id"] for s in selected}
            for c in candidates:
                if c["id"] not in selected_ids:
                    self.backlog.mark_returned(c["id"])
        else:
            # Fallback: generic tasks when backlog is exhausted or not provided
            selected = [
                {
                    "id": f"GEN-{sprint_num:02d}-{i}",
                    "title": f"Sprint {sprint_num} Task {i}",
                    "description": f"Implement feature {i} for sprint {sprint_num}",
                    "story_points": 2,
                }
                for i in range(1, 4)
            ]

        for story in selected:
            await self.kanban.add_card(
                {
                    "title": story["title"],
                    "description": story.get("description", ""),
                    "status": "ready",
                    "story_points": story.get("story_points", 2),
                    "sprint": sprint_num,
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
        """Main development phase — pairs work on tasks until time or tasks exhausted."""
        duration = getattr(self.config, "sprint_duration_minutes", 20)
        end_time = datetime.now() + timedelta(minutes=duration)

        while datetime.now() < end_time:
            # Prune completed tasks from active_sessions
            self.pairing_engine.active_sessions = [
                t for t in self.pairing_engine.active_sessions if not t.done()
            ]

            available_pairs = self.pairing_engine.get_available_pairs()

            for pair in available_pairs:
                task = await self.kanban.pull_ready_task()
                if task:
                    # CodeGenPairingEngine requires sprint_num parameter
                    if isinstance(self.pairing_engine, CodeGenPairingEngine):
                        t = asyncio.create_task(
                            self.pairing_engine.run_pairing_session(pair, task, sprint_num)
                        )
                    else:
                        t = asyncio.create_task(
                            self.pairing_engine.run_pairing_session(pair, task)
                        )
                    self.pairing_engine.active_sessions.append(t)

            # Exit early when all work is done
            if not self.pairing_engine.active_sessions:
                snapshot = await self.kanban.get_snapshot()
                if not snapshot.get("ready"):
                    break

            await asyncio.sleep(0.1)

        await self.pairing_engine.wait_for_completion()

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
                await self._approve_pr_if_exists(card, qa, response if qa else "Auto-approved")

            new_status = "done" if approved else "in_progress"
            try:
                await self.kanban.move_card(card["id"], new_status)

                # Merge PR if moving to done and remote git enabled
                if new_status == "done" and self.config.remote_git_enabled:
                    await self._merge_pr_if_exists(card)
            except Exception:
                pass  # WIP limit may block; leave card where it is

    async def _approve_pr_if_exists(self, card: Dict, qa_agent: Optional[BaseAgent], review_comment: str):
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
            provider_config = self.config.remote_git_config.get(provider_type, {}).copy()

            # Add QA agent's metadata
            if qa_agent:
                author_name = qa_agent.config.name.split(" (")[0]
                author_email = f"{qa_agent.config.role_id}@{self.config.remote_git_config.get('author_email_domain', 'agent.local')}"
                provider_config['author_name'] = author_name
                provider_config['author_email'] = author_email

                # Handle per-agent tokens for GitLab
                if provider_type == "gitlab":
                    token_pattern = provider_config.get("token_env_pattern", "GITLAB_TOKEN_{role_id}")
                    token_env = token_pattern.replace("{role_id}", qa_agent.config.role_id)
                    provider_config['token_env'] = token_env

            # Workspace path (approximate - may need adjustment based on actual workspace structure)
            workspace = Path(self.config.tools_workspace_root) / f"sprint-{self.current_sprint if hasattr(self, 'current_sprint') else 'current'}"

            provider = create_provider(provider_type, workspace, provider_config)
            if provider:
                await provider.approve_pull_request(pr_number, review_comment[:500])  # Truncate comment

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
            provider_config = self.config.remote_git_config.get(provider_type, {}).copy()

            # Use dev lead or first available agent for merge
            merge_agent = self._agent("dev_lead") or (self.agents[0] if self.agents else None)
            if merge_agent:
                author_name = merge_agent.config.name.split(" (")[0]
                author_email = f"{merge_agent.config.role_id}@{self.config.remote_git_config.get('author_email_domain', 'agent.local')}"
                provider_config['author_name'] = author_name
                provider_config['author_email'] = author_email

                # Handle per-agent tokens for GitLab
                if provider_type == "gitlab":
                    token_pattern = provider_config.get("token_env_pattern", "GITLAB_TOKEN_{role_id}")
                    token_env = token_pattern.replace("{role_id}", merge_agent.config.role_id)
                    provider_config['token_env'] = token_env

            workspace = Path(self.config.tools_workspace_root) / f"sprint-{self.current_sprint if hasattr(self, 'current_sprint') else 'current'}"

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

    def _parse_retro_response(self, text: str):
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
