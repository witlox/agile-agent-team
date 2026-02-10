"""Intelligent portfolio backlog distribution across teams.

Replaces naive round-robin with heuristic scoring based on team type,
agent specializations, and optional coordinator-driven triage.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TeamCapabilityProfile:
    """Summarises a team's capabilities for story scoring."""

    team_id: str
    team_type: str  # stream_aligned | platform | enabling | complicated_subsystem
    specializations: Dict[str, int] = field(default_factory=dict)  # spec → agent count
    seniority_distribution: Dict[str, int] = field(
        default_factory=dict
    )  # seniority → count
    agent_count: int = 0


@dataclass
class StoryClassification:
    """Result of classifying a single story."""

    inferred_domain: str  # e.g. "devops", "backend", "frontend", ""
    inferred_team_type: str  # e.g. "platform", "stream_aligned"
    confidence: float  # 0.0–1.0


# ---------------------------------------------------------------------------
# Keyword maps — extensible dicts
# ---------------------------------------------------------------------------

TEAM_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "platform": [
        "infrastructure",
        "ci/cd",
        "deploy",
        "docker",
        "monitoring",
        "logging",
        "health check",
        "connection pool",
        "tooling",
        "pipeline",
        "kubernetes",
    ],
    "enabling": [
        "documentation",
        "training",
        "onboarding",
        "guide",
        "best practices",
    ],
    "complicated_subsystem": [
        "algorithm",
        "cryptograph",
        "ml model",
        "inference",
        "mathematical",
        "optimization",
    ],
    # stream_aligned is the default fallback — no keywords needed
}

SPECIALIZATION_KEYWORDS: Dict[str, List[str]] = {
    "backend": ["api", "endpoint", "rest", "database", "server", "migration"],
    "frontend": ["ui", "component", "dashboard", "form"],
    "devops": ["ci/cd", "deploy", "docker", "kubernetes", "pipeline"],
    "networking": ["http", "proxy", "load balancer", "rate limit"],
    "security": ["authentication", "jwt", "token", "oauth", "encryption"],
    "database": ["sql", "postgresql", "connection pool", "schema"],
}


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def build_team_profiles(
    team_configs: List[Any],
    team_agents: Dict[str, List[Any]],
) -> Dict[str, TeamCapabilityProfile]:
    """Build capability profiles from TeamConfig + agent lists.

    Args:
        team_configs: List of TeamConfig dataclasses.
        team_agents: Mapping of team_id → list of BaseAgent instances.
    """
    profiles: Dict[str, TeamCapabilityProfile] = {}

    for tc in team_configs:
        specs: Dict[str, int] = {}
        seniority: Dict[str, int] = {}

        agents = team_agents.get(tc.id, [])
        for agent in agents:
            cfg = agent.config
            # Primary specialization
            if cfg.primary_specialization:
                specs[cfg.primary_specialization] = (
                    specs.get(cfg.primary_specialization, 0) + 1
                )
            # Auxiliary specializations
            for aux in getattr(cfg, "auxiliary_specializations", []):
                specs[aux] = specs.get(aux, 0) + 1
            # Seniority
            if cfg.seniority:
                seniority[cfg.seniority] = seniority.get(cfg.seniority, 0) + 1

        profiles[tc.id] = TeamCapabilityProfile(
            team_id=tc.id,
            team_type=getattr(tc, "team_type", "") or "",
            specializations=specs,
            seniority_distribution=seniority,
            agent_count=len(agents),
        )

    return profiles


def classify_story(story: Dict) -> StoryClassification:
    """Classify a story by domain and team type.

    Checks explicit fields first (``team_type_hint``, ``domain``, ``tags``),
    then falls back to keyword analysis of title + description.
    """
    # --- Explicit hints (highest confidence) ---
    team_type_hint = story.get("team_type_hint", "")
    if team_type_hint:
        domain = story.get("domain", "")
        return StoryClassification(
            inferred_domain=domain,
            inferred_team_type=team_type_hint,
            confidence=1.0,
        )

    domain = story.get("domain", "")
    tags = [t.lower() for t in story.get("tags", [])]

    if domain or tags:
        # Infer team_type from tags
        inferred_type = _team_type_from_keywords(tags)
        if not inferred_type:
            # Try domain as a keyword
            inferred_type = _team_type_from_keywords([domain]) if domain else ""
        return StoryClassification(
            inferred_domain=domain,
            inferred_team_type=inferred_type or "stream_aligned",
            confidence=0.8 if inferred_type else 0.5,
        )

    # --- Keyword analysis of title + description ---
    text = (story.get("title", "") + " " + story.get("description", "")).lower()

    inferred_type = _team_type_from_text(text)
    inferred_domain = _domain_from_text(text)

    confidence = 0.6 if inferred_type else 0.3
    return StoryClassification(
        inferred_domain=inferred_domain,
        inferred_team_type=inferred_type or "stream_aligned",
        confidence=confidence,
    )


def score_story_for_team(
    classification: StoryClassification,
    profile: TeamCapabilityProfile,
    current_count: int,
    is_brownfield: bool = False,
) -> float:
    """Score how well a story fits a team.

    Higher is better.  Factors:
      - Team type match:  +10
      - stream_aligned catch-all when no type inferred:  +2
      - Specialization overlap:  +3 per matching specialist (max +9)
      - Load balancing:  -1 per story already assigned
      - Brownfield bonus:  +5 when team_type matches and brownfield
    """
    score = 0.0

    # Team type match
    if (
        classification.inferred_team_type
        and classification.inferred_team_type == profile.team_type
    ):
        score += 10.0
        if is_brownfield:
            score += 5.0
    elif (
        classification.inferred_team_type == "stream_aligned" and not profile.team_type
    ):
        # Teams without explicit type treated as stream_aligned
        score += 2.0
    elif classification.confidence < 0.5 and profile.team_type == "stream_aligned":
        # Low-confidence stories default to stream_aligned teams
        score += 2.0

    # Specialization overlap
    spec_bonus = 0.0
    if classification.inferred_domain:
        count = profile.specializations.get(classification.inferred_domain, 0)
        spec_bonus += 3.0 * min(count, 3)
    spec_bonus = min(spec_bonus, 9.0)
    score += spec_bonus

    # Load balancing penalty
    score -= float(current_count)

    return score


def heuristic_distribute(
    stories: List[Dict],
    profiles: Dict[str, TeamCapabilityProfile],
    is_brownfield: bool = False,
) -> Dict[str, List[Dict]]:
    """Distribute stories to teams using scoring heuristic.

    For each story (sorted by priority), score all teams and assign to the
    highest-scoring team.  Returns mapping of team_id → story list.
    """
    if not stories or not profiles:
        return {tid: [] for tid in profiles}

    result: Dict[str, List[Dict]] = {tid: [] for tid in profiles}
    current_counts: Dict[str, int] = {tid: 0 for tid in profiles}

    # Sort stories by priority (lower = higher priority)
    sorted_stories = sorted(stories, key=lambda s: s.get("priority", 999))

    for story in sorted_stories:
        classification = classify_story(story)
        best_team: Optional[str] = None
        best_score = float("-inf")

        for tid, profile in profiles.items():
            s = score_story_for_team(
                classification, profile, current_counts[tid], is_brownfield
            )
            if s > best_score:
                best_score = s
                best_team = tid

        if best_team is not None:
            result[best_team].append(story)
            current_counts[best_team] += 1

    return result


def build_triage_prompt(
    stories: List[Dict],
    profiles: Dict[str, TeamCapabilityProfile],
    product_metadata: Optional[Dict] = None,
) -> str:
    """Build an LLM prompt for a coordinator to triage stories.

    The coordinator should reply with one ``ASSIGN:`` line per story.
    """
    lines: List[str] = [
        "You are the portfolio triage coordinator. Assign each story to the "
        "best-fit team based on team type and specializations.\n",
    ]

    # Product context
    if product_metadata:
        name = product_metadata.get("name", "")
        desc = product_metadata.get("description", "")
        if name or desc:
            lines.append(f"## Product\n{name}: {desc}\n")

    # Teams
    lines.append("## Teams")
    for tid, p in profiles.items():
        specs = ", ".join(f"{k}({v})" for k, v in p.specializations.items())
        lines.append(
            f"- {tid}: type={p.team_type}, agents={p.agent_count}, " f"specs=[{specs}]"
        )
    lines.append("")

    # Stories
    lines.append("## Stories to assign")
    for story in stories:
        sid = story.get("id", "?")
        title = story.get("title", "")
        desc = story.get("description", "")
        tags = story.get("tags", [])
        tag_str = f" tags={tags}" if tags else ""
        lines.append(f"- {sid}: {title} — {desc}{tag_str}")
    lines.append("")

    # Rules
    lines.append(
        "## Rules\n"
        "- Assign infrastructure/monitoring/deploy stories to platform teams.\n"
        "- Assign user-facing features and API endpoints to stream_aligned teams.\n"
        "- Assign documentation/training stories to enabling teams.\n"
        "- Balance load across teams.\n"
        "- Reply with one line per story in this exact format:\n"
        "  ASSIGN: <story_id> to <team_id> because <reason>\n"
    )

    return "\n".join(lines)


def parse_assignments(
    response: str,
    stories: List[Dict],
    valid_team_ids: List[str],
) -> Dict[str, List[Dict]]:
    """Parse ASSIGN: lines from coordinator response.

    Returns mapping of team_id → list of assigned stories.
    Unknown team IDs or story IDs are silently skipped.
    """
    story_map = {s["id"]: s for s in stories if "id" in s}
    team_set = set(valid_team_ids)
    result: Dict[str, List[Dict]] = {tid: [] for tid in valid_team_ids}

    for line in response.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("ASSIGN:"):
            continue
        text = stripped[len("ASSIGN:") :].strip()
        parts = text.split()
        if len(parts) < 3:
            continue

        story_id = parts[0]
        # Expect: <story_id> to <team_id> ...
        try:
            to_idx = [p.lower() for p in parts].index("to")
            team_id = parts[to_idx + 1]
        except (ValueError, IndexError):
            continue

        if story_id not in story_map:
            continue
        if team_id not in team_set:
            continue

        result[team_id].append(story_map[story_id])

    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _team_type_from_keywords(keywords: List[str]) -> str:
    """Return the team type that best matches the given keywords."""
    for team_type, patterns in TEAM_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in patterns:
                return team_type
    return ""


def _team_type_from_text(text: str) -> str:
    """Return the team type whose keywords appear most in *text*."""
    best_type = ""
    best_count = 0
    for team_type, patterns in TEAM_TYPE_KEYWORDS.items():
        count = sum(1 for p in patterns if p in text)
        if count > best_count:
            best_count = count
            best_type = team_type
    return best_type


def _domain_from_text(text: str) -> str:
    """Return the specialization domain whose keywords appear most in *text*."""
    best_domain = ""
    best_count = 0
    for domain, patterns in SPECIALIZATION_KEYWORDS.items():
        count = sum(1 for p in patterns if p in text)
        if count > best_count:
            best_count = count
            best_domain = domain
    return best_domain
