"""Unit tests for BehavioralTaxonomy + Scorer (F-11)."""

import pytest

from src.orchestrator.behavioral_taxonomy import (
    BEHAVIORAL_CODES,
    BehavioralScorer,
    get_codes_for_category,
    get_codes_for_stage,
)
from src.orchestrator.scenario_catalog import EPISODE_TYPES


class TestBehavioralCodes:
    def test_thirty_codes_defined(self):
        assert len(BEHAVIORAL_CODES) == 30

    def test_codes_numbered_b01_through_b30(self):
        expected = {f"B-{i:02d}" for i in range(1, 31)}
        assert set(BEHAVIORAL_CODES.keys()) == expected

    def test_all_codes_have_required_fields(self):
        for key, code in BEHAVIORAL_CODES.items():
            assert code.code == key
            assert code.name, f"{key} has empty name"
            assert code.description, f"{key} has empty description"
            assert code.stage in (1, 2, 3, 4), f"{key} has invalid stage {code.stage}"
            assert code.category, f"{key} has empty category"
            assert code.detection_heuristic, f"{key} has empty detection_heuristic"

    def test_stages_1_through_4_covered(self):
        stages = {code.stage for code in BEHAVIORAL_CODES.values()}
        assert stages == {1, 2, 3, 4}

    def test_codes_match_episode_types_target_behaviors(self):
        """Every behavior ref'd in EPISODE_TYPES must exist in BEHAVIORAL_CODES."""
        for ep_name, ep_info in EPISODE_TYPES.items():
            for b_code in ep_info["target_behaviors"]:
                assert b_code in BEHAVIORAL_CODES, (
                    f"EPISODE_TYPES[{ep_name!r}] references {b_code} "
                    f"which is not in BEHAVIORAL_CODES"
                )

    def test_all_codes_belong_to_valid_category(self):
        valid_categories = set(EPISODE_TYPES.keys())
        for key, code in BEHAVIORAL_CODES.items():
            assert (
                code.category in valid_categories
            ), f"{key} has category {code.category!r} not in EPISODE_TYPES"

    def test_behavioral_code_is_frozen(self):
        code = BEHAVIORAL_CODES["B-01"]
        with pytest.raises(AttributeError):
            code.name = "something_else"  # type: ignore[misc]


class TestGetCodes:
    def test_get_codes_for_category_elicitation(self):
        codes = get_codes_for_category("elicitation")
        assert len(codes) == 3
        assert all(c.category == "elicitation" for c in codes)

    def test_get_codes_for_stage_1(self):
        codes = get_codes_for_stage(1)
        assert len(codes) == 11  # B-01 through B-11
        assert all(c.stage == 1 for c in codes)

    def test_get_codes_for_stage_4(self):
        codes = get_codes_for_stage(4)
        assert len(codes) == 3  # B-28, B-29, B-30


class TestBehavioralScorer:
    def setup_method(self):
        self.scorer = BehavioralScorer()

    def test_empty_expected_returns_perfect_score(self):
        score, detected = self.scorer.score([{"action_content": "hello"}], [])
        assert score == 1.0
        assert detected == []

    def test_empty_decisions_returns_zero(self):
        score, detected = self.scorer.score([], ["B-01"])
        assert score == 0.0
        assert detected == []

    def test_perfect_match(self):
        decisions = [
            {
                "action_content": "Can you clarify this requirement?",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
            {
                "action_content": "The acceptance criteria are missing edge cases",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
            {
                "action_content": "I suggest we split this into smaller stories",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-01", "B-02", "B-03"])
        assert score == pytest.approx(1.0)
        assert set(detected) == {"B-01", "B-02", "B-03"}

    def test_no_match(self):
        decisions = [
            {
                "action_content": "Writing implementation code now",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-01", "B-02"])
        assert score == 0.0
        assert detected == []

    def test_partial_match(self):
        decisions = [
            {
                "action_content": "Can you clarify this requirement?",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
            {
                "action_content": "Writing code now",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-01", "B-02"])
        assert score == pytest.approx(0.5)
        assert detected == ["B-01"]

    def test_b07_test_first_detection(self):
        """B-07: test appears before implement in decisions."""
        decisions = [
            {
                "action_content": "Writing test cases first",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
            {
                "action_content": "Now implementing the feature",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-07"])
        assert score == pytest.approx(1.0)
        assert "B-07" in detected

    def test_b09_incremental_commits(self):
        """B-09: multiple commits detected."""
        decisions = [
            {
                "action_content": "First commit: add model",
                "action_type": "execute_coding_task",
                "context": "",
                "metadata": {"tool_calls": ["git_commit"]},
            },
            {
                "action_content": "Second commit: add controller",
                "action_type": "execute_coding_task",
                "context": "",
                "metadata": {"tool_calls": ["git_commit"]},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-09"])
        assert score == pytest.approx(1.0)
        assert "B-09" in detected

    def test_b17_root_cause_via_context(self):
        """B-17: root cause detection works via context field too."""
        decisions = [
            {
                "action_content": "Looking at logs",
                "action_type": "generate",
                "context": "Investigating root cause of the failure",
                "metadata": {},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-17"])
        assert score == pytest.approx(1.0)

    def test_unknown_behavior_code_ignored(self):
        """Unknown behavior codes don't crash, just don't match."""
        decisions = [
            {
                "action_content": "hello",
                "action_type": "generate",
                "context": "",
                "metadata": {},
            }
        ]
        score, detected = self.scorer.score(decisions, ["B-99"])
        assert score == 0.0
        assert detected == []

    def test_b18_minimal_fix_via_files_changed(self):
        """B-18: detected via small number of files changed."""
        decisions = [
            {
                "action_content": "Fixed the bug",
                "action_type": "execute_coding_task",
                "context": "",
                "metadata": {"files_changed": ["src/foo.py"]},
            },
        ]
        score, detected = self.scorer.score(decisions, ["B-18"])
        assert score == pytest.approx(1.0)
        assert "B-18" in detected
