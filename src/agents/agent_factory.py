"""Factory for creating all team agents."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from .base_agent import BaseAgent, AgentConfig


# Maps filename prefix patterns to config category keys in config.yaml models.agents.*
_PREFIX_TO_CATEGORY = {
    "dev_lead": "dev_lead",
    "qa_lead": "qa_lead",
    "po": "po",
    "dev_sr_": "developers_sr",
    "dev_mid_": "developers_mid",
    "dev_jr_": "developers_jr",
    "tester_": "testers",
}

_DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_MAX_TOKENS = 2048


def _resolve_category(stem: str) -> str:
    """Map a profile filename stem to the config category key."""
    for prefix, category in _PREFIX_TO_CATEGORY.items():
        if stem == prefix or stem.startswith(prefix):
            return category
    return stem


class AgentFactory:
    """Creates BaseAgent instances from team_config profile files."""

    def __init__(
        self,
        config_dir: str,
        vllm_endpoint: str,
        agent_model_configs: Optional[Dict[str, Dict]] = None,
    ):
        self.config_dir = Path(config_dir)
        self.vllm_endpoint = vllm_endpoint
        self.agent_model_configs: Dict[str, Dict] = agent_model_configs or {}

    async def create_all_agents(self) -> List[BaseAgent]:
        """Load all agent configurations and create instances."""
        agents: List[BaseAgent] = []

        individuals_dir = self.config_dir / "02_individuals"
        for profile_file in sorted(individuals_dir.glob("*.md")):
            config = self._parse_agent_config(profile_file)
            agent = BaseAgent(config, self.vllm_endpoint)
            agents.append(agent)

        return agents

    def _parse_agent_config(self, profile_path: Path) -> AgentConfig:
        """Parse agent profile to extract config.

        Reads markdown, extracts **Name** and **Model** fields,
        maps filename to a config category for temperature/max_tokens.
        """
        text = profile_path.read_text()

        # Extract **Name**: ...
        name_match = re.search(r"\*\*Name\*\*:?\s*(.+)", text)
        if name_match:
            name = name_match.group(1).strip()
        else:
            # Fall back to title heading or stem
            title_match = re.match(r"#\s+(.+)", text)
            name = title_match.group(1).strip() if title_match else profile_path.stem

        # Extract **Model**: ...
        model_match = re.search(r"\*\*Model\*\*:?\s*(.+)", text)
        model_from_profile = model_match.group(1).strip() if model_match else ""

        stem = profile_path.stem
        category = _resolve_category(stem)

        # Look up model settings from agent_model_configs (config.yaml)
        cat_config = self.agent_model_configs.get(category, {})
        model = cat_config.get("model", model_from_profile or _DEFAULT_MODEL)
        temperature = float(cat_config.get("temperature", _DEFAULT_TEMPERATURE))
        max_tokens = int(cat_config.get("max_tokens", _DEFAULT_MAX_TOKENS))

        return AgentConfig(
            role_id=stem,
            name=name,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_path=str(profile_path.resolve()),
        )
