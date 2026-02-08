"""Factory for creating all team agents."""

from pathlib import Path
from typing import List
from .base_agent import BaseAgent, AgentConfig

class AgentFactory:
    def __init__(self, config_dir: str, vllm_endpoint: str):
        self.config_dir = Path(config_dir)
        self.vllm_endpoint = vllm_endpoint
    
    async def create_all_agents(self) -> List[BaseAgent]:
        """Load all agent configurations and create instances."""
        
        agents = []
        
        # Load individual agent configs
        individuals_dir = self.config_dir / "02_individuals"
        
        for profile_file in individuals_dir.glob("*.md"):
            config = self._parse_agent_config(profile_file)
            agent = BaseAgent(config, self.vllm_endpoint)
            agents.append(agent)
        
        return agents
    
    def _parse_agent_config(self, profile_path: Path) -> AgentConfig:
        """Parse agent profile to extract config."""
        # Read markdown file
        # Extract model, role_id, etc from headers
        pass
