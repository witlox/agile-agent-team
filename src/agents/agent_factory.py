"""Factory for creating all team agents."""

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
        team_type: str = "",
    ):
        self.config_dir = config_dir
        self.vllm_endpoint = vllm_endpoint
        self.agent_model_configs: Dict[str, Dict] = agent_model_configs or {}
        self.runtime_configs: Dict[str, Dict] = runtime_configs or {}
        self.runtime_mode_override = runtime_mode_override
        self.default_team_type = team_type

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
                    runtime = self._create_agent_runtime(
                        agent_id, agent_cfg, workspace_root
                    )

                agent = BaseAgent(config, self.vllm_endpoint, runtime=runtime)
                agents.append(agent)

        return agents

    def _create_agent_runtime(
        self, agent_id: str, agent_cfg: Dict, workspace_root: str
    ):
        """Create runtime for an agent if configured."""
        try:
            # Get runtime type and config
            runtime_type, runtime_config = get_runtime_config(
                agent_cfg, self.runtime_configs, self.runtime_mode_override
            )

            # Get tool names for this agent
            tool_names = list(agent_cfg.get("tools", []))
            if not tool_names:
                return None

            # Auto-add web tools to PO if domain research is enabled
            domain_research = self.runtime_configs.get("domain_research", {})
            web_search_cfg = domain_research.get("web_search", {})
            use_native_search = runtime_type == "anthropic" and web_search_cfg.get(
                "enabled", False
            )
            if domain_research.get("enabled", False):
                is_po = "po" in agent_id or agent_cfg.get("role_archetype") == "leader"
                if is_po:
                    # For Anthropic runtime, skip the custom web_search tool —
                    # the native server tool handles search.  For vLLM, add it.
                    if not use_native_search and "web_search" not in tool_names:
                        tool_names.append("web_search")
                    if "web_fetch" not in tool_names:
                        tool_names.append("web_fetch")

            # Get tool configuration (merge web search config into tool config)
            tools_config = dict(self.runtime_configs.get("tools", {}))
            if web_search_cfg:
                tools_config["web_search"] = web_search_cfg

            # For Anthropic runtime, enable native web search if configured
            if (
                runtime_type == "anthropic"
                and web_search_cfg.get("enabled", False)
                and ("po" in agent_id or agent_cfg.get("role_archetype") == "leader")
            ):
                runtime_config = dict(runtime_config)
                runtime_config["web_search_enabled"] = True
                runtime_config["web_search_max_uses"] = web_search_cfg.get(
                    "max_results", 5
                )

            # Create runtime
            runtime = create_runtime(
                runtime_type=runtime_type,
                runtime_config=runtime_config,
                tool_names=tool_names,
                workspace_root=workspace_root,
                tool_config=tools_config,
            )

            return runtime

        except Exception as e:
            # Log error but don't fail agent creation
            print(f"Warning: Could not create runtime for {agent_id}: {e}")
            return None

    def _create_agent_config(self, agent_id: str, agent_cfg: Dict) -> AgentConfig:
        """Create AgentConfig from compositional structure.

        Supports both new (primary_specialization + auxiliary_specializations)
        and old (flat specializations list) config formats. When using the old
        format, the first item becomes the primary and the rest become auxiliary.
        """
        seniority = agent_cfg.get("seniority", "")

        # Parse specializations (supports old and new format)
        primary_spec = agent_cfg.get("primary_specialization", "")
        aux_specs = list(agent_cfg.get("auxiliary_specializations", []))

        if not primary_spec and "specializations" in agent_cfg:
            # Backward compat: first item = primary, rest = auxiliary
            old_specs = agent_cfg["specializations"]
            if old_specs:
                primary_spec = old_specs[0]
                aux_specs = old_specs[1:]

        # Validation: junior max 1 auxiliary
        if seniority == "junior" and len(aux_specs) > 1:
            aux_specs = aux_specs[:1]

        # Validation: max 2 auxiliary for everyone
        if len(aux_specs) > 2:
            aux_specs = aux_specs[:2]

        # Compute combined list for backward compatibility
        all_specs: list[str] = []
        if primary_spec:
            all_specs.append(primary_spec)
        all_specs.extend(aux_specs)

        return AgentConfig(
            role_id=agent_id,
            name=agent_cfg.get("name", agent_id),
            individual=agent_cfg.get("individual", ""),
            seniority=seniority,
            primary_specialization=primary_spec,
            auxiliary_specializations=aux_specs,
            specializations=all_specs,
            role_archetype=agent_cfg.get("role_archetype", "developer"),
            team_type=agent_cfg.get("team_type", self.default_team_type),
            team_id=agent_cfg.get("team_id", ""),
            demographics=agent_cfg.get("demographics", {}),
            model=agent_cfg.get("model", _DEFAULT_MODEL),
            temperature=float(agent_cfg.get("temperature", _DEFAULT_TEMPERATURE)),
            max_tokens=int(agent_cfg.get("max_tokens", _DEFAULT_MAX_TOKENS)),
        )
