"""Factory for creating all team agents."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from .base_agent import BaseAgent, AgentConfig
from .runtime.factory import create_runtime, get_runtime_config


_DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 2048


class AgentFactory:
    """Creates BaseAgent instances from config.yaml agent definitions."""

    def __init__(
        self,
        config_dir: str,
        vllm_endpoint: str,
        agent_model_configs: Optional[Dict[str, Dict]] = None,
        runtime_configs: Optional[Dict[str, Dict]] = None,
        runtime_mode_override: Optional[str] = None,
    ):
        self.config_dir = config_dir
        self.vllm_endpoint = vllm_endpoint
        self.agent_model_configs: Dict[str, Dict] = agent_model_configs or {}
        self.runtime_configs: Dict[str, Dict] = runtime_configs or {}
        self.runtime_mode_override = runtime_mode_override

    async def create_all_agents(self) -> List[BaseAgent]:
        """Load all agent configurations and create instances with runtimes."""
        agents: List[BaseAgent] = []

        # Get workspace root from runtime config
        tools_config = self.runtime_configs.get("tools", {})
        workspace_root = tools_config.get("workspace_root", "/tmp/agent-workspace")

        # Ensure workspace exists
        Path(workspace_root).mkdir(parents=True, exist_ok=True)

        for agent_id, agent_cfg in self.agent_model_configs.items():
            if isinstance(agent_cfg, dict):
                config = self._create_agent_config(agent_id, agent_cfg)

                # Create runtime if agent has tools configured
                runtime = None
                if "tools" in agent_cfg and agent_cfg["tools"]:
                    runtime = self._create_agent_runtime(agent_id, agent_cfg, workspace_root)

                agent = BaseAgent(config, self.vllm_endpoint, runtime=runtime)
                agents.append(agent)

        return agents

    def _create_agent_runtime(
        self,
        agent_id: str,
        agent_cfg: Dict,
        workspace_root: str
    ):
        """Create runtime for an agent if configured."""
        try:
            # Get runtime type and config
            runtime_type, runtime_config = get_runtime_config(
                agent_cfg,
                self.runtime_configs,
                self.runtime_mode_override
            )

            # Get tool names for this agent
            tool_names = agent_cfg.get("tools", [])
            if not tool_names:
                return None

            # Get tool configuration
            tools_config = self.runtime_configs.get("tools", {})

            # Create runtime
            runtime = create_runtime(
                runtime_type=runtime_type,
                runtime_config=runtime_config,
                tool_names=tool_names,
                workspace_root=workspace_root,
                tool_config=tools_config
            )

            return runtime

        except Exception as e:
            # Log error but don't fail agent creation
            print(f"Warning: Could not create runtime for {agent_id}: {e}")
            return None

    def _create_agent_config(self, agent_id: str, agent_cfg: Dict) -> AgentConfig:
        """Create AgentConfig from compositional structure (individual + seniority + specializations)."""
        return AgentConfig(
            role_id=agent_id,
            name=agent_cfg.get("name", agent_id),
            individual=agent_cfg.get("individual", ""),
            seniority=agent_cfg.get("seniority", ""),
            specializations=agent_cfg.get("specializations", []),
            role_archetype=agent_cfg.get("role_archetype", "developer"),
            demographics=agent_cfg.get("demographics", {}),
            model=agent_cfg.get("model", _DEFAULT_MODEL),
            temperature=float(agent_cfg.get("temperature", _DEFAULT_TEMPERATURE)),
            max_tokens=int(agent_cfg.get("max_tokens", _DEFAULT_MAX_TOKENS)),
        )
