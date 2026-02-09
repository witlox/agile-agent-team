"""Factory for creating all team agents."""

from typing import Dict, List, Optional

from .base_agent import BaseAgent, AgentConfig


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
    ):
        self.config_dir = config_dir  # Kept for potential future use
        self.vllm_endpoint = vllm_endpoint
        self.agent_model_configs: Dict[str, Dict] = agent_model_configs or {}

    async def create_all_agents(self) -> List[BaseAgent]:
        """Load all agent configurations and create instances from config.yaml."""
        agents: List[BaseAgent] = []

        for agent_id, agent_cfg in self.agent_model_configs.items():
            if isinstance(agent_cfg, dict):
                config = self._create_agent_config(agent_id, agent_cfg)
                agent = BaseAgent(config, self.vllm_endpoint)
                agents.append(agent)

        return agents

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
