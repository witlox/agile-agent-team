#!/bin/bash

# Create core Python modules

# Agent base class
cat > src/agents/base_agent.py << 'PY'
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
PY

# Pairing engine
cat > src/agents/pairing.py << 'PY'
"""Pairing engine for dialogue-driven collaborative programming."""

import asyncio
from typing import Tuple, List
from .base_agent import BaseAgent

class PairingEngine:
    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents
        self.active_sessions = []
        
    def get_available_pairs(self) -> List[Tuple[BaseAgent, BaseAgent]]:
        """Find agents available for pairing."""
        # Match based on task needs and availability
        pass
    
    async def run_pairing_session(self, pair: Tuple[BaseAgent, BaseAgent], task: Dict):
        """Execute TDD pairing session with dialogue checkpoints."""
        
        driver, navigator = pair
        
        # Phase 1: Design dialogue
        approach = await self.brainstorm_approaches(driver, navigator, task)
        
        # Phase 2: TDD cycles with checkpoints
        implementation = await self.collaborative_implementation(
            driver, navigator, task, approach
        )
        
        # Phase 3: Consensus
        approved = await self.get_consensus(driver, navigator, implementation)
        
        if approved:
            await self.commit(implementation, pair, task)
        else:
            await self.escalate(pair, task, implementation)
    
    async def brainstorm_approaches(self, driver, navigator, task):
        """Initial design discussion between pair."""
        # Both propose approaches
        # Run dialogue until consensus
        pass
    
    async def collaborative_implementation(self, driver, navigator, task, approach):
        """TDD implementation with checkpoint dialogues."""
        # Iterative: write test, implement, checkpoint dialogue, repeat
        pass
    
    async def wait_for_completion(self):
        """Wait for all active pairing sessions to finish."""
        await asyncio.gather(*self.active_sessions)
PY

# Shared context database
cat > src/tools/shared_context.py << 'PY'
"""Shared context database for team state."""

import asyncpg
import json
from typing import Dict, List, Optional

class SharedContextDB:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        """Create connection pool and initialize schema."""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self._create_schema()
    
    async def _create_schema(self):
        """Create database tables."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS kanban_cards (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    assigned_pair TEXT[],
                    story_points INTEGER,
                    sprint INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    id SERIAL PRIMARY KEY,
                    sprint INTEGER,
                    driver_id TEXT,
                    navigator_id TEXT,
                    task_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    outcome TEXT,
                    decisions JSONB
                );
                
                CREATE TABLE IF NOT EXISTS meta_learnings (
                    id SERIAL PRIMARY KEY,
                    sprint INTEGER,
                    agent_id TEXT,
                    learning_type TEXT,
                    content JSONB,
                    applied BOOLEAN DEFAULT FALSE
                );
            ''')
    
    async def save_kanban_snapshot(self, sprint: int, data: Dict):
        """Save Kanban board state."""
        pass
    
    async def log_pairing_session(self, session_data: Dict):
        """Log a pairing session."""
        pass
PY

# Kanban board
cat > src/tools/kanban.py << 'PY'
"""Kanban board management."""

from typing import List, Dict, Optional
from .shared_context import SharedContextDB

class KanbanBoard:
    def __init__(self, db: SharedContextDB):
        self.db = db
        self.wip_limits = {"in_progress": 4, "review": 2}
    
    async def pull_ready_task(self) -> Optional[Dict]:
        """Pull highest priority task from Ready column."""
        # Check WIP limits
        # Get top priority ready task
        # Move to in_progress
        pass
    
    async def get_snapshot(self) -> Dict:
        """Get current state of board."""
        pass
    
    async def move_card(self, card_id: int, new_status: str):
        """Move card to new column."""
        # Check WIP limits
        # Update status
        pass
PY

# Metrics
cat > src/metrics/sprint_metrics.py << 'PY'
"""Sprint metrics calculation."""

from dataclasses import dataclass

@dataclass
class SprintResult:
    velocity: int
    features_completed: int
    test_coverage: float
    pairing_sessions: int
    cycle_time_avg: float

class SprintMetrics:
    async def calculate_sprint_results(self, sprint_num, db, kanban):
        """Calculate all metrics for a sprint."""
        # Query database for sprint data
        # Calculate velocity, coverage, etc.
        pass
PY

# Prometheus exporter
cat > src/metrics/prometheus_exporter.py << 'PY'
"""Prometheus metrics exporter."""

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Define metrics
sprint_velocity = Gauge('sprint_velocity', 'Story points per sprint')
test_coverage = Gauge('test_coverage_percent', 'Test coverage')
pairing_sessions = Counter('pairing_sessions_total', 'Total sessions', ['driver', 'navigator'])
consensus_time = Histogram('consensus_seconds', 'Time to consensus')

def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")
PY

# Agent factory
cat > src/agents/agent_factory.py << 'PY'
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
PY

# Config loader
cat > src/orchestrator/config.py << 'PY'
"""Configuration loading and management."""

import yaml
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExperimentConfig:
    name: str
    sprint_duration_minutes: int
    database_url: str
    team_config_dir: str
    vllm_endpoint: str

def load_config(config_path: str) -> ExperimentConfig:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    return ExperimentConfig(
        name=data["experiment"]["name"],
        sprint_duration_minutes=data["experiment"]["sprint_duration_minutes"],
        database_url=data["database"]["url"],
        team_config_dir=data["team"]["config_dir"],
        vllm_endpoint=data["models"]["vllm_endpoint"]
    )
PY

echo "Core Python modules created!"
