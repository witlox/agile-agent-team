"""Enhanced pairing engine with real code generation.

This module extends the base pairing engine to generate actual code using:
- BDD/Gherkin feature files
- Real file operations via agent runtimes
- Test execution and iteration
- Git commits

Workflow:
1. Generate BDD feature file from story
2. Driver implements code using execute_coding_task()
3. Run tests
4. Iterate on failures
5. Commit working code
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_agent import BaseAgent
from ..codegen import WorkspaceManager, BDDGenerator
from ..tools.agent_tools.remote_git import create_provider, PullRequestConfig


class CodeGenPairingEngine:
    """Pairing engine that generates real code with role-based pairing."""

    def __init__(
        self,
        agents: List[BaseAgent],
        workspace_manager: WorkspaceManager,
        db=None,
        kanban=None,
        config=None,
        remote_git_config=None
    ):
        self.agents = agents
        self.workspace_manager = workspace_manager
        self.bdd_generator = BDDGenerator()
        self.active_sessions: List[asyncio.Task] = []
        self._busy_agents: set = set()
        self.db = db
        self.kanban = kanban
        self.config = config
        self.remote_git_config = remote_git_config or {}

    def _is_lead_dev(self, agent: BaseAgent) -> bool:
        """Check if agent is the development lead."""
        return "dev_lead" in agent.config.role_id or "lead" in agent.config.role_archetype

    def _is_tester(self, agent: BaseAgent) -> bool:
        """Check if agent is a tester."""
        return "tester" in agent.config.role_archetype or "qa" in agent.config.role_id

    def _assign_roles(self, agent1: BaseAgent, agent2: BaseAgent) -> Tuple[BaseAgent, BaseAgent]:
        """Assign driver and navigator roles based on team culture.

        Rules:
        1. Lead dev is always navigator (teaching role)
        2. Testers are always navigator when pairing with devs
        3. Otherwise, senior navigates with junior
        4. Same level: random assignment

        Returns:
            (driver, navigator) tuple
        """
        import random

        # Rule 1: Lead dev always navigates
        if self._is_lead_dev(agent1):
            return (agent2, agent1)  # agent2 drives, agent1 (lead dev) navigates
        if self._is_lead_dev(agent2):
            return (agent1, agent2)  # agent1 drives, agent2 (lead dev) navigates

        # Rule 2: Tester always navigates when pairing with dev
        if self._is_tester(agent1) and not self._is_tester(agent2):
            return (agent2, agent1)  # dev drives, tester navigates
        if self._is_tester(agent2) and not self._is_tester(agent1):
            return (agent1, agent2)  # dev drives, tester navigates

        # Rule 3: Senior navigates with junior (teaching)
        seniority_order = {"senior": 3, "mid": 2, "junior": 1}
        agent1_seniority = seniority_order.get(getattr(agent1.config, "seniority", "mid"), 2)
        agent2_seniority = seniority_order.get(getattr(agent2.config, "seniority", "mid"), 2)

        if agent1_seniority > agent2_seniority:
            # agent1 is more senior, navigates
            return (agent2, agent1)
        elif agent2_seniority > agent1_seniority:
            # agent2 is more senior, navigates
            return (agent1, agent2)

        # Rule 4: Same level, random assignment
        if random.random() < 0.5:
            return (agent1, agent2)
        else:
            return (agent2, agent1)

    def get_available_pairs(self) -> List[Tuple[BaseAgent, BaseAgent]]:
        """Find agents available for pairing with role-based assignment.

        Returns pairs as (driver, navigator) tuples respecting team culture:
        - Lead dev always navigates
        - Testers always navigate when pairing with devs
        - Seniors navigate with juniors
        """
        available = [a for a in self.agents if a.config.role_id not in self._busy_agents]

        # Separate developers and testers
        developers = [a for a in available if not self._is_tester(a)]
        testers = [a for a in available if self._is_tester(a)]

        pairs: List[Tuple[BaseAgent, BaseAgent]] = []

        # Pair testers with developers if tester pairing enabled
        tester_pairing_enabled = getattr(self.config, "tester_pairing_enabled", True) if self.config else True
        tester_pairing_frequency = getattr(self.config, "tester_pairing_frequency", 0.20) if self.config else 0.20

        if tester_pairing_enabled and testers and developers:
            import random
            # 20% of pairs include a tester (configurable)
            if random.random() < tester_pairing_frequency and len(developers) > 0:
                tester = testers.pop(0)
                dev = developers.pop(0)
                driver, navigator = self._assign_roles(dev, tester)
                pairs.append((driver, navigator))

        # Pair remaining developers
        for i in range(0, len(developers) - 1, 2):
            driver, navigator = self._assign_roles(developers[i], developers[i + 1])
            pairs.append((driver, navigator))

        return pairs

    async def run_pairing_session(
        self,
        pair: Tuple[BaseAgent, BaseAgent],
        task: Dict,
        sprint_num: int
    ) -> Dict:
        """Execute pairing session with real code generation.

        Workflow:
        1. Setup workspace for this story
        2. Generate BDD feature file
        3. Driver implements code via runtime
        4. Navigator reviews implementation
        5. Run tests and iterate on failures
        6. Commit working code
        7. Update Kanban

        Args:
            pair: (driver, navigator) agents
            task: Story/task dict with id, title, description, acceptance_criteria
            sprint_num: Current sprint number

        Returns:
            Session result dict
        """
        driver, navigator = pair
        self._busy_agents.add(driver.config.role_id)
        self._busy_agents.add(navigator.config.role_id)

        start_time = datetime.utcnow()
        session_result: Dict = {
            "sprint": sprint_num,
            "driver_id": driver.config.role_id,
            "navigator_id": navigator.config.role_id,
            "task_id": task.get("id"),
            "start_time": start_time.isoformat(),
            "outcome": "pending",
            "files_changed": [],
            "test_results": {},
        }

        try:
            # Phase 0: Setup workspace
            story_id = task.get("id", f"task-{sprint_num}")
            workspace = self.workspace_manager.create_sprint_workspace(sprint_num, story_id)
            session_result["workspace"] = str(workspace)

            # Phase 1: Generate BDD feature file (if story has BDD info)
            feature_file = None
            if self._should_generate_bdd(task):
                feature_file = self.bdd_generator.generate_feature_file(task, workspace)
                session_result["feature_file"] = str(feature_file)

            # Phase 2: Implementation using driver's runtime
            if driver.runtime:
                impl_result = await self._implement_with_runtime(
                    driver, navigator, task, workspace, feature_file
                )
                session_result.update(impl_result)
            else:
                # Fallback to dialogue-based (legacy)
                impl_result = await self._implement_with_dialogue(driver, navigator, task)
                session_result.update(impl_result)

            # Phase 3: Run tests if available
            if driver.runtime and self._has_tests(workspace):
                test_result = await self._run_tests_with_iteration(driver, workspace)
                session_result["test_results"] = test_result

            # Phase 4: Commit if tests pass
            if session_result.get("test_results", {}).get("passed", False):
                commit_sha = await self._commit_changes(driver, workspace, task)
                session_result["commit_sha"] = commit_sha
                session_result["outcome"] = "completed"

                # Phase 4.5: Push and create PR if remote git enabled
                pr_url = await self._push_and_create_pr(driver, workspace, task, commit_sha)
                if pr_url:
                    session_result["pr_url"] = pr_url
                    # Store PR URL in kanban card metadata
                    if self.kanban and task.get("id"):
                        try:
                            await self.db.update_card_field(
                                task["id"],
                                "metadata",
                                json.dumps({"pr_url": pr_url})
                            )
                        except Exception:
                            pass
            else:
                session_result["outcome"] = "tests_failed"

            # Phase 5: Update Kanban
            if self.kanban and task.get("id"):
                try:
                    await self.kanban.move_card(task["id"], "review")
                except Exception:
                    pass  # WIP limit may be full

        except Exception as e:
            session_result["outcome"] = "error"
            session_result["error"] = str(e)

        finally:
            self._busy_agents.discard(driver.config.role_id)
            self._busy_agents.discard(navigator.config.role_id)
            session_result["end_time"] = datetime.utcnow().isoformat()

        if self.db is not None:
            await self.db.log_pairing_session(session_result)

        return session_result

    async def _implement_with_runtime(
        self,
        driver: BaseAgent,
        navigator: BaseAgent,
        task: Dict,
        workspace: Path,
        feature_file: Optional[Path]
    ) -> Dict:
        """Implement code using driver's runtime (tool-using agent)."""

        # Build task description for driver
        task_prompt = self._build_implementation_prompt(task, workspace, feature_file)

        # Driver implements using agentic loop
        result = await driver.execute_coding_task(
            task_description=task_prompt,
            max_turns=20
        )

        return {
            "implementation": result["content"],
            "files_changed": result["files_changed"],
            "tool_calls": len(result["tool_calls"]),
            "turns": result["turns"],
            "success": result["success"]
        }

    def _build_implementation_prompt(
        self,
        task: Dict,
        workspace: Path,
        feature_file: Optional[Path]
    ) -> str:
        """Build implementation task prompt for agent."""
        prompt_parts = []

        # Story context
        prompt_parts.append(f"## Story: {task.get('title', 'Untitled')}")
        prompt_parts.append(f"\n{task.get('description', '')}\n")

        # Acceptance criteria
        if "acceptance_criteria" in task:
            prompt_parts.append("\n## Acceptance Criteria")
            for ac in task["acceptance_criteria"]:
                prompt_parts.append(f"- {ac}")

        # BDD feature reference
        if feature_file:
            prompt_parts.append(f"\n## BDD Feature")
            prompt_parts.append(f"A Gherkin feature file has been created at: {feature_file.relative_to(workspace)}")
            prompt_parts.append("Your implementation should make the scenarios in this feature pass.")

        # Implementation instructions
        prompt_parts.append("\n## Task")
        prompt_parts.append("Implement this story by:")
        prompt_parts.append("1. Reading any existing code in the workspace")
        prompt_parts.append("2. Writing clean, tested implementation")
        prompt_parts.append("3. Creating or updating test files")
        prompt_parts.append("4. Running tests to verify your implementation")
        prompt_parts.append("5. Iterating until all tests pass")
        prompt_parts.append("\nUse your tools (read_file, write_file, edit_file, bash, run_tests) to complete this task.")

        return "\n".join(prompt_parts)

    async def _implement_with_dialogue(
        self,
        driver: BaseAgent,
        navigator: BaseAgent,
        task: Dict
    ) -> Dict:
        """Fallback: dialogue-based implementation (no real code)."""
        task_desc = task.get("description", task.get("title", "unknown task"))
        prompt = f"Task: {task_desc}\nPropose an implementation approach."

        response = await driver.generate(prompt)

        return {
            "implementation": response,
            "files_changed": [],
            "tool_calls": 0,
            "turns": 1,
            "success": True
        }

    async def _run_tests_with_iteration(
        self,
        agent: BaseAgent,
        workspace: Path,
        max_iterations: int = 3
    ) -> Dict:
        """Run tests and iterate on failures."""
        for iteration in range(max_iterations):
            # Agent uses run_tests tool via runtime
            test_prompt = "Run the tests using the run_tests tool. If tests fail, read the error output and fix the code."

            result = await agent.execute_coding_task(
                task_description=test_prompt,
                max_turns=10
            )

            # Check if tests passed (look for success in tool calls or output)
            if "passed" in result["content"].lower() or "all tests passed" in result["content"].lower():
                return {
                    "passed": True,
                    "iterations": iteration + 1,
                    "output": result["content"]
                }

        return {
            "passed": False,
            "iterations": max_iterations,
            "output": result.get("content", "Tests did not pass after max iterations")
        }

    async def _commit_changes(
        self,
        agent: BaseAgent,
        workspace: Path,
        task: Dict
    ) -> Optional[str]:
        """Commit changes using agent's git tools."""
        story_id = task.get("id", "unknown")
        title = task.get("title", "Implementation")

        commit_prompt = f"""
        Stage and commit all changes with this message:

        feat: {title} ({story_id})

        Use git_status to see changes, git_add to stage all files, and git_commit with the message above.
        """

        result = await agent.execute_coding_task(
            task_description=commit_prompt,
            max_turns=5
        )

        # Extract commit SHA if mentioned in output (simplified)
        if "commit" in result["content"].lower():
            return "committed"  # Real SHA extraction would parse git output

        return None

    async def _push_and_create_pr(
        self,
        driver: BaseAgent,
        workspace: Path,
        task: Dict,
        commit_sha: str
    ) -> Optional[str]:
        """Push branch to remote and create PR/MR.

        Returns PR/MR URL if successful, None otherwise.
        """
        # Check if remote_git is enabled
        if not self.remote_git_config.get('enabled'):
            return None

        try:
            # Get current branch name
            proc = await asyncio.create_subprocess_shell(
                "git rev-parse --abbrev-ref HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace)
            )
            stdout, _ = await proc.communicate()
            branch_name = stdout.decode("utf-8").strip()

            # Extract agent metadata for git authorship
            author_name = driver.config.name.split(" (")[0]  # "Alex Chen"
            author_email = f"{driver.config.role_id}@{self.remote_git_config.get('author_email_domain', 'agent.local')}"

            # Create provider instance
            provider_type = self.remote_git_config.get('provider', 'github')
            provider_config_key = provider_type
            provider_config = self.remote_git_config.get(provider_config_key, {}).copy()

            # Add author metadata
            provider_config['author_name'] = author_name
            provider_config['author_email'] = author_email

            # Handle per-agent tokens for GitLab
            if provider_type == "gitlab":
                token_pattern = provider_config.get("token_env_pattern", "GITLAB_TOKEN_{role_id}")
                token_env = token_pattern.replace("{role_id}", driver.config.role_id)
                provider_config['token_env'] = token_env

            provider = create_provider(provider_type, workspace, provider_config)
            if not provider:
                return None

            # Push branch to remote
            push_cmd = f"git push -u origin {branch_name}"
            proc = await asyncio.create_subprocess_shell(
                push_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace)
            )
            await asyncio.wait_for(proc.communicate(), timeout=60)

            if proc.returncode != 0:
                return None

            # Create PR/MR
            base_branch = provider_config.get('base_branch', 'main')
            draft = provider_config.get('draft_prs', False)

            pr_title = f"feat: {task.get('title', 'Implementation')}"
            pr_body = (
                f"## Summary\n\n"
                f"{task.get('description', 'No description provided')}\n\n"
                f"## Implementation Details\n\n"
                f"- Driver: {driver.config.name}\n"
                f"- Branch: `{branch_name}`\n"
                f"- Commit: {commit_sha[:8] if len(commit_sha) > 8 else commit_sha}\n\n"
                f"## Test Plan\n\n"
                f"- [ ] All tests passing\n"
                f"- [ ] Code reviewed\n"
                f"- [ ] Ready for QA review\n"
            )

            pr_config = PullRequestConfig(
                title=pr_title,
                body=pr_body,
                base_branch=base_branch,
                head_branch=branch_name,
                draft=draft
            )

            result = await provider.create_pull_request(pr_config)

            if result.success:
                return result.url

            return None

        except Exception:
            # Log error but don't fail the pairing session
            return None

    def _should_generate_bdd(self, task: Dict) -> bool:
        """Check if task should have BDD feature file."""
        # Generate BDD if task has scenarios or is substantial
        return (
            "scenarios" in task
            or task.get("story_points", 0) >= 2
            or len(task.get("acceptance_criteria", [])) >= 2
        )

    def _has_tests(self, workspace: Path) -> bool:
        """Check if workspace has a tests directory."""
        return (workspace / "tests").exists() or (workspace / "test").exists()
