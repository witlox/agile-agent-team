"""Unit tests for specialization proficiency system."""

from src.agents.base_agent import BaseAgent, AgentConfig


def _make_agent(**overrides) -> BaseAgent:
    """Create a test agent with optional overrides."""
    defaults = {
        "role_id": "test_agent",
        "name": "Test Agent",
        "model": "mock",
        "temperature": 0.7,
        "max_tokens": 1000,
        "seniority": "senior",
        "role_archetype": "developer",
    }
    defaults.update(overrides)
    config = AgentConfig(**defaults)
    return BaseAgent(config, vllm_endpoint="mock://")


# --- Downclass seniority ---


def test_downclass_seniority_senior_to_mid():
    """Senior downclasses to mid."""
    assert BaseAgent._downclass_seniority("senior") == "mid"


def test_downclass_seniority_mid_to_junior():
    """Mid downclasses to junior."""
    assert BaseAgent._downclass_seniority("mid") == "junior"


def test_downclass_seniority_junior_floor():
    """Junior stays at junior (floor)."""
    assert BaseAgent._downclass_seniority("junior") == "junior"


# --- A-candidate descriptors ---


def test_a_candidate_descriptor_senior():
    """Senior descriptor mentions 8+ years and expert."""
    desc = BaseAgent._get_a_candidate_descriptor("senior")
    assert "8+ years" in desc
    assert "Expert" in desc
    assert "[LANGUAGE PROFICIENCY" in desc


def test_a_candidate_descriptor_mid():
    """Mid descriptor mentions 4+ years and proficient."""
    desc = BaseAgent._get_a_candidate_descriptor("mid")
    assert "4+ years" in desc
    assert "Proficient" in desc
    assert "[LANGUAGE PROFICIENCY" in desc


def test_a_candidate_descriptor_junior():
    """Junior descriptor mentions 1+ years and competent."""
    desc = BaseAgent._get_a_candidate_descriptor("junior")
    assert "1+ years" in desc
    assert "Competent" in desc
    assert "[LANGUAGE PROFICIENCY" in desc


# --- Prompt annotations ---


def test_primary_specialization_annotated_in_prompt():
    """Primary specialization prompt contains PRIMARY SPECIALIZATION tag."""
    agent = _make_agent(
        seniority="senior",
        primary_specialization="networking",
        auxiliary_specializations=["security"],
        specializations=["networking", "security"],
    )
    assert "[PRIMARY SPECIALIZATION" in agent.prompt
    assert "Senior-Level Proficiency" in agent.prompt


def test_auxiliary_specialization_downclassed_in_prompt():
    """Senior's auxiliary is annotated at mid level."""
    agent = _make_agent(
        seniority="senior",
        primary_specialization="networking",
        auxiliary_specializations=["security"],
        specializations=["networking", "security"],
    )
    assert "[AUXILIARY SPECIALIZATION" in agent.prompt
    assert "Mid-Level Proficiency" in agent.prompt
    assert "competent but not an expert" in agent.prompt


def test_a_candidate_baseline_in_prompt():
    """Prompt contains A-candidate language proficiency baseline."""
    agent = _make_agent(
        seniority="senior",
        primary_specialization="networking",
        specializations=["networking"],
    )
    assert "[LANGUAGE PROFICIENCY" in agent.prompt
    assert "A-Candidate Baseline" in agent.prompt


# --- Factory validation ---


def test_junior_max_one_auxiliary():
    """Factory truncates juniors to max 1 auxiliary specialization."""
    from src.agents.agent_factory import AgentFactory

    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
    )
    cfg = factory._create_agent_config(
        "jr_test",
        {
            "name": "Junior Test",
            "seniority": "junior",
            "primary_specialization": "backend",
            "auxiliary_specializations": ["frontend", "database"],
        },
    )
    assert cfg.primary_specialization == "backend"
    assert len(cfg.auxiliary_specializations) == 1
    assert cfg.auxiliary_specializations == ["frontend"]


def test_specializations_list_contains_all():
    """Combined specializations list equals primary + auxiliaries."""
    from src.agents.agent_factory import AgentFactory

    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
    )
    cfg = factory._create_agent_config(
        "sr_test",
        {
            "name": "Senior Test",
            "seniority": "senior",
            "primary_specialization": "networking",
            "auxiliary_specializations": ["security", "backend"],
        },
    )
    assert cfg.specializations == ["networking", "security", "backend"]


def test_backward_compat_flat_specializations():
    """Old flat specializations format still works; first becomes primary."""
    from src.agents.agent_factory import AgentFactory

    factory = AgentFactory(
        config_dir="team_config",
        vllm_endpoint="mock://",
    )
    cfg = factory._create_agent_config(
        "old_style",
        {
            "name": "Old Style Agent",
            "seniority": "mid",
            "specializations": ["backend", "api_design"],
        },
    )
    assert cfg.primary_specialization == "backend"
    assert cfg.auxiliary_specializations == ["api_design"]
    assert cfg.specializations == ["backend", "api_design"]
