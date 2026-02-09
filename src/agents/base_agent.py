"""Base agent class that all agents inherit from."""

import json
import os
import re
from dataclasses import dataclass, field
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
    individual: str = ""                      # Personality file (e.g., "jamie_rodriguez")
    seniority: str = ""                       # junior | mid | senior
    specializations: List[str] = field(default_factory=list)  # List of specialization files
    role_archetype: str = ""                  # developer | tester | leader
    demographics: Dict[str, str] = field(default_factory=dict)  # pronouns, cultural_background, etc.


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
        self._original_config: Optional[AgentConfig] = None
        self._swap_state: Optional[Dict] = None

    def swap_to(self, target_role_id: str, domain: str, proficiency: float, sprint: int):
        """Temporarily reassign this agent to cover a different domain."""
        if self._original_config is None:
            self._original_config = self.config
        self._swap_state = {
            "role_id": target_role_id,
            "domain": domain,
            "proficiency": proficiency,
            "sprint": sprint,
        }
        swap_notice = (
            f"\n\n[PROFILE SWAP ACTIVE]\n"
            f"You are temporarily covering {domain} tasks. "
            f"Proficiency: {proficiency * 100:.0f}%.\n"
            "You are less familiar with this domain — ask more questions, verify assumptions,\n"
            "and expect to work 20% slower than your usual pace."
        )
        self.prompt = self._load_prompt() + swap_notice

    def revert_swap(self):
        """Restore original role configuration."""
        if self._original_config is not None:
            self.config = self._original_config
            self._original_config = None
        self._swap_state = None
        self.prompt = self._load_prompt()

    def decay_swap(self, current_sprint: int, knowledge_decay_sprints: int = 1):
        """Reduce proficiency over time and revert if past decay threshold."""
        if self._swap_state is None:
            return
        sprints_elapsed = current_sprint - self._swap_state["sprint"]
        if sprints_elapsed >= knowledge_decay_sprints:
            self.revert_swap()
        else:
            # Decay proficiency by 10% per sprint
            self._swap_state["proficiency"] = max(
                0.0, self._swap_state["proficiency"] - 0.10 * sprints_elapsed
            )

    @property
    def is_swapped(self) -> bool:
        """Return True if this agent is currently profile-swapped."""
        return self._swap_state is not None

    def _load_prompt(self) -> str:
        """Load and compose agent prompt from layered config files.

        Composition order:
        1. 00_base/base_agent.md (universal)
        2. 01_role_archetypes/{developer,tester,leader}.md
        3. 02_seniority/{junior,mid,senior}.md
        4. 03_specializations/{spec1,spec2,...}.md (multiple)
        5. 04_domain_knowledge/ (layered by seniority)
        6. 05_individuals/{name}.md
        7. Demographic modifiers (applied as text)
        """
        # Determine team_config directory
        # Try to find it from environment or default location
        team_config_dir = Path(os.environ.get("TEAM_CONFIG_DIR", "team_config"))
        if not team_config_dir.exists():
            # Try relative to this file's location
            team_config_dir = Path(__file__).parent.parent.parent / "team_config"

        if not team_config_dir.exists():
            return "You are a helpful software engineering team member."

        parts: List[str] = []

        # 1. Base agent (universal)
        base_path = team_config_dir / "00_base" / "base_agent.md"
        if base_path.exists():
            parts.append(base_path.read_text())

        # 2. Role archetype(s)
        if self.config.role_archetype:
            archetypes = self.config.role_archetype.split("+")  # Support "developer+leader"
            for archetype in archetypes:
                arch_path = team_config_dir / "01_role_archetypes" / f"{archetype.strip()}.md"
                if arch_path.exists():
                    parts.append(arch_path.read_text())

        # 3. Seniority level
        if self.config.seniority:
            seniority_path = team_config_dir / "02_seniority" / f"{self.config.seniority}.md"
            if seniority_path.exists():
                parts.append(seniority_path.read_text())

        # 4. Specializations (multiple allowed)
        for spec in self.config.specializations:
            spec_path = team_config_dir / "03_specializations" / f"{spec}.md"
            if spec_path.exists():
                parts.append(spec_path.read_text())

        # 5. Domain knowledge (layered by seniority)
        domain_dir = team_config_dir / "04_domain_knowledge"
        if domain_dir.exists():
            # Always load base product context
            base_domain = domain_dir / "00_saas_project_management.md"
            if base_domain.exists():
                parts.append(base_domain.read_text())

            # Load seniority-specific domain knowledge (cumulative)
            if self.config.seniority == "junior":
                junior_domain = domain_dir / "01_junior_domain.md"
                if junior_domain.exists():
                    parts.append(junior_domain.read_text())
            elif self.config.seniority == "mid":
                junior_domain = domain_dir / "01_junior_domain.md"
                mid_domain = domain_dir / "02_mid_domain.md"
                if junior_domain.exists():
                    parts.append(junior_domain.read_text())
                if mid_domain.exists():
                    parts.append(mid_domain.read_text())
            elif self.config.seniority == "senior":
                junior_domain = domain_dir / "01_junior_domain.md"
                mid_domain = domain_dir / "02_mid_domain.md"
                senior_domain = domain_dir / "03_senior_domain.md"
                if junior_domain.exists():
                    parts.append(junior_domain.read_text())
                if mid_domain.exists():
                    parts.append(mid_domain.read_text())
                if senior_domain.exists():
                    parts.append(senior_domain.read_text())

        # 6. Individual personality
        if self.config.individual:
            individual_path = team_config_dir / "05_individuals" / f"{self.config.individual}.md"
            if individual_path.exists():
                parts.append(individual_path.read_text())

        # 7. Demographic modifiers (injected as text)
        if self.config.demographics:
            demo_text = "\n\n[DEMOGRAPHIC CONTEXT]\n"
            if "pronouns" in self.config.demographics:
                demo_text += f"Pronouns: {self.config.demographics['pronouns']}\n"
            if "cultural_background" in self.config.demographics:
                demo_text += f"Cultural Background: {self.config.demographics['cultural_background']}\n"
            parts.append(demo_text)

        # 8. Meta-learnings (dynamic, loaded from JSONL)
        meta_learnings = self._load_meta_learnings(team_config_dir)
        if meta_learnings:
            parts.append(meta_learnings)

        return "\n\n---\n\n".join(parts)

    def _load_meta_learnings(self, team_config_dir: Path) -> str:
        """Load meta-learnings from 04_meta/meta_learnings.jsonl for this agent."""
        jsonl_path = team_config_dir / "04_meta" / "meta_learnings.jsonl"
        if not jsonl_path.exists():
            return ""

        learnings: List[str] = []
        try:
            with open(jsonl_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    # Match learnings for this agent's role_id
                    if entry.get("agent_id") == self.config.role_id:
                        sprint_num = entry.get("sprint", "?")
                        learning_type = entry.get("learning_type", "learning")
                        content = entry.get("content", {})
                        text = content.get("text", "")
                        if text:
                            learnings.append(f"- **Sprint {sprint_num} ({learning_type})**: {text}")
        except (json.JSONDecodeError, IOError):
            return ""

        if not learnings:
            return ""

        header = "\n\n[META-LEARNINGS]\n"
        header += "Insights from past retrospectives that should inform your behavior:\n\n"
        return header + "\n".join(learnings)

    def _is_mock_mode(self) -> bool:
        """Return True if mock mode is active."""
        return (
            os.environ.get("MOCK_LLM", "").lower() == "true"
            or self.vllm_endpoint.startswith("mock://")
        )

    def _mock_response(self, message: str) -> str:
        """Return a canned response based on role_id and message context."""
        msg_lower = message.lower()
        # Approval/review prompts → always approve in mock mode
        if any(kw in msg_lower for kw in ("approve", "review", "accept", "definition of done")):
            return f"approve — looks good from {self.config.role_id}"
        # Story/planning selection → echo back first story IDs found
        if "us-" in msg_lower:
            import re
            ids = re.findall(r"us-\d+", msg_lower)
            if ids:
                return "\n".join(ids[:3])
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
