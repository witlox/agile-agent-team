"""Technical planning phase - Team breaks down stories into tasks."""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import random


@dataclass
class Task:
    """Technical task for implementation."""

    id: str
    story_id: str
    title: str
    description: str
    owner: str  # Agent ID who provides continuity
    initial_navigator: str  # Agent ID for Day 1
    estimated_hours: int
    depends_on: List[str] = field(default_factory=list)  # Task IDs this depends on
    specialization_needed: Optional[str] = None


class TechnicalPlanningSession:
    """Manages Phase 2 planning: Team breaks down stories, assigns owners."""

    def __init__(self, team_agents, dev_lead, qa_lead):
        self.team = team_agents
        self.dev_lead = dev_lead
        self.qa_lead = qa_lead

    async def plan_implementation(
        self, refined_stories: List, sprint_num: int
    ) -> Tuple[List[Task], Dict[str, List[str]]]:
        """Break down stories into tasks and assign owners.

        Args:
            refined_stories: Stories from Phase 1 refinement
            sprint_num: Current sprint number

        Returns:
            Tuple of (tasks, dependency_graph)
        """
        print("\n  === Phase 2: Technical Planning (Team Only) ===")
        print(f"  Stories to break down: {len(refined_stories)}\n")

        all_tasks = []
        task_counter = 1

        for story in refined_stories:
            print(f"  Planning: {story.id} - {story.title}")

            # Team discusses architecture and breaks down story
            task_breakdown = await self._team_breaks_down_story(story, sprint_num)
            print(f"    Breakdown: {len(task_breakdown)} tasks")

            # Create Task objects
            for task_dict in task_breakdown:
                task = Task(
                    id=f"T-{sprint_num:02d}-{task_counter:03d}",
                    story_id=story.id,
                    title=task_dict["title"],
                    description=task_dict["description"],
                    owner=task_dict["owner"],
                    initial_navigator=task_dict["initial_navigator"],
                    estimated_hours=task_dict.get("estimated_hours", 8),
                    depends_on=task_dict.get("depends_on", []),
                    specialization_needed=task_dict.get("specialization"),
                )
                all_tasks.append(task)
                task_counter += 1

            # Show task assignments
            for task in [t for t in all_tasks if t.story_id == story.id]:
                deps = (
                    f" (depends on {', '.join(task.depends_on)})"
                    if task.depends_on
                    else ""
                )
                print(f"    - {task.id}: {task.title}")
                print(
                    f"      Owner: {task.owner}, Navigator: {task.initial_navigator}{deps}"
                )

            print()

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(all_tasks)

        print(f"  Total tasks created: {len(all_tasks)}")
        print(
            f"  Dependencies: {sum(len(deps) for deps in dependency_graph.values())} edges\n"
        )

        return all_tasks, dependency_graph

    async def _team_breaks_down_story(self, story, sprint_num: int) -> List[Dict]:
        """Team collaboratively breaks down story into tasks.

        Returns:
            List of task dictionaries with owner and navigator assignments
        """
        if not self.dev_lead:
            # Fallback: Simple breakdown
            return self._simple_breakdown(story)

        # Dev lead facilitates breakdown discussion
        breakdown_prompt = f"""You're leading technical planning for sprint {sprint_num}.

Story: {story.id} - {story.title}
Description: {story.description}
Story Points: {story.story_points}
Team Consensus: {story.team_consensus}

Break this story down into 2-4 technical tasks. For each task:
1. Task title (implementation-focused, e.g., "Implement JWT token generation")
2. Brief description
3. Estimated hours (4, 8, 16)
4. Dependencies (which tasks must complete first)

Format your response as a list:
Task 1: [Title]
Description: [Description]
Hours: [4/8/16]
Depends on: [Task numbers, or "none"]

Task 2: [Title]
...

Keep it practical and implementable. Break complex tasks into smaller ones.
"""

        response = await self.dev_lead.generate(breakdown_prompt)

        # Parse response into task dictionaries
        tasks = self._parse_task_breakdown(response, story.story_points)

        # Assign owners based on specialization
        for task in tasks:
            owner = await self._assign_task_owner(task, story)
            navigator = await self._assign_initial_navigator(owner, task)
            task["owner"] = owner
            task["initial_navigator"] = navigator

        return tasks

    def _parse_task_breakdown(self, response: str, story_points: int) -> List[Dict]:
        """Parse dev lead's task breakdown response."""
        import re

        tasks = []
        lines = response.split("\n")

        current_task = None
        for line in lines:
            line = line.strip()

            # Task title line
            if re.match(r"^Task \d+:", line, re.IGNORECASE):
                if current_task:
                    tasks.append(current_task)
                title = re.sub(r"^Task \d+:\s*", "", line, flags=re.IGNORECASE).strip()
                current_task = {"title": title, "description": "", "estimated_hours": 8}

            # Description line
            elif line.lower().startswith("description:") and current_task:
                desc = re.sub(
                    r"^description:\s*", "", line, flags=re.IGNORECASE
                ).strip()
                current_task["description"] = desc

            # Hours line
            elif line.lower().startswith("hours:") and current_task:
                hours_match = re.search(r"\b(4|8|16)\b", line)
                if hours_match:
                    current_task["estimated_hours"] = int(hours_match.group(1))

            # Dependencies line
            elif line.lower().startswith("depends on:") and current_task:
                if "none" not in line.lower():
                    # Extract task numbers
                    deps = re.findall(r"\d+", line)
                    current_task["depends_on_numbers"] = [int(d) for d in deps]

        # Add last task
        if current_task:
            tasks.append(current_task)

        # Fallback if parsing failed
        if not tasks:
            # Create simple tasks based on story points
            num_tasks = min(story_points // 2, 4)  # 2-4 tasks
            for i in range(max(1, num_tasks)):
                tasks.append(
                    {
                        "title": f"Implement component {i+1}",
                        "description": "Implementation task",
                        "estimated_hours": 8,
                    }
                )

        return tasks

    async def _assign_task_owner(self, task: Dict, story) -> str:
        """Team discusses and assigns task owner based on specialization.

        Returns:
            Agent ID of the owner
        """
        # Extract keywords from task to determine specialization needed
        task_text = f"{task['title']} {task.get('description', '')}".lower()

        # Map keywords to specializations
        specialization_keywords = {
            "python_specialist": ["python", "django", "flask", "pytest"],
            "golang_specialist": ["go", "golang", "goroutine", "channel"],
            "rust_specialist": ["rust", "cargo", "ownership", "lifetime"],
            "typescript_specialist": ["typescript", "react", "node", "frontend", "ui"],
            "cpp_specialist": ["c++", "cpp", "cmake", "memory"],
            "backend": ["api", "endpoint", "server", "database", "service"],
            "frontend": ["frontend", "ui", "component", "view", "page"],
            "devops": ["deploy", "docker", "kubernetes", "ci", "pipeline"],
            "test_automation": ["test", "testing", "qa", "integration test"],
        }

        # Find best specialization match
        best_spec = None
        best_score = 0
        for spec, keywords in specialization_keywords.items():
            score = sum(1 for kw in keywords if kw in task_text)
            if score > best_score:
                best_score = score
                best_spec = spec

        task["specialization"] = best_spec

        # Find developers with matching specialization
        matching_devs = [
            agent
            for agent in self.team
            if hasattr(agent.config, "specializations")
            and best_spec is not None
            and any(
                best_spec in str(s).lower() or str(s).lower() in best_spec.lower()
                for s in agent.config.specializations
            )
        ]

        if matching_devs:
            # Pick senior if available, otherwise mid, otherwise any
            senior = [a for a in matching_devs if a.config.seniority == "senior"]
            mid = [a for a in matching_devs if a.config.seniority == "mid"]

            if senior:
                return senior[0].config.role_id
            elif mid:
                return mid[0].config.role_id
            else:
                return matching_devs[0].config.role_id

        # Fallback: Pick any senior developer
        seniors = [a for a in self.team if a.config.seniority == "senior"]
        if seniors:
            return seniors[0].config.role_id

        # Last resort: Pick first developer
        return self.team[0].config.role_id if self.team else "unknown"

    async def _assign_initial_navigator(self, owner: str, task: Dict) -> str:
        """Assign initial navigator (Day 1 pair) for task owner.

        Prefer someone with complementary skills.
        """
        # Find owner agent
        owner_agent = next((a for a in self.team if a.config.role_id == owner), None)

        if not owner_agent:
            # Fallback
            return self.team[0].config.role_id if self.team else owner

        # Find available navigators (not the owner)
        candidates = [a for a in self.team if a.config.role_id != owner]

        if not candidates:
            return owner  # Fallback (solo work)

        # Prefer complementary seniority
        if owner_agent.config.seniority == "senior":
            # Senior pairs with junior/mid for mentoring
            juniors = [a for a in candidates if a.config.seniority in ["junior", "mid"]]
            if juniors:
                return random.choice(juniors).config.role_id

        elif owner_agent.config.seniority == "junior":
            # Junior pairs with senior for learning
            seniors = [a for a in candidates if a.config.seniority == "senior"]
            if seniors:
                return random.choice(seniors).config.role_id

        # Default: Random pairing
        return random.choice(candidates).config.role_id

    def _simple_breakdown(self, story) -> List[Dict]:
        """Simple fallback breakdown when no dev lead available."""
        num_tasks = min(story.story_points // 2, 3)
        tasks = []

        for i in range(max(1, num_tasks)):
            tasks.append(
                {
                    "title": f"{story.title} - Part {i+1}",
                    "description": f"Implementation task {i+1}",
                    "estimated_hours": 8,
                    "owner": self.team[i % len(self.team)].config.role_id
                    if self.team
                    else "unknown",
                    "initial_navigator": self.team[
                        (i + 1) % len(self.team)
                    ].config.role_id
                    if len(self.team) > 1
                    else self.team[0].config.role_id,
                }
            )

        return tasks

    def _build_dependency_graph(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """Build dependency graph from tasks.

        Returns:
            Dictionary mapping task_id -> [dependent_task_ids]
        """
        graph = {task.id: task.depends_on.copy() for task in tasks}

        # Resolve depends_on_numbers to actual task IDs
        for task in tasks:
            if hasattr(task, "depends_on_numbers"):
                # Map numbers to task IDs in same story
                story_tasks = [t for t in tasks if t.story_id == task.story_id]
                for dep_num in task.depends_on_numbers:
                    if 1 <= dep_num <= len(story_tasks):
                        dep_task_id = story_tasks[dep_num - 1].id
                        if dep_task_id not in graph[task.id]:
                            graph[task.id].append(dep_task_id)

        return graph
