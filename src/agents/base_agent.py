"""Base agent class that all agents inherit from."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
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


# Canned responses used in mock mode, keyed by role_id
_MOCK_RESPONSES: Dict[str, str] = {
    "dev_lead": "Approved. The approach looks solid.",
    "qa_lead": "Tests look good. Coverage is sufficient.",
    "po": "Accepted. This meets the acceptance criteria.",
    "dev_sr_devops": "Infrastructure change looks safe to deploy.",
    "dev_sr_networking": "Network configuration is correct.",
    "dev_mid_backend": "Backend implementation is clean.",
    "dev_mid_frontend": "Frontend component renders correctly.",
    "dev_jr_fullstack_a": "I have a question: why do we do it this way?",
    "dev_jr_fullstack_b": "I think this looks right, but I'm not 100% sure.",
    "tester_e2e": "End-to-end tests passed. No regressions found.",
    "tester_integration": "Integration tests passed.",
}


class BaseAgent:
    """LLM-backed agent with a composed system prompt."""

    def __init__(self, config: AgentConfig, vllm_endpoint: str):
        self.config = config
        self.vllm_endpoint = vllm_endpoint
        self.prompt = self._load_prompt()
        self.conversation_history: List[Dict] = []
        self.learning_history: List[Dict] = []

    def _load_prompt(self) -> str:
        """Load and compose agent prompt from config files.

        Layers:
        1. 00_base/base_agent.md  (universal)
        2. 01_role_archetypes/<archetype>.md  (parsed from **Inherits**: line)
        3. Individual profile at prompt_path
        """
        if not self.config.prompt_path:
            return "You are a helpful software engineering team member."

        profile_path = Path(self.config.prompt_path)
        if not profile_path.exists():
            return "You are a helpful software engineering team member."

        team_config_dir = profile_path.parent.parent  # 02_individuals/../ = team_config/

        # Parse **Inherits**: line from individual profile
        profile_text = profile_path.read_text()
        inherit_match = re.search(r"\*\*Inherits\*\*:?\s*(.+)", profile_text)
        archetype_files: List[str] = []
        if inherit_match:
            raw = inherit_match.group(1)
            # Extract filenames like developer.md, leader.md, base_agent.md
            archetype_files = re.findall(r"`?(\w[\w.-]*\.md)`?", raw)

        parts: List[str] = []

        # 1. Base prompt
        base_path = team_config_dir / "00_base" / "base_agent.md"
        if base_path.exists():
            parts.append(base_path.read_text())

        # 2. Role archetypes (exclude base_agent.md already loaded)
        archetypes_dir = team_config_dir / "01_role_archetypes"
        for fname in archetype_files:
            if fname == "base_agent.md":
                continue
            arch_path = archetypes_dir / fname
            if arch_path.exists():
                parts.append(arch_path.read_text())

        # 3. Individual profile
        parts.append(profile_text)

        return "\n\n---\n\n".join(parts)

    def _is_mock_mode(self) -> bool:
        """Return True if mock mode is active."""
        return (
            os.environ.get("MOCK_LLM", "").lower() == "true"
            or self.vllm_endpoint.startswith("mock://")
        )

    def _mock_response(self, message: str) -> str:
        """Return a canned response based on role_id."""
        default = f"[{self.config.role_id}] Response to: {message[:50]}"
        return _MOCK_RESPONSES.get(self.config.role_id, default)

    async def generate(self, user_message: str, context: Optional[Dict] = None) -> str:
        """Generate response using vLLM (or mock mode)."""
        self.conversation_history.append({"role": "user", "content": user_message})

        if self._is_mock_mode():
            response = self._mock_response(user_message)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.vllm_endpoint}/v1/completions",
                json={
                    "model": self.config.model,
                    "prompt": self._build_prompt(user_message, context),
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                },
            )
            text = resp.json()["choices"][0]["text"]

        self.conversation_history.append({"role": "assistant", "content": text})
        return text

    def _build_prompt(self, message: str, context: Optional[Dict] = None) -> str:
        """Build complete prompt with system instructions + context + message."""
        parts = [self.prompt]
        if context:
            parts.append(f"\nCurrent Context:\n{context}")
        parts.append(f"\n{message}")
        return "\n".join(parts)
