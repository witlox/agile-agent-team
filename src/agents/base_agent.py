"""Base agent class that all agents inherit from."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import httpx

@dataclass
class AgentConfig:
    role_id: str
    name: str
    model: str
    temperature: float
    max_tokens: int
    prompt_path: str

class BaseAgent:
    def __init__(self, config: AgentConfig, vllm_endpoint: str):
        self.config = config
        self.vllm_endpoint = vllm_endpoint
        self.prompt = self._load_prompt()
        self.conversation_history = []
        self.learning_history = []
        
    def _load_prompt(self) -> str:
        """Load and compose agent prompt from config files."""
        # Load base + archetype + individual profile
        # Merge into complete system prompt
        pass
    
    async def generate(self, user_message: str, context: Dict = None) -> str:
        """Generate response using vLLM."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.vllm_endpoint}/v1/completions",
                json={
                    "model": self.config.model,
                    "prompt": self._build_prompt(user_message, context),
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                }
            )
            return response.json()["choices"][0]["text"]
    
    def _build_prompt(self, message: str, context: Dict = None) -> str:
        """Build complete prompt with system instructions + context + message."""
        parts = [self.prompt]
        if context:
            parts.append(f"\nCurrent Context:\n{context}")
        parts.append(f"\n{message}")
        return "\n".join(parts)
