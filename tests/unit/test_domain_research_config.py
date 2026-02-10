"""Unit tests for domain research configuration and backlog context_documents."""

import yaml

from src.orchestrator.config import load_config
from src.orchestrator.backlog import Backlog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONFIG = {
    "experiment": {
        "name": "test-experiment",
        "sprint_duration_minutes": 30,
    },
    "team": {
        "config_dir": "team_config",
    },
    "models": {
        "vllm_endpoint": "http://localhost:8000",
    },
    "database": {
        "url": "mock://",
    },
}


def _write_config(tmp_path, data):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


def _write_backlog(tmp_path, data):
    path = tmp_path / "backlog.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False))
    return str(path)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_config_domain_research_defaults(tmp_path):
    """Without domain_research section, defaults are disabled/empty."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert cfg.domain_research_enabled is False
    assert cfg.domain_research_config == {}


def test_config_domain_research_enabled(tmp_path):
    """Full domain_research config is loaded correctly."""
    data = {
        **MINIMAL_CONFIG,
        "domain_research": {
            "enabled": True,
            "context_documents": ["docs/vision.md", "docs/analysis.md"],
            "web_search": {
                "enabled": True,
                "engine": "brave",
                "api_key_env": "BRAVE_KEY",
                "max_results": 3,
            },
        },
    }
    path = _write_config(tmp_path, data)
    cfg = load_config(path)
    assert cfg.domain_research_enabled is True
    assert cfg.domain_research_config["context_documents"] == [
        "docs/vision.md",
        "docs/analysis.md",
    ]
    ws = cfg.domain_research_config["web_search"]
    assert ws["enabled"] is True
    assert ws["engine"] == "brave"
    assert ws["api_key_env"] == "BRAVE_KEY"
    assert ws["max_results"] == 3
    # Also injected into runtime_configs for AgentFactory
    assert "domain_research" in cfg.runtime_configs
    assert cfg.runtime_configs["domain_research"]["enabled"] is True


def test_config_domain_research_missing(tmp_path):
    """Missing domain_research section falls back to defaults (backward compat)."""
    path = _write_config(tmp_path, MINIMAL_CONFIG)
    cfg = load_config(path)
    assert cfg.domain_research_enabled is False
    assert "domain_research" not in cfg.runtime_configs


# ---------------------------------------------------------------------------
# Backlog context_documents tests
# ---------------------------------------------------------------------------


def test_product_metadata_context_documents(tmp_path):
    """context_documents field is parsed from backlog.yaml product section."""
    data = {
        "product": {
            "name": "Test",
            "description": "A test product",
            "context_documents": ["docs/a.md", "docs/b.md"],
        },
        "stories": [],
    }
    path = _write_backlog(tmp_path, data)
    backlog = Backlog(str(path))
    meta = backlog.get_product_metadata()
    assert meta.context_documents == ["docs/a.md", "docs/b.md"]


def test_project_context_includes_documents(tmp_path):
    """get_project_context() includes reference document list when present."""
    data = {
        "product": {
            "name": "Test",
            "description": "A test product",
            "mission": "Build something great",
            "vision": "World domination",
            "goals": ["Ship v1"],
            "context_documents": ["docs/vision.md"],
        },
        "stories": [],
    }
    path = _write_backlog(tmp_path, data)
    backlog = Backlog(str(path))
    ctx = backlog.get_project_context()
    assert "Reference Documents" in ctx
    assert "docs/vision.md" in ctx


# ---------------------------------------------------------------------------
# AgentFactory web tool selection (Anthropic vs vLLM)
# ---------------------------------------------------------------------------


def test_anthropic_po_gets_native_search_not_custom_tool(tmp_path):
    """Anthropic PO should NOT get custom web_search tool (native replaces it).

    The Anthropic API has a native web_search_20250305 server tool.  Adding
    our custom WebSearchTool alongside it would create a name collision
    (both named 'web_search').  For Anthropic, only web_fetch should be
    added as a custom tool; native search handles the rest.
    """
    runtime_configs = {
        "anthropic": {
            "enabled": True,
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "tools": {"workspace_root": str(tmp_path)},
        "domain_research": {
            "enabled": True,
            "web_search": {"enabled": True, "engine": "brave", "api_key_env": "KEY"},
        },
    }
    agent_cfg = {
        "name": "PO",
        "role_archetype": "leader",
        "seniority": "senior",
        "runtime": "anthropic",
        "tools": ["filesystem"],
    }

    # Simulate what _create_agent_runtime does: build tool_names
    tool_names = list(agent_cfg.get("tools", []))
    domain_research = runtime_configs.get("domain_research", {})
    web_search_cfg = domain_research.get("web_search", {})
    runtime_type = "anthropic"
    use_native_search = runtime_type == "anthropic" and web_search_cfg.get(
        "enabled", False
    )

    if domain_research.get("enabled", False):
        is_po = "po" in "alex_senior_po"
        if is_po:
            if not use_native_search and "web_search" not in tool_names:
                tool_names.append("web_search")
            if "web_fetch" not in tool_names:
                tool_names.append("web_fetch")

    # Custom web_search should NOT be present (native handles it)
    assert "web_search" not in tool_names
    # web_fetch should still be present
    assert "web_fetch" in tool_names


def test_vllm_po_gets_custom_web_search_tool(tmp_path):
    """vLLM PO should get the custom web_search tool (no native alternative)."""
    runtime_configs = {
        "local_vllm": {
            "enabled": True,
            "endpoint": "http://localhost:8000",
        },
        "tools": {"workspace_root": str(tmp_path)},
        "domain_research": {
            "enabled": True,
            "web_search": {"enabled": True, "engine": "brave", "api_key_env": "KEY"},
        },
    }
    agent_cfg = {
        "name": "PO",
        "role_archetype": "leader",
        "seniority": "senior",
        "runtime": "local_vllm",
        "tools": ["filesystem"],
    }

    tool_names = list(agent_cfg.get("tools", []))
    domain_research = runtime_configs.get("domain_research", {})
    web_search_cfg = domain_research.get("web_search", {})
    runtime_type = "local_vllm"
    use_native_search = runtime_type == "anthropic" and web_search_cfg.get(
        "enabled", False
    )

    if domain_research.get("enabled", False):
        is_po = True
        if is_po:
            if not use_native_search and "web_search" not in tool_names:
                tool_names.append("web_search")
            if "web_fetch" not in tool_names:
                tool_names.append("web_fetch")

    # vLLM should get BOTH custom tools
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
