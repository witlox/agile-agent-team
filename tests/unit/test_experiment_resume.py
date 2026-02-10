"""Unit tests for experiment resume functions."""

import json
from pathlib import Path

from src.orchestrator.experiment_resume import (
    detect_last_sprint,
    detect_last_sprint_multi_team,
    restore_selected_story_ids,
    restore_selected_story_ids_multi_team,
    restore_sprint_results,
    restore_team_results,
)


# ---------------------------------------------------------------------------
# detect_last_sprint
# ---------------------------------------------------------------------------


class TestDetectLastSprint:
    def test_empty_dir(self, tmp_path: Path) -> None:
        assert detect_last_sprint(str(tmp_path)) == 0

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        assert detect_last_sprint(str(tmp_path / "nope")) == 0

    def test_single_sprint(self, tmp_path: Path) -> None:
        (tmp_path / "sprint-01").mkdir()
        assert detect_last_sprint(str(tmp_path)) == 1

    def test_multiple_sprints(self, tmp_path: Path) -> None:
        for i in [1, 2, 5]:
            (tmp_path / f"sprint-{i:02d}").mkdir()
        assert detect_last_sprint(str(tmp_path)) == 5

    def test_non_sprint_dirs_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "sprint-03").mkdir()
        (tmp_path / "logs").mkdir()
        (tmp_path / "sprint-summary.txt").touch()
        (tmp_path / "other-07").mkdir()
        assert detect_last_sprint(str(tmp_path)) == 3

    def test_sprint_zero_only(self, tmp_path: Path) -> None:
        (tmp_path / "sprint-00").mkdir()
        assert detect_last_sprint(str(tmp_path)) == 0


# ---------------------------------------------------------------------------
# detect_last_sprint_multi_team
# ---------------------------------------------------------------------------


class TestDetectLastSprintMultiTeam:
    def test_finds_max_across_teams(self, tmp_path: Path) -> None:
        (tmp_path / "alpha" / "sprint-02").mkdir(parents=True)
        (tmp_path / "beta" / "sprint-04").mkdir(parents=True)
        assert detect_last_sprint_multi_team(str(tmp_path), ["alpha", "beta"]) == 4

    def test_missing_team_dir(self, tmp_path: Path) -> None:
        (tmp_path / "alpha" / "sprint-01").mkdir(parents=True)
        assert detect_last_sprint_multi_team(str(tmp_path), ["alpha", "missing"]) == 1

    def test_empty_teams(self, tmp_path: Path) -> None:
        assert detect_last_sprint_multi_team(str(tmp_path), []) == 0


# ---------------------------------------------------------------------------
# restore_sprint_results
# ---------------------------------------------------------------------------


class TestRestoreSprintResults:
    def test_missing_file(self, tmp_path: Path) -> None:
        assert restore_sprint_results(str(tmp_path)) == []

    def test_valid_report(self, tmp_path: Path) -> None:
        sprints = [
            {"sprint": 1, "velocity": 10, "features_completed": 2},
            {"sprint": 2, "velocity": 15, "features_completed": 3},
        ]
        report = {"experiment": "test", "sprints": sprints}
        (tmp_path / "final_report.json").write_text(json.dumps(report))
        result = restore_sprint_results(str(tmp_path))
        assert len(result) == 2
        assert result[0]["velocity"] == 10
        assert result[1]["sprint"] == 2

    def test_corrupt_json(self, tmp_path: Path) -> None:
        (tmp_path / "final_report.json").write_text("not valid json{{{")
        assert restore_sprint_results(str(tmp_path)) == []

    def test_missing_sprints_key(self, tmp_path: Path) -> None:
        (tmp_path / "final_report.json").write_text(json.dumps({"experiment": "x"}))
        assert restore_sprint_results(str(tmp_path)) == []

    def test_sprints_not_a_list(self, tmp_path: Path) -> None:
        (tmp_path / "final_report.json").write_text(
            json.dumps({"sprints": "not a list"})
        )
        assert restore_sprint_results(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# restore_team_results
# ---------------------------------------------------------------------------


class TestRestoreTeamResults:
    def test_missing_file(self, tmp_path: Path) -> None:
        assert restore_team_results(str(tmp_path)) == {}

    def test_valid_multi_team_report(self, tmp_path: Path) -> None:
        report = {
            "mode": "multi_team",
            "teams": {
                "alpha": {
                    "sprints": [{"sprint": 1, "velocity": 8}],
                    "avg_velocity": 8,
                },
                "beta": {
                    "sprints": [
                        {"sprint": 1, "velocity": 12},
                        {"sprint": 2, "velocity": 14},
                    ],
                    "avg_velocity": 13,
                },
            },
        }
        (tmp_path / "final_report.json").write_text(json.dumps(report))
        result = restore_team_results(str(tmp_path))
        assert len(result) == 2
        assert len(result["alpha"]) == 1
        assert len(result["beta"]) == 2
        assert result["beta"][1]["velocity"] == 14

    def test_corrupt_json(self, tmp_path: Path) -> None:
        (tmp_path / "final_report.json").write_text("{bad")
        assert restore_team_results(str(tmp_path)) == {}

    def test_teams_not_dict(self, tmp_path: Path) -> None:
        (tmp_path / "final_report.json").write_text(json.dumps({"teams": []}))
        assert restore_team_results(str(tmp_path)) == {}


# ---------------------------------------------------------------------------
# restore_selected_story_ids
# ---------------------------------------------------------------------------


class TestRestoreSelectedStoryIds:
    def test_empty_dir(self, tmp_path: Path) -> None:
        assert restore_selected_story_ids(str(tmp_path)) == set()

    def test_single_sprint(self, tmp_path: Path) -> None:
        sprint_dir = tmp_path / "sprint-01"
        sprint_dir.mkdir()
        kanban = {
            "ready": [{"id": "c1", "story_id": "US-001"}],
            "in_progress": [{"id": "c2", "story_id": "US-002"}],
            "done": [{"id": "c3", "story_id": "US-003"}],
        }
        (sprint_dir / "kanban.json").write_text(json.dumps(kanban))
        result = restore_selected_story_ids(str(tmp_path))
        assert result == {"US-001", "US-002", "US-003"}

    def test_multiple_sprints(self, tmp_path: Path) -> None:
        for i, story_id in [(1, "US-001"), (2, "US-002")]:
            sprint_dir = tmp_path / f"sprint-{i:02d}"
            sprint_dir.mkdir()
            kanban = {"done": [{"id": f"c{i}", "story_id": story_id}]}
            (sprint_dir / "kanban.json").write_text(json.dumps(kanban))
        result = restore_selected_story_ids(str(tmp_path))
        assert result == {"US-001", "US-002"}

    def test_cards_without_story_id(self, tmp_path: Path) -> None:
        sprint_dir = tmp_path / "sprint-01"
        sprint_dir.mkdir()
        kanban = {
            "done": [
                {"id": "c1", "story_id": "US-001"},
                {"id": "c2"},  # no story_id
                {"id": "c3", "story_id": ""},  # empty story_id
            ]
        }
        (sprint_dir / "kanban.json").write_text(json.dumps(kanban))
        result = restore_selected_story_ids(str(tmp_path))
        assert result == {"US-001"}

    def test_corrupt_kanban_skipped(self, tmp_path: Path) -> None:
        sprint_dir = tmp_path / "sprint-01"
        sprint_dir.mkdir()
        (sprint_dir / "kanban.json").write_text("not json!")
        assert restore_selected_story_ids(str(tmp_path)) == set()

    def test_non_sprint_dirs_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "logs").mkdir()
        sprint_dir = tmp_path / "sprint-01"
        sprint_dir.mkdir()
        kanban = {"done": [{"id": "c1", "story_id": "US-001"}]}
        (sprint_dir / "kanban.json").write_text(json.dumps(kanban))
        assert restore_selected_story_ids(str(tmp_path)) == {"US-001"}


# ---------------------------------------------------------------------------
# restore_selected_story_ids_multi_team
# ---------------------------------------------------------------------------


class TestRestoreSelectedStoryIdsMultiTeam:
    def test_union_across_teams(self, tmp_path: Path) -> None:
        for tid, sid in [("alpha", "US-001"), ("beta", "US-002")]:
            sprint_dir = tmp_path / tid / "sprint-01"
            sprint_dir.mkdir(parents=True)
            kanban = {"done": [{"id": "c1", "story_id": sid}]}
            (sprint_dir / "kanban.json").write_text(json.dumps(kanban))

        result = restore_selected_story_ids_multi_team(str(tmp_path), ["alpha", "beta"])
        assert result == {"US-001", "US-002"}

    def test_missing_team_dir(self, tmp_path: Path) -> None:
        sprint_dir = tmp_path / "alpha" / "sprint-01"
        sprint_dir.mkdir(parents=True)
        kanban = {"done": [{"id": "c1", "story_id": "US-001"}]}
        (sprint_dir / "kanban.json").write_text(json.dumps(kanban))

        result = restore_selected_story_ids_multi_team(
            str(tmp_path), ["alpha", "ghost"]
        )
        assert result == {"US-001"}
