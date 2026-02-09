"""Story refinement phase - PO + Team collaborative planning."""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class RefinedStory:
    """Story after refinement with team estimates and clarifications."""

    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int
    priority: int
    clarifications: List[Dict[str, str]]  # [{agent: question, po: answer}, ...]
    team_consensus: str  # Summary of team understanding


class StoryRefinementSession:
    """Manages Phase 1 planning: PO presents stories, team asks questions."""

    def __init__(self, po_agent, team_agents, dev_lead):
        self.po = po_agent
        self.team = team_agents
        self.dev_lead = dev_lead

    async def refine_stories(
        self, candidate_stories: List[Dict], sprint_num: int, team_capacity: int
    ) -> List[RefinedStory]:
        """Run story refinement session with PO and team.

        Args:
            candidate_stories: Stories from backlog to consider
            sprint_num: Current sprint number
            team_capacity: Max story points team can commit to

        Returns:
            List of refined stories selected for sprint
        """
        refined_stories = []
        total_points = 0

        print("\n  === Phase 1: Story Refinement (PO + Team) ===")
        print(f"  Candidate stories: {len(candidate_stories)}")
        print(f"  Team capacity: {team_capacity} story points\n")

        for story in candidate_stories:
            print(f"  Refining: {story['id']} - {story['title']}")

            # PO presents story
            presentation = await self._po_present_story(story, sprint_num)
            print("    PO presents business context...")

            # Team asks clarifying questions
            clarifications = await self._team_asks_questions(story, presentation)
            print(f"    Team asked {len(clarifications)} clarifying questions")

            # Team estimates story points
            estimated_points = await self._team_estimates_story(story, clarifications)
            print(f"    Team estimate: {estimated_points} story points")

            # Check if we have capacity
            if total_points + estimated_points <= team_capacity:
                refined = RefinedStory(
                    id=story["id"],
                    title=story["title"],
                    description=story["description"],
                    acceptance_criteria=story.get("acceptance_criteria", []),
                    story_points=estimated_points,
                    priority=story.get("priority", 5),
                    clarifications=clarifications,
                    team_consensus=await self._build_team_consensus(
                        story, clarifications
                    ),
                )
                refined_stories.append(refined)
                total_points += estimated_points
                print(f"    ✓ Added to sprint ({total_points}/{team_capacity} points)")
            else:
                print("    ✗ Skipped (would exceed capacity)")
                break  # Stop once we hit capacity

            print()

        print(
            f"  Selected {len(refined_stories)} stories totaling {total_points} points\n"
        )
        return refined_stories

    async def _po_present_story(self, story: Dict, sprint_num: int) -> str:
        """PO presents story with business context."""
        if not self.po:
            # Fallback if no PO agent
            return f"Story {story['id']}: {story['description']}"

        prompt = f"""You are presenting story {story['id']} to the team in Sprint {sprint_num} planning.

Story: {story['title']}
Description: {story['description']}
Acceptance Criteria:
{self._format_criteria(story.get('acceptance_criteria', []))}

Present this story to the team covering:
1. Business context - Why are we building this? What problem does it solve?
2. User need - What does the user want to accomplish?
3. Business value - Why now? What's the impact?
4. Acceptance criteria - How will we know it's done?
5. Constraints - Any deadlines, compliance, dependencies?

Keep it concise (3-4 paragraphs). Focus on the WHAT and WHY, not the HOW.
"""
        presentation = await self.po.generate(prompt)
        return presentation

    async def _team_asks_questions(
        self, story: Dict, presentation: str
    ) -> List[Dict[str, str]]:
        """Team members ask clarifying questions, PO answers."""
        clarifications = []

        # Sample 3-4 team members to ask questions (rotate who asks)
        import random

        asking_team = random.sample(self.team, min(4, len(self.team)))

        for agent in asking_team:
            # Agent generates clarifying question
            question_prompt = f"""You're in sprint planning. The PO just presented:

{presentation}

Ask ONE clarifying question about:
- Technical depth/complexity
- Edge cases or error handling
- Integration with existing systems
- User experience details
- Scope boundaries (what's in/out)

Your question (one sentence):"""

            question = await agent.generate(question_prompt)
            question = question.strip().split("\n")[0]  # Take first line only

            # PO answers
            if self.po:
                answer_prompt = f"""A team member asked about story {story['id']}:

Question: {question}

Provide a clear, concise answer from the business/product perspective.
Focus on requirements, not implementation. (2-3 sentences max)"""

                answer = await self.po.generate(answer_prompt)
            else:
                answer = "Standard business requirements apply."

            clarifications.append(
                {
                    "agent": agent.config.name,
                    "agent_id": agent.config.role_id,
                    "question": question,
                    "answer": answer.strip(),
                }
            )

        return clarifications

    async def _team_estimates_story(
        self, story: Dict, clarifications: List[Dict]
    ) -> int:
        """Team estimates story points collaboratively.

        Uses dev lead to facilitate estimation discussion.
        """
        if not self.dev_lead:
            # Fallback to story's existing estimate or default
            return story.get("story_points", 3)

        # Build context from clarifications
        clarification_summary = "\n".join(
            f"Q: {c['question']}\nA: {c['answer']}" for c in clarifications
        )

        estimate_prompt = f"""You're facilitating story point estimation for:

Story: {story['title']}
Description: {story['description']}

Team discussion so far:
{clarification_summary}

Based on the story complexity and team discussion, estimate story points:
- 1 point: Trivial (few hours)
- 2 points: Simple (< 1 day)
- 3 points: Moderate (1-2 days)
- 5 points: Complex (3-4 days)
- 8 points: Very complex (full week)
- 13 points: Epic (needs breakdown)

Reply with ONLY the number (1, 2, 3, 5, 8, or 13):"""

        response = await self.dev_lead.generate(estimate_prompt)

        # Parse response
        import re

        match = re.search(r"\b(1|2|3|5|8|13)\b", response)
        if match:
            return int(match.group(1))

        # Fallback
        return story.get("story_points", 3)

    async def _build_team_consensus(
        self, story: Dict, clarifications: List[Dict]
    ) -> str:
        """Build a consensus statement about team's understanding."""
        if not self.dev_lead:
            return f"Team understands story {story['id']}"

        clarification_summary = "\n".join(
            f"- {c['question']} → {c['answer']}"
            for c in clarifications[:3]  # Top 3 clarifications
        )

        consensus_prompt = f"""Summarize the team's understanding after discussing story {story['id']}:

{story['title']}

Key clarifications:
{clarification_summary}

Write a one-sentence consensus statement about what the team will build.
Example: "Team will implement JWT-based authentication with refresh tokens, supporting both web and mobile clients."

Your consensus (one sentence):"""

        consensus = await self.dev_lead.generate(consensus_prompt)
        return consensus.strip().split("\n")[0]  # First line only

    def _format_criteria(self, criteria: List[str]) -> str:
        """Format acceptance criteria as bulleted list."""
        if not criteria:
            return "  (None specified)"
        return "\n".join(f"  - {c}" for c in criteria)
