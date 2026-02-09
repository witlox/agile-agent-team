"""Daily standup - coordination, architectural alignment, blocker resolution."""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StandupReport:
    """Report from a pair during standup."""
    pair: tuple  # (owner_id, navigator_id)
    task_id: str
    task_title: str

    # Standard standup items
    completed_yesterday: str
    plan_today: str
    blockers: List[str] = field(default_factory=list)

    # Agile-specific items
    architectural_discoveries: List[str] = field(default_factory=list)
    cross_pair_dependencies: List[Dict] = field(default_factory=list)
    needs_dev_lead_decision: List[str] = field(default_factory=list)


@dataclass
class StandupOutcome:
    """Outcome of standup with dev lead decisions."""
    reports: List[StandupReport]
    dev_lead_decisions: List[Dict]  # [{issue, decision, affected_pairs}, ...]
    dependency_coordination: List[Dict]  # [{from_pair, to_pair, what, deadline}, ...]
    architectural_alignments: List[Dict]  # [{assumption, reality, impact}, ...]
    timestamp: datetime = field(default_factory=datetime.now)


class DailyStandupSession:
    """Manages daily standup coordination."""

    def __init__(self, dev_lead, qa_lead, db):
        self.dev_lead = dev_lead
        self.qa_lead = qa_lead
        self.db = db

    async def run_standup(
        self,
        sprint_num: int,
        day_num: int,
        active_pairs: List[tuple],  # [(owner_id, navigator_id), ...]
        tasks_in_progress: List[Dict]
    ) -> StandupOutcome:
        """Run daily standup with all active pairs.

        Args:
            sprint_num: Current sprint number
            day_num: Day number in sprint (2-10, no standup on Day 1)
            active_pairs: List of (owner_id, navigator_id) tuples
            tasks_in_progress: List of task dictionaries currently being worked

        Returns:
            StandupOutcome with reports and dev lead decisions
        """
        print(f"\n  === Daily Standup - Sprint {sprint_num}, Day {day_num} ===")
        print(f"  Time: ~9:00 AM (simulated)")
        print(f"  Participants: {len(active_pairs)} pairs + Dev Lead\n")

        # Each pair reports
        reports = []
        for owner_id, navigator_id in active_pairs:
            # Find task for this pair
            task = self._find_task_for_pair(owner_id, tasks_in_progress)
            if task:
                report = await self._pair_reports(
                    (owner_id, navigator_id),
                    task,
                    sprint_num,
                    day_num
                )
                reports.append(report)
                self._print_pair_report(report)

        # Dev lead facilitates and resolves issues
        print("\n  Dev Lead facilitation:")
        outcome = await self._dev_lead_facilitates(
            reports,
            sprint_num,
            day_num
        )

        print(f"\n  Standup complete. Decisions made: {len(outcome.dev_lead_decisions)}")
        print(f"  Dependencies coordinated: {len(outcome.dependency_coordination)}")
        print(f"  Architectural alignments: {len(outcome.architectural_alignments)}\n")

        return outcome

    async def _pair_reports(
        self,
        pair: tuple,
        task: Dict,
        sprint_num: int,
        day_num: int
    ) -> StandupReport:
        """Generate standup report for a pair."""

        # Get task progress from database
        task_progress = await self._get_task_progress(task['id'], day_num)

        # Simulate pair's standup update
        owner_id, navigator_id = pair

        report = StandupReport(
            pair=pair,
            task_id=task['id'],
            task_title=task['title'],
            completed_yesterday=task_progress.get(
                'completed_yesterday',
                f"Started work on {task['title']}" if day_num == 2 else
                f"Continued implementation"
            ),
            plan_today=task_progress.get(
                'plan_today',
                f"Complete {task['title']}" if task_progress.get('progress', 0) > 70 else
                "Continue implementation and write tests"
            )
        )

        # Randomly inject realistic standup content (simulated)
        import random

        # 20% chance of architectural discovery
        if random.random() < 0.2:
            discoveries = [
                "We assumed stateless auth, but discovered we need session storage for MFA",
                "Original design used REST, but GraphQL is better fit for complex queries",
                "We need Redis for rate limiting, not just PostgreSQL",
                "Authentication middleware requires changes to all existing endpoints",
                "Frontend state management is more complex than estimated"
            ]
            report.architectural_discoveries.append(random.choice(discoveries))

        # 15% chance of cross-pair dependency
        if random.random() < 0.15:
            other_pairs = [p for p in [pair] if p != pair]  # Simplified
            if other_pairs:
                report.cross_pair_dependencies.append({
                    'needs_from': 'other pair',
                    'what': 'API endpoint stub',
                    'blocking': True
                })

        # 10% chance of blocker needing dev lead
        if random.random() < 0.1:
            blockers = [
                "Disagreement on whether to use Redis or PostgreSQL for sessions",
                "Unclear if we should support backwards compatibility",
                "Conflicting requirements between stories US-042 and US-039",
                "Need architectural decision: monolith vs. microservice for this feature"
            ]
            blocker = random.choice(blockers)
            report.blockers.append(blocker)
            report.needs_dev_lead_decision.append(blocker)

        return report

    async def _dev_lead_facilitates(
        self,
        reports: List[StandupReport],
        sprint_num: int,
        day_num: int
    ) -> StandupOutcome:
        """Dev lead facilitates standup and makes decisions."""

        decisions = []
        dependencies = []
        alignments = []

        # Collect all blockers needing decisions
        blockers_to_resolve = []
        for report in reports:
            for blocker in report.needs_dev_lead_decision:
                blockers_to_resolve.append({
                    'pair': report.pair,
                    'task': report.task_id,
                    'blocker': blocker
                })

        # Dev lead resolves each blocker
        for blocker_info in blockers_to_resolve:
            decision = await self._dev_lead_makes_decision(
                blocker_info['blocker'],
                sprint_num,
                day_num
            )
            decisions.append({
                'issue': blocker_info['blocker'],
                'decision': decision,
                'affected_pairs': [blocker_info['pair']],
                'task': blocker_info['task']
            })
            print(f"    🔧 Decision: {blocker_info['blocker']}")
            print(f"       → {decision}")

        # Coordinate cross-pair dependencies
        for report in reports:
            for dep in report.cross_pair_dependencies:
                coordination = await self._coordinate_dependency(
                    report.pair,
                    dep,
                    day_num
                )
                dependencies.append(coordination)
                print(f"    🔗 Dependency: {report.pair[0]} needs {dep['what']}")
                print(f"       → {coordination['plan']}")

        # Address architectural discoveries
        for report in reports:
            for discovery in report.architectural_discoveries:
                alignment = await self._align_architecture(
                    report.pair,
                    discovery,
                    sprint_num
                )
                alignments.append(alignment)
                print(f"    🏗️  Architecture: {discovery}")
                print(f"       → {alignment['decision']}")

        return StandupOutcome(
            reports=reports,
            dev_lead_decisions=decisions,
            dependency_coordination=dependencies,
            architectural_alignments=alignments
        )

    async def _dev_lead_makes_decision(
        self,
        blocker: str,
        sprint_num: int,
        day_num: int
    ) -> str:
        """Dev lead makes architectural or process decision."""

        if not self.dev_lead:
            return "Team to discuss and decide offline"

        prompt = f"""You're the dev lead in a daily standup (Sprint {sprint_num}, Day {day_num}).

A pair reports this blocker:
"{blocker}"

Make a clear, decisive call to unblock them. Consider:
- Technical trade-offs
- Sprint timeline
- Consistency with existing architecture
- Team skill levels

Provide your decision in 1-2 sentences. Be direct and actionable.

Your decision:"""

        decision = await self.dev_lead.generate(prompt)
        return decision.strip().split('\n')[0]  # First line

    async def _coordinate_dependency(
        self,
        blocked_pair: tuple,
        dependency: Dict,
        day_num: int
    ) -> Dict:
        """Dev lead coordinates cross-pair dependency."""

        return {
            'from_pair': blocked_pair,
            'needs': dependency['what'],
            'plan': f"Upstream pair to deliver by end of Day {day_num}",
            'blocking': dependency.get('blocking', False)
        }

    async def _align_architecture(
        self,
        pair: tuple,
        discovery: str,
        sprint_num: int
    ) -> Dict:
        """Dev lead addresses architectural discovery."""

        if not self.dev_lead:
            return {
                'discovery': discovery,
                'decision': 'Team to discuss and align',
                'impact': []
            }

        prompt = f"""In standup, a pair discovered:
"{discovery}"

As dev lead, provide architectural guidance:
1. Is this a valid concern?
2. What should the team do?
3. Which other pairs are affected?

Keep response concise (2-3 sentences).

Your guidance:"""

        guidance = await self.dev_lead.generate(prompt)

        return {
            'discovery': discovery,
            'decision': guidance.strip(),
            'impact': [pair]
        }

    def _find_task_for_pair(self, owner_id: str, tasks: List[Dict]) -> Optional[Dict]:
        """Find task assigned to pair owner."""
        for task in tasks:
            if task.get('owner') == owner_id:
                return task
        return None

    async def _get_task_progress(self, task_id: str, day_num: int) -> Dict:
        """Get task progress from database or estimate."""
        # Simplified: Estimate progress based on day number
        # In real implementation, query pairing session database

        progress_estimate = min(day_num * 15, 95)  # 15% per day, cap at 95%

        return {
            'progress': progress_estimate,
            'completed_yesterday': 'Implementation progress',
            'plan_today': 'Continue implementation' if progress_estimate < 80 else 'Finalize and test'
        }

    def _print_pair_report(self, report: StandupReport):
        """Print formatted pair report."""
        print(f"  📋 Pair: {report.pair[0]} + {report.pair[1]}")
        print(f"     Task: {report.task_id} - {report.task_title}")
        print(f"     Yesterday: {report.completed_yesterday}")
        print(f"     Today: {report.plan_today}")

        if report.blockers:
            print(f"     ⚠️  Blockers: {', '.join(report.blockers)}")

        if report.architectural_discoveries:
            print(f"     🏗️  Architectural: {report.architectural_discoveries[0]}")

        if report.cross_pair_dependencies:
            print(f"     🔗 Depends on: {report.cross_pair_dependencies[0]['what']}")

        print()
