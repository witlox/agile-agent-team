"""Unit tests for profile swapping system."""

import pytest
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.fixture
def agent():
    """Create a test agent."""
    config = AgentConfig(
        role_id="dev_mid_backend",
        name="Marcus Backend",
        role_archetype="developer",
        seniority="mid",
        specializations=["backend"],
        model="mock",
        temperature=0.7,
        max_tokens=1000,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def test_swap_to_sets_swap_state(agent):
    """Test swap_to() creates swap state."""
    agent.swap_to(
        target_role_id="incident_responder",
        domain="production incident response",
        proficiency=0.70,
        sprint=3,
    )

    assert agent._swap_state is not None
    assert agent._swap_state["role_id"] == "incident_responder"
    assert agent._swap_state["domain"] == "production incident response"
    assert agent._swap_state["proficiency"] == 0.70
    assert agent._swap_state["sprint"] == 3


def test_swap_to_modifies_prompt(agent):
    """Test swap_to() adds swap notice to prompt."""
    original_prompt = agent.prompt

    agent.swap_to(
        target_role_id="incident_responder",
        domain="production incident response",
        proficiency=0.70,
        sprint=3,
    )

    # Prompt should be longer (swap notice added)
    assert len(agent.prompt) > len(original_prompt)
    # Should contain swap notice markers
    assert "[PROFILE SWAP ACTIVE]" in agent.prompt
    assert "production incident response" in agent.prompt
    assert "70%" in agent.prompt


def test_swap_to_preserves_original_config(agent):
    """Test swap_to() preserves original config."""
    original_config = agent.config

    agent.swap_to(
        target_role_id="incident_responder",
        domain="production incident response",
        proficiency=0.70,
        sprint=3,
    )

    assert agent._original_config is not None
    assert agent._original_config.role_id == original_config.role_id
    assert agent._original_config.name == original_config.name
    assert agent._original_config.seniority == original_config.seniority


def test_is_swapped_property(agent):
    """Test is_swapped property returns correct state."""
    # Initially not swapped
    assert agent.is_swapped is False

    # After swap, should be True
    agent.swap_to("incident_responder", "incidents", 0.70, 3)
    assert agent.is_swapped is True

    # After revert, should be False
    agent.revert_swap()
    assert agent.is_swapped is False


def test_revert_swap_restores_config(agent):
    """Test revert_swap() restores original config."""
    original_role_id = agent.config.role_id
    original_name = agent.config.name

    agent.swap_to("incident_responder", "incidents", 0.70, 3)
    agent.revert_swap()

    assert agent.config.role_id == original_role_id
    assert agent.config.name == original_name
    assert agent._original_config is None


def test_revert_swap_clears_state(agent):
    """Test revert_swap() clears swap state."""
    agent.swap_to("incident_responder", "incidents", 0.70, 3)
    assert agent._swap_state is not None

    agent.revert_swap()
    assert agent._swap_state is None


def test_revert_swap_restores_prompt(agent):
    """Test revert_swap() restores original prompt."""
    original_prompt = agent.prompt

    agent.swap_to("incident_responder", "incidents", 0.70, 3)
    swapped_prompt = agent.prompt

    agent.revert_swap()

    # Prompt should be back to original
    assert agent.prompt == original_prompt
    assert agent.prompt != swapped_prompt
    assert "[PROFILE SWAP ACTIVE]" not in agent.prompt


def test_decay_swap_reduces_proficiency(agent):
    """Test decay_swap() reduces proficiency over time."""
    agent.swap_to("incident_responder", "incidents", 0.70, sprint=1)

    # No decay in same sprint
    agent.decay_swap(current_sprint=1, knowledge_decay_sprints=1)
    assert agent._swap_state is not None
    assert agent._swap_state["proficiency"] == 0.70

    # Decay happens but not enough to revert yet
    # (knowledge_decay_sprints=2 means revert after 2 sprints)
    agent.decay_swap(current_sprint=2, knowledge_decay_sprints=3)
    # After 1 sprint elapsed: proficiency -= 0.10 * 1 = 0.60
    assert agent._swap_state is not None
    assert agent._swap_state["proficiency"] == pytest.approx(0.60, abs=0.01)


def test_decay_swap_reverts_after_decay_period(agent):
    """Test decay_swap() reverts after decay threshold."""
    agent.swap_to("incident_responder", "incidents", 0.70, sprint=1)

    # After 1 sprint elapsed, with knowledge_decay_sprints=1, should revert
    agent.decay_swap(current_sprint=2, knowledge_decay_sprints=1)

    assert agent._swap_state is None
    assert agent.is_swapped is False


def test_multiple_swaps_only_preserve_first_original(agent):
    """Test multiple swaps don't overwrite original config."""
    original_role_id = agent.config.role_id

    # First swap
    agent.swap_to("incident_responder", "incidents", 0.70, 1)
    first_original = agent._original_config

    # Second swap (while already swapped)
    agent.swap_to("security_specialist", "security", 0.60, 2)

    # Original should still be the same (first original, not swapped config)
    assert agent._original_config == first_original
    assert agent._original_config.role_id == original_role_id


def test_revert_when_not_swapped_is_safe(agent):
    """Test revert_swap() when not swapped doesn't crash."""
    # Should be safe to call even when not swapped
    agent.revert_swap()
    assert agent._swap_state is None
    assert agent.is_swapped is False


def test_decay_when_not_swapped_is_safe(agent):
    """Test decay_swap() when not swapped doesn't crash."""
    # Should be safe to call even when not swapped
    agent.decay_swap(current_sprint=5, knowledge_decay_sprints=1)
    assert agent._swap_state is None
    assert agent.is_swapped is False


def test_swap_proficiency_bounds(agent):
    """Test proficiency decay doesn't go below 0."""
    agent.swap_to("incident_responder", "incidents", 0.15, sprint=1)

    # Decay would reduce to 0.05, but should cap at 0
    agent.decay_swap(current_sprint=2, knowledge_decay_sprints=3)

    # Should still be swapped but at minimum proficiency
    assert agent._swap_state is not None
    assert agent._swap_state["proficiency"] == pytest.approx(0.05, abs=0.01)
