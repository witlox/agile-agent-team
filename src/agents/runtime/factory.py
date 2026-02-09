"""Factory for creating agent runtimes."""

import os
from typing import Dict, List, Optional

from .base import AgentRuntime
from .vllm_runtime import VLLMRuntime
from .anthropic_runtime import AnthropicRuntime
from ...tools.agent_tools import create_tools


def create_runtime(
    runtime_type: str,
    runtime_config: Dict,
    tool_names: List[str],
    workspace_root: str,
    tool_config: Optional[Dict] = None,
) -> AgentRuntime:
    """Create an agent runtime instance.

    Args:
        runtime_type: "anthropic" or "local_vllm"
        runtime_config: Runtime-specific configuration
        tool_names: List of tool names to make available
        workspace_root: Root directory for file operations
        tool_config: Optional tool-specific configuration

    Returns:
        Instantiated AgentRuntime

    Raises:
        ValueError: If runtime_type is unknown
    """
    # Create tools
    tools = create_tools(tool_names, workspace_root, tool_config or {})

    # Instantiate runtime
    if runtime_type == "local_vllm":
        return VLLMRuntime(runtime_config, tools)
    elif runtime_type == "anthropic":
        return AnthropicRuntime(runtime_config, tools)
    else:
        raise ValueError(
            f"Unknown runtime type: {runtime_type}. "
            f"Available: local_vllm, anthropic"
        )


def get_runtime_config(
    agent_config: Dict,
    global_runtime_configs: Dict,
    runtime_mode_override: Optional[str] = None,
) -> tuple[str, Dict]:
    """Get runtime type and config for an agent.

    Args:
        agent_config: Agent-specific configuration from config.yaml
        global_runtime_configs: Global runtime configurations
        runtime_mode_override: Optional override (e.g., from CLI or env var)

    Returns:
        Tuple of (runtime_type, runtime_config)
    """
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

    # Get runtime configuration
    if runtime_type == "local_vllm":
        runtime_config = global_runtime_configs.get("local_vllm", {})
        runtime_config = runtime_config.copy()

        # Override model if specified in agent config
        if "model" in agent_config:
            runtime_config["model"] = agent_config["model"]

    elif runtime_type == "anthropic":
        runtime_config = global_runtime_configs.get("anthropic", {})
        runtime_config = runtime_config.copy()

        # Override model if specified in agent config
        if "model" in agent_config:
            runtime_config["model"] = agent_config["model"]
    else:
        raise ValueError(f"Unknown runtime type: {runtime_type}")

    return runtime_type, runtime_config
