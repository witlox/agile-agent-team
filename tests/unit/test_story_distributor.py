"""Unit tests for intelligent portfolio story distribution."""

from src.orchestrator.story_distributor import (
    StoryClassification,
    TeamCapabilityProfile,
    build_team_profiles,
    build_triage_prompt,
    classify_story,
    heuristic_distribute,
    parse_assignments,
    score_story_for_team,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeAgentConfig:
    def __init__(
        self,
        primary_specialization: str = "",
        auxiliary_specializations: list = None,
        seniority: str = "mid",
    ):
        self.primary_specialization = primary_specialization
        self.auxiliary_specializations = auxiliary_specializations or []
        self.seniority = seniority


class _FakeAgent:
    def __init__(self, spec: str = "", seniority: str = "mid", aux: list = None):
        self.config = _FakeAgentConfig(spec, aux or [], seniority)


class _FakeTeamConfig:
    def __init__(self, id: str, team_type: str = ""):
        self.id = id
        self.team_type = team_type


def _profile(
    team_id: str,
    team_type: str = "stream_aligned",
    specs: dict = None,
    agent_count: int = 3,
) -> TeamCapabilityProfile:
    return TeamCapabilityProfile(
        team_id=team_id,
        team_type=team_type,
        specializations=specs or {},
        seniority_distribution={},
        agent_count=agent_count,
    )


# ---------------------------------------------------------------------------
# build_team_profiles
# ---------------------------------------------------------------------------


def test_build_team_profiles():
    """Specialization counts and seniority are aggregated from agents."""
    teams = [_FakeTeamConfig("alpha", "stream_aligned")]
    agents = {
        "alpha": [
            _FakeAgent("backend", "senior"),
            _FakeAgent("backend", "mid"),
            _FakeAgent("frontend", "junior"),
        ]
    }

    profiles = build_team_profiles(teams, agents)
    assert "alpha" in profiles
    p = profiles["alpha"]
    assert p.team_type == "stream_aligned"
    assert p.specializations["backend"] == 2
    assert p.specializations["frontend"] == 1
    assert p.agent_count == 3
    assert p.seniority_distribution["senior"] == 1
    assert p.seniority_distribution["junior"] == 1


# ---------------------------------------------------------------------------
# classify_story
# ---------------------------------------------------------------------------


def test_classify_story_explicit_team_type_hint():
    story = {"id": "US-001", "title": "X", "team_type_hint": "platform"}
    c = classify_story(story)
    assert c.inferred_team_type == "platform"
    assert c.confidence == 1.0


def test_classify_story_explicit_domain():
    story = {"id": "US-002", "title": "X", "domain": "devops"}
    c = classify_story(story)
    assert c.inferred_domain == "devops"
    assert c.confidence > 0.0


def test_classify_story_explicit_tags():
    story = {"id": "US-003", "title": "X", "tags": ["monitoring", "infrastructure"]}
    c = classify_story(story)
    assert c.inferred_team_type == "platform"
    assert c.confidence >= 0.8


def test_classify_story_title_keywords():
    story = {
        "id": "US-004",
        "title": "Health check endpoint",
        "description": "monitoring",
    }
    c = classify_story(story)
    assert c.inferred_team_type == "platform"


def test_classify_story_default_stream_aligned():
    story = {
        "id": "US-005",
        "title": "User profile page",
        "description": "Display user info",
    }
    c = classify_story(story)
    assert c.inferred_team_type == "stream_aligned"


# ---------------------------------------------------------------------------
# score_story_for_team
# ---------------------------------------------------------------------------


def test_score_team_type_match():
    """Platform story scores highest for platform team."""
    classification = StoryClassification("devops", "platform", 0.8)
    platform_profile = _profile("plat", "platform", {"devops": 2})
    stream_profile = _profile("stream", "stream_aligned", {"backend": 2})

    s_plat = score_story_for_team(classification, platform_profile, 0)
    s_stream = score_story_for_team(classification, stream_profile, 0)
    assert s_plat > s_stream


def test_score_specialization_match():
    """Backend story scores higher for team with backend agents."""
    classification = StoryClassification("backend", "stream_aligned", 0.6)
    backend_team = _profile("be", "stream_aligned", {"backend": 3})
    frontend_team = _profile("fe", "stream_aligned", {"frontend": 3})

    s_be = score_story_for_team(classification, backend_team, 0)
    s_fe = score_story_for_team(classification, frontend_team, 0)
    assert s_be > s_fe


def test_score_load_balancing_penalty():
    """Team with more stories gets lower score."""
    classification = StoryClassification("", "stream_aligned", 0.3)
    profile = _profile("t1", "stream_aligned")

    s0 = score_story_for_team(classification, profile, 0)
    s3 = score_story_for_team(classification, profile, 3)
    assert s0 > s3


def test_score_brownfield_bonus():
    """Brownfield mode gives +5 when team type matches."""
    classification = StoryClassification("devops", "platform", 0.8)
    profile = _profile("plat", "platform")

    s_green = score_story_for_team(classification, profile, 0, is_brownfield=False)
    s_brown = score_story_for_team(classification, profile, 0, is_brownfield=True)
    assert s_brown == s_green + 5.0


# ---------------------------------------------------------------------------
# heuristic_distribute
# ---------------------------------------------------------------------------


def test_heuristic_distribute_basic():
    """6 stories across 2 teams — infra to platform, features to stream."""
    profiles = {
        "stream": _profile("stream", "stream_aligned", {"backend": 2}),
        "plat": _profile("plat", "platform", {"devops": 2}),
    }
    stories = [
        {
            "id": "S1",
            "title": "User login API",
            "priority": 1,
            "description": "REST endpoint",
        },
        {
            "id": "S2",
            "title": "Health check endpoint",
            "priority": 2,
            "description": "monitoring",
        },
        {"id": "S3", "title": "Deploy pipeline", "priority": 3, "description": "CI/CD"},
        {
            "id": "S4",
            "title": "User profile page",
            "priority": 4,
            "description": "display info",
        },
        {
            "id": "S5",
            "title": "Logging middleware",
            "priority": 5,
            "description": "infrastructure logging",
        },
        {
            "id": "S6",
            "title": "Shopping cart",
            "priority": 6,
            "description": "add items",
        },
    ]

    result = heuristic_distribute(stories, profiles)
    all_assigned = result["stream"] + result["plat"]
    assert len(all_assigned) == 6

    # Infrastructure stories should go to platform
    plat_ids = {s["id"] for s in result["plat"]}
    assert "S2" in plat_ids  # health check → platform
    assert "S3" in plat_ids  # deploy → platform


def test_heuristic_distribute_all_stream():
    """All generic stories, fairly balanced distribution."""
    profiles = {
        "t1": _profile("t1", "stream_aligned", agent_count=3),
        "t2": _profile("t2", "stream_aligned", agent_count=3),
    }
    stories = [
        {
            "id": f"S{i}",
            "title": f"Feature {i}",
            "priority": i,
            "description": "user feature",
        }
        for i in range(1, 7)
    ]

    result = heuristic_distribute(stories, profiles)
    assert len(result["t1"]) + len(result["t2"]) == 6
    # With load balancing, expect roughly even
    assert abs(len(result["t1"]) - len(result["t2"])) <= 2


def test_heuristic_distribute_empty():
    profiles = {"t1": _profile("t1")}
    result = heuristic_distribute([], profiles)
    assert result == {"t1": []}


def test_heuristic_distribute_single_team():
    profiles = {"only": _profile("only", "stream_aligned")}
    stories = [
        {"id": "S1", "title": "A", "priority": 1},
        {"id": "S2", "title": "B", "priority": 2},
    ]
    result = heuristic_distribute(stories, profiles)
    assert len(result["only"]) == 2


# ---------------------------------------------------------------------------
# build_triage_prompt
# ---------------------------------------------------------------------------


def test_build_triage_prompt_structure():
    profiles = {
        "alpha": _profile("alpha", "stream_aligned", {"backend": 2}),
        "beta": _profile("beta", "platform", {"devops": 1}),
    }
    stories = [
        {"id": "US-001", "title": "Login API", "description": "REST"},
        {"id": "US-002", "title": "CI pipeline", "description": "deploy"},
    ]

    prompt = build_triage_prompt(
        stories, profiles, {"name": "Demo", "description": "test"}
    )
    assert "alpha" in prompt
    assert "beta" in prompt
    assert "US-001" in prompt
    assert "US-002" in prompt
    assert "ASSIGN:" in prompt
    assert "Demo" in prompt


# ---------------------------------------------------------------------------
# parse_assignments
# ---------------------------------------------------------------------------


def test_parse_assignments_valid():
    response = (
        "ASSIGN: US-001 to alpha because it's a backend feature\n"
        "ASSIGN: US-002 to beta because infrastructure\n"
    )
    stories = [
        {"id": "US-001", "title": "Login"},
        {"id": "US-002", "title": "CI"},
    ]
    result = parse_assignments(response, stories, ["alpha", "beta"])
    assert len(result["alpha"]) == 1
    assert len(result["beta"]) == 1
    assert result["alpha"][0]["id"] == "US-001"


def test_parse_assignments_invalid_team():
    response = "ASSIGN: US-001 to unknown_team because reasons\n"
    stories = [{"id": "US-001", "title": "X"}]
    result = parse_assignments(response, stories, ["alpha"])
    assert result["alpha"] == []


def test_parse_assignments_invalid_story():
    response = "ASSIGN: FAKE-999 to alpha because reasons\n"
    stories = [{"id": "US-001", "title": "X"}]
    result = parse_assignments(response, stories, ["alpha"])
    assert result["alpha"] == []


def test_parse_assignments_empty():
    response = "I don't know what to do with these stories."
    stories = [{"id": "US-001", "title": "X"}]
    result = parse_assignments(response, stories, ["alpha"])
    assert result["alpha"] == []
