"""Pure functions for detecting and restoring experiment state from output artifacts.

Used by --continue N to resume an experiment from its last completed sprint.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set


def detect_last_sprint(output_dir: str) -> int:
    """Scan output directory for sprint-NN directories, return highest N.

    Returns 0 if no sprint directories are found.
    """
    root = Path(output_dir)
    if not root.is_dir():
        return 0

    max_sprint = 0
    for entry in root.iterdir():
        if entry.is_dir():
            match = re.fullmatch(r"sprint-(\d+)", entry.name)
            if match:
                max_sprint = max(max_sprint, int(match.group(1)))
    return max_sprint


def detect_last_sprint_multi_team(output_dir: str, team_ids: List[str]) -> int:
    """Detect the last completed sprint across multiple team subdirectories.

    Looks inside ``<output_dir>/<team_id>/sprint-NN`` for each team and
    returns the maximum sprint number found across all teams.

    Returns 0 if no sprint directories are found.
    """
    root = Path(output_dir)
    if not root.is_dir():
        return 0

    max_sprint = 0
    for tid in team_ids:
        team_dir = root / tid
        if team_dir.is_dir():
            max_sprint = max(max_sprint, detect_last_sprint(str(team_dir)))
    return max_sprint


def restore_sprint_results(output_dir: str) -> List[Dict[str, Any]]:
    """Read sprint results from final_report.json (single-team mode).

    Returns the ``sprints`` list from the report, or an empty list if the
    file is missing or malformed.
    """
    report_path = Path(output_dir) / "final_report.json"
    if not report_path.exists():
        return []
    try:
        data = json.loads(report_path.read_text())
        sprints = data.get("sprints", [])
        if isinstance(sprints, list):
            return sprints
        return []
    except (json.JSONDecodeError, OSError):
        return []


def restore_team_results(output_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Read per-team sprint results from final_report.json (multi-team mode).

    Returns ``{team_id: [sprint_result, ...], ...}`` from the report's
    ``teams`` section, or an empty dict if the file is missing.
    """
    report_path = Path(output_dir) / "final_report.json"
    if not report_path.exists():
        return {}
    try:
        data = json.loads(report_path.read_text())
        teams = data.get("teams", {})
        if not isinstance(teams, dict):
            return {}
        result: Dict[str, List[Dict[str, Any]]] = {}
        for tid, team_data in teams.items():
            if isinstance(team_data, dict):
                sprints = team_data.get("sprints", [])
                result[tid] = sprints if isinstance(sprints, list) else []
        return result
    except (json.JSONDecodeError, OSError):
        return {}


def restore_selected_story_ids(output_dir: str) -> Set[str]:
    """Scan kanban.json snapshots to find all story IDs that were selected.

    Looks at ``sprint-NN/kanban.json`` for each sprint directory and collects
    ``story_id`` from cards in all statuses.
    """
    root = Path(output_dir)
    if not root.is_dir():
        return set()

    story_ids: Set[str] = set()
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if not re.fullmatch(r"sprint-\d+", entry.name):
            continue
        kanban_path = entry / "kanban.json"
        if not kanban_path.exists():
            continue
        story_ids.update(_extract_story_ids_from_kanban(kanban_path))
    return story_ids


def restore_selected_story_ids_multi_team(
    output_dir: str, team_ids: List[str]
) -> Set[str]:
    """Union of selected story IDs across all team subdirectories."""
    story_ids: Set[str] = set()
    root = Path(output_dir)
    for tid in team_ids:
        team_dir = root / tid
        if team_dir.is_dir():
            story_ids.update(restore_selected_story_ids(str(team_dir)))
    return story_ids


def _extract_story_ids_from_kanban(kanban_path: Path) -> Set[str]:
    """Extract story_id values from a kanban.json snapshot."""
    try:
        data = json.loads(kanban_path.read_text())
    except (json.JSONDecodeError, OSError):
        return set()

    ids: Set[str] = set()
    if isinstance(data, dict):
        for _status, cards in data.items():
            if isinstance(cards, list):
                for card in cards:
                    if isinstance(card, dict):
                        sid = card.get("story_id")
                        if sid:
                            ids.add(str(sid))
    return ids
