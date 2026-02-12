"""Factory for creating agent runtimes.

Supports a pluggable registry so external consumers (e.g. dojo) can
register custom runtime types.
"""

import os
from typing import Callable, Dict, List, Optional

from .base import AgentRuntime
from .vllm_runtime import VLLMRuntime
from .anthropic_runtime import AnthropicRuntime
from ...tools.agent_tools import create_tools

# Module-level registry
_RUNTIME_REGISTRY: Dict[str, Callable[..., AgentRuntime]] = {}
_DEFAULTS_REGISTERED: bool = False


def register_runtime(name: str, factory_fn: Callable[..., AgentRuntime]) -> None:
    """Register a custom runtime type.

    Args:
        name: Runtime type name (e.g., "training_candidate").
        factory_fn: Callable(config: Dict, tools: List[Tool]) -> AgentRuntime.
    """
    _RUNTIME_REGISTRY[name] = factory_fn


def _default_registrations() -> None:
    """Register built-in runtimes on first use."""
    global _DEFAULTS_REGISTERED
    if _DEFAULTS_REGISTERED:
        return
    _DEFAULTS_REGISTERED = True
    if "local_vllm" not in _RUNTIME_REGISTRY:
        _RUNTIME_REGISTRY["local_vllm"] = lambda cfg, tools: VLLMRuntime(cfg, tools)
    if "anthropic" not in _RUNTIME_REGISTRY:
        _RUNTIME_REGISTRY["anthropic"] = lambda cfg, tools: AnthropicRuntime(cfg, tools)


def registered_runtime_types() -> List[str]:
    """Return sorted list of registered runtime type names."""
    _default_registrations()
    return sorted(_RUNTIME_REGISTRY.keys())


def create_runtime(
    runtime_type: str,
    runtime_config: Dict,
    tool_names: List[str],
    workspace_root: str,
    tool_config: Optional[Dict] = None,
) -> AgentRuntime:
    """Create an agent runtime instance.

    Args:
        runtime_type: Registered runtime type name.
        runtime_config: Runtime-specific configuration.
        tool_names: List of tool names to make available.
        workspace_root: Root directory for file operations.
        tool_config: Optional tool-specific configuration.

    Returns:
        Instantiated AgentRuntime.

    Raises:
        ValueError: If runtime_type is unknown.
    """
    _default_registrations()

    # Create tools
    tools = create_tools(tool_names, workspace_root, tool_config or {})

    # Look up factory in registry
    factory_fn = _RUNTIME_REGISTRY.get(runtime_type)
    if factory_fn is None:
        raise ValueError(
            f"Unknown runtime type: {runtime_type}. "
            f"Available: {sorted(_RUNTIME_REGISTRY.keys())}"
        )
    return factory_fn(runtime_config, tools)


def get_runtime_config(
    agent_config: Dict,
    global_runtime_configs: Dict,
    runtime_mode_override: Optional[str] = None,
) -> tuple[str, Dict]:
    """Get runtime type and config for an agent.

    Args:
        agent_config: Agent-specific configuration from config.yaml.
        global_runtime_configs: Global runtime configurations.
        runtime_mode_override: Optional override (e.g., from CLI or env var).

    Returns:
        Tuple of (runtime_type, runtime_config).
    """
    _default_registrations()

    # Check for override
    runtime_mode = runtime_mode_override or os.environ.get("AGENT_RUNTIME_MODE")

    if runtime_mode == "local":
        # Force all agents to local
        runtime_type = "local_vllm"
    elif runtime_mode == "anthropic":
        # Force all agents to Anthropic
        runtime_type = "anthropic"
    else:
        # Use agent-specific runtime from config
        runtime_type = agent_config.get("runtime", "local_vllm")

    # Validate runtime type
    if runtime_type not in _RUNTIME_REGISTRY:
        raise ValueError(
            f"Unknown runtime type: {runtime_type}. "
            f"Available: {sorted(_RUNTIME_REGISTRY.keys())}"
        )

    # Get runtime configuration
    runtime_config = global_runtime_configs.get(runtime_type, {})
    runtime_config = runtime_config.copy()

    # Override model if specified in agent config
    if "model" in agent_config:
        runtime_config["model"] = agent_config["model"]

    return runtime_type, runtime_config
