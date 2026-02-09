"""Sprint Review/Demo - Team demonstrates completed work to PO.

IMPORTANT: Stakeholder Feedback Loop
- Regular sprint reviews (most sprints): Team + PO only
- PO represents stakeholder interests (fast feedback loop within simulation time)
- Major stakeholder reviews: Every 5 sprints (see config.sprints_per_stakeholder_review)
- Real stakeholders review asynchronously (hours/days in human time)
- Simulation pauses for stakeholder input, then resumes with feedback as backlog items

This module handles the FAST loop (PO feedback). Real stakeholder feedback is handled
by the experiment runner pausing every 5 sprints for human input.
"""

from typing import List, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DemoResult:
    """Result of demonstrating a completed story."""

    story_id: str
    story_title: str
    presenter: str  # Agent ID who demoed
    demo_summary: str
    acceptance_criteria_met: Dict[str, bool]  # criterion -> met
    po_decision: str  # 'accepted' | 'rejected' | 'accepted_with_notes'
    po_feedback: str
    stakeholder_feedback: List[str] = field(default_factory=list)


@dataclass
class SprintReviewOutcome:
    """Outcome of sprint review ceremony."""

    sprint_num: int
    demo_results: List[DemoResult]
    total_stories: int
    accepted_stories: int
    rejected_stories: int
    acceptance_rate: float
    stakeholder_satisfaction: str  # 'high' | 'medium' | 'low'
    backlog_additions: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class SprintReviewSession:
    """Manages sprint review/demo ceremony."""

    def __init__(self, po_agent, dev_lead, qa_lead, kanban, db):
        self.po = po_agent
        self.dev_lead = dev_lead
        self.qa_lead = qa_lead
        self.kanban = kanban
        self.db = db

    async def run_review(
        self, sprint_num: int, completed_stories: List[Dict]
    ) -> SprintReviewOutcome:
        """Run sprint review with demos and PO acceptance.

        Args:
            sprint_num: Current sprint number
            completed_stories: Stories that passed QA review

        Returns:
            SprintReviewOutcome with acceptance decisions
        """
        print(f"\n  === Sprint Review/Demo - Sprint {sprint_num} ===")
        print("  Time: Last day of sprint (simulated)")
        print("  Participants: Team + PO + Stakeholders")
        print(f"  Stories to demo: {len(completed_stories)}\n")

        demo_results = []

        for story in completed_stories:
            print(f"  Demonstrating: {story['id']} - {story.get('title', 'Untitled')}")

            # Team demonstrates the story
            demo = await self._team_demonstrates_story(story, sprint_num)
            print(f"    Presenter: {demo.presenter}")
            print(f"    Demo: {demo.demo_summary[:80]}...")

            # PO reviews against acceptance criteria
            decision = await self._po_reviews_story(story, demo)
            demo.po_decision = decision["decision"]
            demo.po_feedback = decision["feedback"]
            demo.acceptance_criteria_met = decision["criteria_met"]

            print(f"    PO Decision: {demo.po_decision.upper()}")
            print(f"    Feedback: {demo.po_feedback[:80]}...")

            # Simulate stakeholder feedback
            stakeholder_feedback = await self._gather_stakeholder_feedback(story, demo)
            demo.stakeholder_feedback = stakeholder_feedback

            if stakeholder_feedback:
                print(f"    Stakeholder: {stakeholder_feedback[0][:60]}...")

            demo_results.append(demo)
            print()

        # Calculate metrics
        accepted = sum(1 for d in demo_results if d.po_decision == "accepted")
        rejected = sum(1 for d in demo_results if d.po_decision == "rejected")
        acceptance_rate = accepted / len(demo_results) if demo_results else 0.0

        # Determine stakeholder satisfaction
        satisfaction = self._calculate_satisfaction(acceptance_rate, demo_results)

        # Collect backlog additions from feedback
        backlog_additions = await self._collect_backlog_items(demo_results)

        outcome = SprintReviewOutcome(
            sprint_num=sprint_num,
            demo_results=demo_results,
            total_stories=len(completed_stories),
            accepted_stories=accepted,
            rejected_stories=rejected,
            acceptance_rate=acceptance_rate,
            stakeholder_satisfaction=satisfaction,
            backlog_additions=backlog_additions,
        )

        print("  Review Summary:")
        print(
            f"    Accepted: {accepted}/{len(demo_results)} ({acceptance_rate*100:.0f}%)"
        )
        print(f"    Rejected: {rejected}/{len(demo_results)}")
        print(f"    Stakeholder Satisfaction: {satisfaction.upper()}")
        print(f"    New backlog items: {len(backlog_additions)}\n")

        return outcome

    async def _team_demonstrates_story(
        self, story: Dict, sprint_num: int
    ) -> DemoResult:
        """Team member demonstrates completed story."""

        # Find who worked on this story (use dev lead or any developer)
        presenter = self.dev_lead.agent_id if self.dev_lead else "team"

        # Generate demo narrative
        demo_summary = await self._generate_demo_narrative(story, sprint_num)

        return DemoResult(
            story_id=story["id"],
            story_title=story.get("title", "Untitled"),
            presenter=presenter,
            demo_summary=demo_summary,
            acceptance_criteria_met={},  # Filled by PO review
            po_decision="",  # Filled by PO review
            po_feedback="",  # Filled by PO review
        )

    async def _generate_demo_narrative(self, story: Dict, sprint_num: int) -> str:
        """Generate demo narrative for story."""

        if not self.dev_lead:
            return f"We implemented {story.get('title', 'the story')} as specified."

        prompt = f"""You're demonstrating completed story to PO and stakeholders.

Story: {story['id']} - {story.get('title', 'Untitled')}
Description: {story.get('description', 'No description')}

Create a brief demo narrative (3-4 sentences) showing:
1. What was built
2. How it works (user perspective)
3. Key features implemented
4. Example usage or walkthrough

Keep it business-focused, not technical details.

Demo narrative:"""

        narrative = await self.dev_lead.generate(prompt)
        return narrative.strip()

    async def _po_reviews_story(self, story: Dict, demo: DemoResult) -> Dict:
        """PO reviews story against acceptance criteria and decides to accept/reject."""

        if not self.po:
            # Fallback: Auto-accept
            return {
                "decision": "accepted",
                "feedback": "Story meets requirements.",
                "criteria_met": {},
            }

        # Get acceptance criteria
        criteria = story.get("acceptance_criteria", [])

        if not criteria:
            criteria = ["Feature works as described"]

        # PO evaluates each criterion
        criteria_met = {}
        for criterion in criteria:
            # Simulate PO checking criterion (80% pass rate)
            import random

            met = random.random() < 0.80  # 80% of criteria typically met
            criteria_met[criterion] = met

        # Overall decision based on criteria
        all_met = all(criteria_met.values())
        most_met = (
            sum(criteria_met.values()) / len(criteria_met) >= 0.70
            if criteria_met
            else True
        )

        if all_met:
            decision = "accepted"
        elif most_met:
            decision = "accepted_with_notes"
        else:
            decision = "rejected"

        # Generate PO feedback
        feedback = await self._po_generates_feedback(
            story, demo, decision, criteria_met
        )

        return {
            "decision": decision,
            "feedback": feedback,
            "criteria_met": criteria_met,
        }

    async def _po_generates_feedback(
        self,
        story: Dict,
        demo: DemoResult,
        decision: str,
        criteria_met: Dict[str, bool],
    ) -> str:
        """PO generates acceptance/rejection feedback."""

        if not self.po:
            return f"Story {decision}."

        unmet_criteria = [c for c, met in criteria_met.items() if not met]

        prompt = f"""You're the PO reviewing a story demo.

Story: {story['id']} - {story.get('title', 'Untitled')}
Demo: {demo.demo_summary}

Decision: {decision.upper()}
Unmet criteria: {', '.join(unmet_criteria) if unmet_criteria else 'None'}

Provide feedback (2-3 sentences):
- If accepted: What you liked, business value delivered
- If accepted with notes: What works + what to improve in backlog refinement
- If rejected: What's missing and needs to be fixed

Feedback:"""

        feedback = await self.po.generate(prompt)
        return feedback.strip()

    async def _gather_stakeholder_feedback(
        self, story: Dict, demo: DemoResult
    ) -> List[str]:
        """Simulate stakeholder-like feedback from PO perspective.

        Note: In regular sprint reviews (most sprints), PO represents stakeholder
        interests. Real stakeholder feedback happens asynchronously every 5 sprints
        (outside simulation time). This method simulates what stakeholders MIGHT say
        for research/realism purposes, but it's actually PO feedback.
        """

        # Simplified: Generate 1-2 PO comments representing stakeholder perspective
        import random

        feedback_templates = [
            "This will help our customers a lot, great work!",
            "Can we add [related feature] in the next sprint?",
            "How does this integrate with [existing system]?",
            "The UX could be improved, but good start.",
            "This unblocks the enterprise deal, thank you!",
            "We need to validate this with users next sprint.",
        ]

        num_comments = random.randint(0, 2)
        return random.sample(feedback_templates, num_comments)

    def _calculate_satisfaction(
        self, acceptance_rate: float, demo_results: List[DemoResult]
    ) -> str:
        """Calculate stakeholder satisfaction based on demos."""

        # High satisfaction: >80% accepted
        # Medium satisfaction: 50-80% accepted
        # Low satisfaction: <50% accepted

        if acceptance_rate >= 0.80:
            return "high"
        elif acceptance_rate >= 0.50:
            return "medium"
        else:
            return "low"

    async def _collect_backlog_items(
        self, demo_results: List[DemoResult]
    ) -> List[Dict]:
        """Extract new backlog items from feedback."""

        backlog_items = []

        for demo in demo_results:
            # Extract follow-up items from PO feedback
            if (
                "next sprint" in demo.po_feedback.lower()
                or "backlog" in demo.po_feedback.lower()
            ):
                backlog_items.append(
                    {
                        "title": f"Follow-up for {demo.story_id}",
                        "description": f"Based on review feedback: {demo.po_feedback[:100]}",
                        "source": "sprint_review",
                        "sprint": None,  # Not assigned yet
                    }
                )

            # Extract from stakeholder feedback
            for feedback in demo.stakeholder_feedback:
                if "?" in feedback or "can we" in feedback.lower():
                    backlog_items.append(
                        {
                            "title": f"Stakeholder request: {feedback[:50]}",
                            "description": feedback,
                            "source": "stakeholder",
                            "sprint": None,
                        }
                    )

        return backlog_items
