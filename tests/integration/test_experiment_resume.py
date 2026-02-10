"""Integration tests for experiment resume (--continue N)."""

import json
from pathlib import Path

from src.orchestrator.backlog import Backlog
from src.orchestrator.experiment_resume import (
    detect_last_sprint,
    detect_last_sprint_multi_team,
    restore_selected_story_ids,
    restore_selected_story_ids_multi_team,
    restore_sprint_results,
    restore_team_results,
)


# ---------------------------------------------------------------------------
# Helper: create a minimal backlog file
# ---------------------------------------------------------------------------


def _write_backlog(path: Path, stories: list) -> None:
    """Write a minimal backlog YAML for testing."""
    import yaml

    data = {
        "product": {"name": "Test Product", "description": "A test product"},
        "stories": stories,
    }
    path.write_text(yaml.dump(data))


# ---------------------------------------------------------------------------
# Backlog.mark_selected
# ---------------------------------------------------------------------------


class TestBacklogMarkSelected:
    def test_mark_selected_skips_stories(self, tmp_path: Path) -> None:
        stories = [
            {"id": "US-001", "title": "Story 1", "priority": 1},
            {"id": "US-002", "title": "Story 2", "priority": 2},
            {"id": "US-003", "title": "Story 3", "priority": 3},
        ]
        bp = tmp_path / "backlog.yaml"
        _write_backlog(bp, stories)

        backlog = Backlog(str(bp))
        assert backlog.remaining == 3

        backlog.mark_selected({"US-001", "US-002"})
        assert backlog.remaining == 1

        # next_stories should only return US-003
        available = backlog.next_stories(5)
        assert len(available) == 1
        assert available[0]["id"] == "US-003"

    def test_mark_selected_idempotent(self, tmp_path: Path) -> None:
        stories = [{"id": "US-001", "title": "Story 1", "priority": 1}]
        bp = tmp_path / "backlog.yaml"
        _write_backlog(bp, stories)

        backlog = Backlog(str(bp))
        backlog.mark_selected({"US-001"})
        backlog.mark_selected({"US-001"})  # duplicate
        assert backlog.remaining == 0


# ---------------------------------------------------------------------------
# Sprint results restore + append
# ---------------------------------------------------------------------------


class TestSprintResultsRestoreAndAppend:
    def test_restore_then_append(self, tmp_path: Path) -> None:
        """Simulate restoring prior results and appending a new sprint."""
        # Write a "prior" final_report.json with 2 sprints
        prior_sprints = [
            {"sprint": 1, "velocity": 10, "features_completed": 2},
            {"sprint": 2, "velocity": 15, "features_completed": 3},
        ]
        report = {"experiment": "test", "sprints": prior_sprints}
        (tmp_path / "final_report.json").write_text(json.dumps(report))

        # Restore
        results = restore_sprint_results(str(tmp_path))
        assert len(results) == 2

        # Simulate adding a new sprint result
        results.append({"sprint": 3, "velocity": 20, "features_completed": 4})
        assert len(results) == 3
        assert results[-1]["sprint"] == 3


# ---------------------------------------------------------------------------
# Full resume flow: single-team
# ---------------------------------------------------------------------------


class TestFullResumeSingleTeam:
    def test_detect_restore_verify(self, tmp_path: Path) -> None:
        """Create fake prior output, detect/restore, verify start sprint."""
        output = tmp_path / "experiment"
        output.mkdir()

        # Create sprint directories with kanban snapshots
        for i in [1, 2]:
            sprint_dir = output / f"sprint-{i:02d}"
            sprint_dir.mkdir()
            kanban = {
                "done": [
                    {"id": f"card-{i}", "story_id": f"US-{i:03d}"},
                ]
            }
            (sprint_dir / "kanban.json").write_text(json.dumps(kanban))

        # Write final_report.json
        report = {
            "experiment": "test",
            "sprints": [
                {"sprint": 1, "velocity": 10, "features_completed": 2},
                {"sprint": 2, "velocity": 12, "features_completed": 3},
            ],
        }
        (output / "final_report.json").write_text(json.dumps(report))

        # Detect last sprint
        last = detect_last_sprint(str(output))
        assert last == 2

        # Restore sprint results
        results = restore_sprint_results(str(output))
        assert len(results) == 2

        # Restore story IDs
        story_ids = restore_selected_story_ids(str(output))
        assert story_ids == {"US-001", "US-002"}

        # The next sprint should be 3
        continue_sprints = 2
        start = last + 1
        end = last + continue_sprints
        assert list(range(start, end + 1)) == [3, 4]


# ---------------------------------------------------------------------------
# Full resume flow: multi-team
# ---------------------------------------------------------------------------


class TestFullResumeMultiTeam:
    def test_detect_restore_verify_multi_team(self, tmp_path: Path) -> None:
        """Create fake multi-team output, detect/restore, verify."""
        output = tmp_path / "experiment"
        output.mkdir()

        team_ids = ["alpha", "beta"]

        # Create per-team sprint directories
        for tid in team_ids:
            for i in [1, 2, 3]:
                sprint_dir = output / tid / f"sprint-{i:02d}"
                sprint_dir.mkdir(parents=True)
                kanban = {
                    "done": [{"id": f"{tid}-c{i}", "story_id": f"{tid}-US-{i:03d}"}]
                }
                (sprint_dir / "kanban.json").write_text(json.dumps(kanban))

        # Write portfolio final_report.json
        report = {
            "mode": "multi_team",
            "teams": {
                "alpha": {
                    "sprints": [
                        {"sprint": 1, "velocity": 8, "features_completed": 1},
                        {"sprint": 2, "velocity": 10, "features_completed": 2},
                        {"sprint": 3, "velocity": 12, "features_completed": 2},
                    ]
                },
                "beta": {
                    "sprints": [
                        {"sprint": 1, "velocity": 6, "features_completed": 1},
                        {"sprint": 2, "velocity": 9, "features_completed": 2},
                        {"sprint": 3, "velocity": 11, "features_completed": 3},
                    ]
                },
            },
        }
        (output / "final_report.json").write_text(json.dumps(report))

        # Detect
        last = detect_last_sprint_multi_team(str(output), team_ids)
        assert last == 3

        # Restore team results
        team_results = restore_team_results(str(output))
        assert len(team_results) == 2
        assert len(team_results["alpha"]) == 3
        assert len(team_results["beta"]) == 3

        # Restore story IDs
        story_ids = restore_selected_story_ids_multi_team(str(output), team_ids)
        expected = set()
        for tid in team_ids:
            for i in [1, 2, 3]:
                expected.add(f"{tid}-US-{i:03d}")
        assert story_ids == expected

        # Next sprint should be 4
        continue_sprints = 2
        start = last + 1
        end = last + continue_sprints
        assert list(range(start, end + 1)) == [4, 5]
