"""Behavioral taxonomy and scorer for RL episode evaluation.

Defines 30 behavioral codes (B-01 through B-30) that map to the
13 episode types in the scenario catalog.  The BehavioralScorer
evaluates decision traces against expected behaviors using keyword/
pattern heuristics (no LLM calls).  Dojo can override with its own
LLM-based judge by passing ``behavioral_score`` directly to
``RewardCalculator.compute()``.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class BehavioralCode:
    """A single behavioral code definition."""

    code: str  # "B-01"
    name: str  # "ask_clarifying_question"
    description: str  # Human-readable
    stage: int  # 1-4
    category: str  # Episode type name
    detection_heuristic: str  # Method name on BehavioralScorer


# fmt: off
BEHAVIORAL_CODES: Dict[str, BehavioralCode] = {
    # ── Stage 1: Foundation ──────────────────────────────────────────
    # elicitation
    "B-01": BehavioralCode("B-01", "ask_clarifying_question",
        "Agent asks a clarifying question about requirements",
        1, "elicitation", "_detect_clarifying_question"),
    "B-02": BehavioralCode("B-02", "identify_missing_acceptance_criteria",
        "Agent identifies missing acceptance criteria in a story",
        1, "elicitation", "_detect_missing_acceptance_criteria"),
    "B-03": BehavioralCode("B-03", "propose_story_split",
        "Agent proposes splitting a large story into smaller ones",
        1, "elicitation", "_detect_story_split"),

    # decomposition
    "B-04": BehavioralCode("B-04", "estimate_story_points",
        "Agent estimates story points for a task",
        1, "decomposition", "_detect_estimation"),
    "B-05": BehavioralCode("B-05", "identify_technical_dependencies",
        "Agent identifies dependencies between tasks",
        1, "decomposition", "_detect_dependencies"),
    "B-06": BehavioralCode("B-06", "create_subtasks",
        "Agent creates subtasks for a story",
        1, "decomposition", "_detect_subtasks"),

    # implementation
    "B-07": BehavioralCode("B-07", "write_test_first",
        "Agent writes tests before implementation code",
        1, "implementation", "_detect_test_first"),
    "B-08": BehavioralCode("B-08", "follow_coding_conventions",
        "Agent follows team coding conventions",
        1, "implementation", "_detect_conventions"),
    "B-09": BehavioralCode("B-09", "commit_incrementally",
        "Agent commits code in small incremental chunks",
        1, "implementation", "_detect_incremental_commits"),

    # self_monitoring
    "B-10": BehavioralCode("B-10", "run_tests_before_commit",
        "Agent runs tests before committing",
        1, "self_monitoring", "_detect_tests_before_commit"),
    "B-11": BehavioralCode("B-11", "request_review_at_checkpoint",
        "Agent requests review at pairing checkpoints",
        1, "self_monitoring", "_detect_review_request"),

    # ── Stage 2: Advanced ────────────────────────────────────────────
    # research
    "B-12": BehavioralCode("B-12", "search_for_prior_art",
        "Agent searches for existing solutions before implementing",
        2, "research", "_detect_prior_art_search"),
    "B-13": BehavioralCode("B-13", "prototype_before_commit",
        "Agent creates a prototype/spike before full implementation",
        2, "research", "_detect_prototype"),
    "B-14": BehavioralCode("B-14", "document_spike_findings",
        "Agent documents findings from a research spike",
        2, "research", "_detect_spike_docs"),

    # triage
    "B-15": BehavioralCode("B-15", "prioritize_by_severity",
        "Agent prioritizes issues by severity",
        2, "triage", "_detect_severity_prioritization"),
    "B-16": BehavioralCode("B-16", "communicate_impact_assessment",
        "Agent communicates impact assessment to the team",
        2, "triage", "_detect_impact_assessment"),

    # recovery
    "B-17": BehavioralCode("B-17", "diagnose_root_cause",
        "Agent diagnoses the root cause of an issue",
        2, "recovery", "_detect_root_cause"),
    "B-18": BehavioralCode("B-18", "apply_minimal_fix",
        "Agent applies a minimal, targeted fix",
        2, "recovery", "_detect_minimal_fix"),
    "B-19": BehavioralCode("B-19", "add_regression_test",
        "Agent adds a regression test after fixing a bug",
        2, "recovery", "_detect_regression_test"),

    # scope_change
    "B-20": BehavioralCode("B-20", "renegotiate_scope",
        "Agent renegotiates scope when requirements change",
        2, "scope_change", "_detect_scope_renegotiation"),
    "B-21": BehavioralCode("B-21", "update_backlog_priority",
        "Agent updates backlog priorities after scope change",
        2, "scope_change", "_detect_backlog_update"),

    # ── Stage 3: Expert ──────────────────────────────────────────────
    # borrowing_arrival
    "B-22": BehavioralCode("B-22", "read_team_conventions",
        "Borrowed agent reads the new team's conventions",
        3, "borrowing_arrival", "_detect_convention_reading"),
    "B-23": BehavioralCode("B-23", "introduce_self_at_standup",
        "Borrowed agent introduces themselves at standup",
        3, "borrowing_arrival", "_detect_standup_intro"),

    # cross_team_dependency
    "B-24": BehavioralCode("B-24", "declare_dependency",
        "Agent declares a cross-team dependency",
        3, "cross_team_dependency", "_detect_dependency_declaration"),
    "B-25": BehavioralCode("B-25", "negotiate_interface_contract",
        "Agent negotiates an interface contract with another team",
        3, "cross_team_dependency", "_detect_interface_negotiation"),

    # knowledge_handoff
    "B-26": BehavioralCode("B-26", "write_handoff_document",
        "Agent writes a handoff document before departure",
        3, "knowledge_handoff", "_detect_handoff_doc"),
    "B-27": BehavioralCode("B-27", "pair_with_successor",
        "Agent pairs with their successor for knowledge transfer",
        3, "knowledge_handoff", "_detect_successor_pairing"),

    # ── Stage 4: Transfer ────────────────────────────────────────────
    # onboarding_support
    "B-28": BehavioralCode("B-28", "mentor_new_member",
        "Agent mentors a new team member",
        4, "onboarding_support", "_detect_mentoring"),
    "B-29": BehavioralCode("B-29", "share_tacit_knowledge",
        "Agent shares tacit knowledge with the team",
        4, "onboarding_support", "_detect_knowledge_sharing"),

    # compensation
    "B-30": BehavioralCode("B-30", "cover_departed_role",
        "Agent covers responsibilities of a departed team member",
        4, "compensation", "_detect_role_coverage"),
}
# fmt: on


def get_codes_for_category(category: str) -> List[BehavioralCode]:
    """Return all behavioral codes for a given episode type category."""
    return [c for c in BEHAVIORAL_CODES.values() if c.category == category]


def get_codes_for_stage(stage: int) -> List[BehavioralCode]:
    """Return all behavioral codes for a given training stage."""
    return [c for c in BEHAVIORAL_CODES.values() if c.stage == stage]


class BehavioralScorer:
    """Score decision traces against expected behavioral codes.

    Uses keyword/pattern heuristics (no LLM calls).  Dojo can override
    with its own LLM-based judge by passing ``behavioral_score`` directly
    to ``RewardCalculator.compute()``.

    Usage::

        scorer = BehavioralScorer()
        score, detected = scorer.score(decisions, ["B-07", "B-09"])
    """

    def score(
        self,
        decisions: List[Dict[str, Any]],
        expected_behaviors: List[str],
    ) -> Tuple[float, List[str]]:
        """Score decisions against expected behavioral codes.

        Args:
            decisions: List of decision dicts with keys like ``action_type``,
                ``action_content``, ``metadata``, ``phase``.
            expected_behaviors: List of behavioral code strings (e.g. ``["B-07"]``).

        Returns:
            Tuple of (score 0.0-1.0, list of detected behavior code strings).
        """
        if not expected_behaviors:
            return 1.0, []

        if not decisions:
            return 0.0, []

        detected: List[str] = []
        for code_str in expected_behaviors:
            bc = BEHAVIORAL_CODES.get(code_str)
            if bc is None:
                continue
            heuristic = getattr(self, bc.detection_heuristic, None)
            if heuristic is not None and heuristic(decisions):
                detected.append(code_str)

        return len(detected) / len(expected_behaviors), detected

    # ── Stage 1 heuristics ───────────────────────────────────────────

    def _detect_clarifying_question(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-01: Agent asks a clarifying question."""
        keywords = {
            "clarify",
            "clarification",
            "question",
            "unclear",
            "ambiguous",
            "what do you mean",
            "could you explain",
            "can you clarify",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_missing_acceptance_criteria(
        self, decisions: List[Dict[str, Any]]
    ) -> bool:
        """B-02: Agent identifies missing acceptance criteria."""
        keywords = {
            "acceptance criteria",
            "missing criteria",
            "missing requirement",
            "not specified",
            "undefined behavior",
            "edge case",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_story_split(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-03: Agent proposes splitting a story."""
        keywords = {
            "split",
            "break down",
            "decompose",
            "too large",
            "smaller stories",
            "sub-story",
            "substory",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_estimation(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-04: Agent estimates story points."""
        keywords = {
            "story point",
            "estimate",
            "points",
            "sizing",
            "complexity",
            "t-shirt size",
            "fibonacci",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_dependencies(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-05: Agent identifies technical dependencies."""
        keywords = {
            "dependency",
            "depends on",
            "blocked by",
            "prerequisite",
            "requires",
            "dependent",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_subtasks(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-06: Agent creates subtasks."""
        keywords = {
            "subtask",
            "sub-task",
            "task breakdown",
            "work item",
            "step 1",
            "step 2",
            "checklist",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_test_first(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-07: Agent writes tests before implementation."""
        return self._check_action_order(decisions, first="test", then="implement")

    def _detect_conventions(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-08: Agent follows coding conventions."""
        keywords = {
            "convention",
            "style guide",
            "linting",
            "formatting",
            "naming convention",
            "code standard",
            "best practice",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_incremental_commits(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-09: Agent commits incrementally."""
        commit_count = sum(
            1
            for d in decisions
            if d.get("action_type") == "execute_coding_task"
            and "commit" in str(d.get("metadata", {}).get("tool_calls", [])).lower()
        )
        # Also check action_content for commit-related text
        if commit_count < 2:
            commit_count += sum(
                1
                for d in decisions
                if "commit" in d.get("action_content", "").lower()
                and d.get("action_type") in ("generate", "execute_coding_task")
            )
        return commit_count >= 2

    def _detect_tests_before_commit(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-10: Agent runs tests before committing."""
        return self._check_action_order(decisions, first="test", then="commit")

    def _detect_review_request(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-11: Agent requests review at checkpoint."""
        keywords = {
            "review",
            "checkpoint",
            "feedback",
            "check my work",
            "please review",
            "navigator",
        }
        return self._any_content_matches(decisions, keywords)

    # ── Stage 2 heuristics ───────────────────────────────────────────

    def _detect_prior_art_search(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-12: Agent searches for prior art."""
        keywords = {
            "prior art",
            "existing solution",
            "search",
            "look for",
            "already implemented",
            "reference implementation",
            "similar",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_prototype(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-13: Agent creates a prototype."""
        keywords = {
            "prototype",
            "spike",
            "proof of concept",
            "poc",
            "experiment",
            "try out",
            "quick test",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_spike_docs(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-14: Agent documents spike findings."""
        keywords = {
            "findings",
            "documented",
            "spike result",
            "research notes",
            "conclusion",
            "recommendation",
            "trade-off",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_severity_prioritization(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-15: Agent prioritizes by severity."""
        keywords = {
            "severity",
            "priority",
            "critical",
            "high priority",
            "p0",
            "p1",
            "urgent",
            "blocker",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_impact_assessment(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-16: Agent communicates impact assessment."""
        keywords = {
            "impact",
            "assessment",
            "affected",
            "blast radius",
            "downstream",
            "users impacted",
            "scope of impact",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_root_cause(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-17: Agent diagnoses root cause."""
        keywords = {
            "root cause",
            "diagnosis",
            "investigate",
            "debug",
            "underlying issue",
            "source of",
            "trace back",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_minimal_fix(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-18: Agent applies a minimal fix."""
        keywords = {
            "minimal fix",
            "targeted fix",
            "small change",
            "surgical",
            "narrow fix",
            "least invasive",
            "focused fix",
        }
        # Also check for small file changes
        for d in decisions:
            files_changed = d.get("metadata", {}).get("files_changed", [])
            if files_changed and len(files_changed) <= 2:
                return True
        return self._any_content_matches(decisions, keywords)

    def _detect_regression_test(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-19: Agent adds a regression test."""
        keywords = {
            "regression test",
            "regression",
            "test for the fix",
            "prevent recurrence",
            "test case for",
            "verify fix",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_scope_renegotiation(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-20: Agent renegotiates scope."""
        keywords = {
            "renegotiate",
            "scope change",
            "descope",
            "defer",
            "reduce scope",
            "out of scope",
            "negotiate",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_backlog_update(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-21: Agent updates backlog priorities."""
        keywords = {
            "backlog",
            "reprioritize",
            "re-prioritize",
            "priority update",
            "reorder",
            "move to backlog",
            "update priority",
        }
        return self._any_content_matches(decisions, keywords)

    # ── Stage 3 heuristics ───────────────────────────────────────────

    def _detect_convention_reading(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-22: Borrowed agent reads team conventions."""
        keywords = {
            "convention",
            "team norms",
            "coding standard",
            "style guide",
            "team practice",
            "how does this team",
            "team process",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_standup_intro(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-23: Borrowed agent introduces themselves."""
        keywords = {
            "introduce",
            "new to the team",
            "joining",
            "hello team",
            "i'm here to help",
            "borrowed from",
            "visiting",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_dependency_declaration(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-24: Agent declares cross-team dependency."""
        keywords = {
            "cross-team",
            "dependency",
            "depends on team",
            "blocked by team",
            "interface",
            "api contract",
            "shared service",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_interface_negotiation(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-25: Agent negotiates interface contract."""
        keywords = {
            "interface contract",
            "api contract",
            "negotiate",
            "agree on",
            "schema",
            "endpoint",
            "protocol",
            "message format",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_handoff_doc(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-26: Agent writes handoff document."""
        keywords = {
            "handoff",
            "hand-off",
            "transition document",
            "knowledge transfer",
            "documentation",
            "leaving notes",
            "departure doc",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_successor_pairing(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-27: Agent pairs with successor."""
        keywords = {
            "pair with successor",
            "knowledge transfer session",
            "shadow",
            "walk through",
            "show you how",
            "handover session",
            "pair session",
        }
        return self._any_content_matches(decisions, keywords)

    # ── Stage 4 heuristics ───────────────────────────────────────────

    def _detect_mentoring(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-28: Agent mentors a new member."""
        keywords = {
            "mentor",
            "guide",
            "teach",
            "help understand",
            "explain to",
            "show how",
            "onboarding buddy",
            "coaching",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_knowledge_sharing(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-29: Agent shares tacit knowledge."""
        keywords = {
            "tacit knowledge",
            "tribal knowledge",
            "undocumented",
            "tip",
            "trick",
            "gotcha",
            "watch out for",
            "heads up",
        }
        return self._any_content_matches(decisions, keywords)

    def _detect_role_coverage(self, decisions: List[Dict[str, Any]]) -> bool:
        """B-30: Agent covers departed role."""
        keywords = {
            "cover",
            "fill in",
            "take over",
            "compensate",
            "pick up",
            "absorb responsibilities",
            "step in for",
            "backfill",
        }
        return self._any_content_matches(decisions, keywords)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _any_content_matches(decisions: List[Dict[str, Any]], keywords: set) -> bool:
        """Return True if any decision's content matches a keyword."""
        for d in decisions:
            content = d.get("action_content", "").lower()
            context = d.get("context", "").lower()
            combined = content + " " + context
            for kw in keywords:
                if kw in combined:
                    return True
        return False

    @staticmethod
    def _check_action_order(
        decisions: List[Dict[str, Any]],
        first: str,
        then: str,
    ) -> bool:
        """Return True if a decision matching ``first`` appears before ``then``."""
        first_idx = -1
        then_idx = -1
        for i, d in enumerate(decisions):
            content = d.get("action_content", "").lower()
            action_type = d.get("action_type", "").lower()
            tool_calls = str(d.get("metadata", {}).get("tool_calls", [])).lower()
            combined = content + " " + action_type + " " + tool_calls
            if first_idx < 0 and first in combined:
                first_idx = i
            if then in combined:
                then_idx = i
        return first_idx >= 0 and then_idx > first_idx
