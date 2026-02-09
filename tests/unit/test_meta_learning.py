"""Unit tests for meta-learning system."""

import json
import pytest
from pathlib import Path
from src.agents.base_agent import BaseAgent, AgentConfig


@pytest.fixture
def temp_team_config(tmp_path):
    """Create temporary team_config directory with meta learnings."""
    team_config = tmp_path / "team_config"
    team_config.mkdir()

    # Create minimal base agent file
    base_dir = team_config / "00_base"
    base_dir.mkdir()
    (base_dir / "base_agent.md").write_text("# Base Agent\n\nYou are a helpful agent.")

    # Create meta directory
    meta_dir = team_config / "07_meta"
    meta_dir.mkdir()

    return team_config


@pytest.fixture
def agent_with_team_config(temp_team_config, monkeypatch):
    """Create agent with custom team_config location."""
    monkeypatch.setenv("TEAM_CONFIG_DIR", str(temp_team_config))

    config = AgentConfig(
        role_id="alex_senior_networking",
        name="Alex Chen",
        role_archetype="developer",
        seniority="senior",
        specializations=["networking"],
        model="mock",
        temperature=0.7,
        max_tokens=1000,
    )
    return BaseAgent(config, vllm_endpoint="mock://")


def test_write_meta_learning_to_jsonl(temp_team_config):
    """Test writing meta-learning entry to JSONL file."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Write a learning entry
    entry = {
        "sprint": 1,
        "agent_id": "alex_senior_networking",
        "learning_type": "keep",
        "content": {"text": "Pair rotation improved knowledge sharing"},
        "applied": True,
    }

    with open(jsonl_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Verify file exists and contains entry
    assert jsonl_path.exists()
    lines = jsonl_path.read_text().strip().split("\n")
    assert len(lines) == 1

    # Parse and verify
    parsed = json.loads(lines[0])
    assert parsed["sprint"] == 1
    assert parsed["agent_id"] == "alex_senior_networking"
    assert parsed["learning_type"] == "keep"
    assert parsed["content"]["text"] == "Pair rotation improved knowledge sharing"


def test_read_meta_learnings_filters_by_agent(agent_with_team_config, temp_team_config):
    """Test meta-learnings are filtered by agent_id."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Write learnings for multiple agents
    entries = [
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "Alex learning 1"},
            "applied": True,
        },
        {
            "sprint": 1,
            "agent_id": "jamie_junior_fullstack",
            "learning_type": "keep",
            "content": {"text": "Jamie learning 1"},
            "applied": True,
        },
        {
            "sprint": 2,
            "agent_id": "alex_senior_networking",
            "learning_type": "drop",
            "content": {"text": "Alex learning 2"},
            "applied": True,
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Reload agent prompt
    prompt = agent_with_team_config._load_prompt()

    # Should contain only Alex's learnings
    assert "Alex learning 1" in prompt
    assert "Alex learning 2" in prompt
    # Should NOT contain Jamie's learning
    assert "Jamie learning 1" not in prompt


def test_meta_learnings_loaded_in_prompt(agent_with_team_config, temp_team_config):
    """Test meta-learnings appear in agent's composed prompt."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Write a learning
    entry = {
        "sprint": 3,
        "agent_id": "alex_senior_networking",
        "learning_type": "keep",
        "content": {"text": "Always review network configs before deployment"},
        "applied": True,
    }

    with open(jsonl_path, "w") as f:
        f.write(json.dumps(entry) + "\n")

    # Reload prompt
    prompt = agent_with_team_config._load_prompt()

    # Learning should be in prompt
    assert "Always review network configs before deployment" in prompt
    # Sprint info should be included
    assert "Sprint 3" in prompt or "sprint 3" in prompt.lower()


def test_multiple_learnings_accumulated(agent_with_team_config, temp_team_config):
    """Test multiple learnings for same agent accumulate."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Write multiple learnings
    entries = [
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "Learning 1: Code review is valuable"},
            "applied": True,
        },
        {
            "sprint": 2,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "Learning 2: Test-first development works"},
            "applied": True,
        },
        {
            "sprint": 3,
            "agent_id": "alex_senior_networking",
            "learning_type": "drop",
            "content": {"text": "Learning 3: Skip detailed design docs"},
            "applied": True,
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Reload prompt
    prompt = agent_with_team_config._load_prompt()

    # All learnings should be present
    assert "Learning 1: Code review is valuable" in prompt
    assert "Learning 2: Test-first development works" in prompt
    assert "Learning 3: Skip detailed design docs" in prompt


def test_empty_jsonl_returns_empty_string(agent_with_team_config, temp_team_config):
    """Test empty or missing JSONL file handled gracefully."""
    # No JSONL file exists yet
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"
    assert not jsonl_path.exists()

    # Should not crash
    meta_text = agent_with_team_config._load_meta_learnings(temp_team_config)
    assert meta_text == ""

    # Empty file
    jsonl_path.touch()
    meta_text = agent_with_team_config._load_meta_learnings(temp_team_config)
    assert meta_text == ""


def test_malformed_jsonl_handled(agent_with_team_config, temp_team_config):
    """Test malformed JSONL lines are skipped gracefully."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Write mix of valid and invalid lines
    with open(jsonl_path, "w") as f:
        # Valid entry
        f.write(
            json.dumps(
                {
                    "sprint": 1,
                    "agent_id": "alex_senior_networking",
                    "learning_type": "keep",
                    "content": {"text": "Valid learning"},
                    "applied": True,
                }
            )
            + "\n"
        )
        # Malformed JSON
        f.write("this is not json\n")
        # Empty line
        f.write("\n")
        # Another valid entry
        f.write(
            json.dumps(
                {
                    "sprint": 2,
                    "agent_id": "alex_senior_networking",
                    "learning_type": "drop",
                    "content": {"text": "Another valid learning"},
                    "applied": True,
                }
            )
            + "\n"
        )

    # Should not crash, should load valid entries only
    prompt = agent_with_team_config._load_prompt()

    assert "Valid learning" in prompt
    assert "Another valid learning" in prompt
    assert "this is not json" not in prompt


def test_meta_learning_sprint_tracking(agent_with_team_config, temp_team_config):
    """Test sprint numbers are preserved in learnings."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    entries = [
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "Sprint 1 insight"},
            "applied": True,
        },
        {
            "sprint": 5,
            "agent_id": "alex_senior_networking",
            "learning_type": "puzzle",
            "content": {"text": "Sprint 5 question"},
            "applied": True,
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Read back entries
    with open(jsonl_path, "r") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert lines[0]["sprint"] == 1
    assert lines[1]["sprint"] == 5


def test_meta_learning_types(agent_with_team_config, temp_team_config):
    """Test different learning types (keep, drop, puzzle)."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    entries = [
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "KEEP: Pair programming"},
            "applied": True,
        },
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "drop",
            "content": {"text": "DROP: Long meetings"},
            "applied": True,
        },
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "puzzle",
            "content": {"text": "PUZZLE: Why tests fail randomly?"},
            "applied": True,
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    prompt = agent_with_team_config._load_prompt()

    # All types should appear
    assert "KEEP: Pair programming" in prompt
    assert "DROP: Long meetings" in prompt
    assert "PUZZLE: Why tests fail randomly?" in prompt


def test_prompt_reloads_after_new_learning(agent_with_team_config, temp_team_config):
    """Test prompt can be reloaded to pick up new learnings."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Initial prompt has no learnings
    initial_prompt = agent_with_team_config.prompt
    assert "New learning" not in initial_prompt

    # Add a learning
    entry = {
        "sprint": 1,
        "agent_id": "alex_senior_networking",
        "learning_type": "keep",
        "content": {"text": "New learning from sprint 1"},
        "applied": True,
    }

    with open(jsonl_path, "w") as f:
        f.write(json.dumps(entry) + "\n")

    # Reload prompt (simulates what SprintManager does)
    agent_with_team_config.prompt = agent_with_team_config._load_prompt()

    # New prompt should include learning
    assert "New learning from sprint 1" in agent_with_team_config.prompt


def test_meta_learnings_format_in_prompt(agent_with_team_config, temp_team_config):
    """Test meta-learnings are formatted correctly in prompt."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    entry = {
        "sprint": 2,
        "agent_id": "alex_senior_networking",
        "learning_type": "keep",
        "content": {"text": "Always document network topology changes"},
        "applied": True,
    }

    with open(jsonl_path, "w") as f:
        f.write(json.dumps(entry) + "\n")

    prompt = agent_with_team_config._load_prompt()

    # Should be formatted with context
    # Check for the learning text
    assert "Always document network topology changes" in prompt
    # Check for sprint context
    assert "Sprint 2" in prompt or "sprint 2" in prompt.lower()
    # Check for learning type
    assert "keep" in prompt.lower()


def test_meta_learnings_only_for_matching_agent(agent_with_team_config, temp_team_config):
    """Test agent only loads their own learnings, not others."""
    jsonl_path = temp_team_config / "07_meta" / "meta_learnings.jsonl"

    # Create learnings for different agents
    entries = [
        {
            "sprint": 1,
            "agent_id": "alex_senior_networking",
            "learning_type": "keep",
            "content": {"text": "Alex specific learning"},
            "applied": True,
        },
        {
            "sprint": 1,
            "agent_id": "marcus_mid_backend",
            "learning_type": "keep",
            "content": {"text": "Marcus specific learning"},
            "applied": True,
        },
        {
            "sprint": 1,
            "agent_id": "jamie_junior_fullstack",
            "learning_type": "keep",
            "content": {"text": "Jamie specific learning"},
            "applied": True,
        },
    ]

    with open(jsonl_path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    # Alex's prompt
    prompt = agent_with_team_config._load_prompt()

    # Should have Alex's learning
    assert "Alex specific learning" in prompt
    # Should NOT have others' learnings
    assert "Marcus specific learning" not in prompt
    assert "Jamie specific learning" not in prompt
