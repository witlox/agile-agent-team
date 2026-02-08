#!/usr/bin/env python3
"""
Complete repository builder - generates all files for the agile agent team experiment.
Run this script to create the entire project structure.
"""

import os
import json
from pathlib import Path
from textwrap import dedent

BASE = Path("/home/claude/agile-agent-team")

def write(path, content):
    """Write file with content, create parents if needed."""
    full = BASE / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(dedent(content).strip() + "\n")
    print(f"✓ {path}")

# Core Python source files
write("src/__init__.py", "# Agile Agent Team Core Package")

write("src/orchestrator/__init__.py", "# Sprint Orchestration System")

write("src/orchestrator/main.py", """
\"\"\"
Main orchestrator for running agile agent team sprints.
\"\"\"

import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from .sprint_manager import SprintManager
from .config import load_config
from ..agents.agent_factory import AgentFactory
from ..tools.shared_context import SharedContextDB
from ..metrics.prometheus_exporter import start_metrics_server

async def run_experiment(config_path: str, num_sprints: int, output_dir: str):
    \"\"\"Run the complete experiment for N sprints.\"\"\"
    
    # Load configuration
    config = load_config(config_path)
    
    # Initialize shared context database
    db = SharedContextDB(config.database_url)
    await db.initialize()
    
    # Start metrics server
    start_metrics_server(port=8080)
    
    # Create agent factory and load all agents
    factory = AgentFactory(config.team_config_dir, config.vllm_endpoint)
    agents = await factory.create_all_agents()
    
    print(f"Loaded {len(agents)} agents")
    for agent in agents:
        print(f"  - {agent.role_id}: {agent.name}")
    
    # Initialize sprint manager
    sprint_mgr = SprintManager(
        agents=agents,
        shared_db=db,
        config=config,
        output_dir=Path(output_dir)
    )
    
    # Run sprints
    for sprint_num in range(1, num_sprints + 1):
        print(f"\n{'='*60}")
        print(f"SPRINT {sprint_num} - {datetime.now()}")
        print(f"{'='*60}\n")
        
        result = await sprint_mgr.run_sprint(sprint_num)
        
        # Stakeholder review every 5 sprints
        if sprint_num % 5 == 0:
            await sprint_mgr.stakeholder_review(sprint_num)
        
        # Print summary
        print(f"\nSprint {sprint_num} Summary:")
        print(f"  Velocity: {result.velocity} points")
        print(f"  Features completed: {result.features_completed}")
        print(f"  Test coverage: {result.test_coverage}%")
        print(f"  Pairing sessions: {result.pairing_sessions}")
    
    # Final report
    await sprint_mgr.generate_final_report()
    
    print(f"\nExperiment complete! Output: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Run agile agent team experiment")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--sprints", type=int, default=10, help="Number of sprints")
    parser.add_argument("--output", default="outputs/experiment", help="Output directory")
    
    args = parser.parse_args()
    
    asyncio.run(run_experiment(args.config, args.sprints, args.output))

if __name__ == "__main__":
    main()
""")

write("src/orchestrator/sprint_manager.py", """
\"\"\"
Sprint lifecycle manager - orchestrates planning, execution, retro.
\"\"\"

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from ..agents.base_agent import BaseAgent
from ..agents.pairing import PairingEngine
from ..tools.kanban import KanbanBoard
from ..tools.shared_context import SharedContextDB
from ..metrics.sprint_metrics import SprintMetrics

class SprintManager:
    def __init__(self, agents: List[BaseAgent], shared_db: SharedContextDB, config, output_dir: Path):
        self.agents = agents
        self.db = shared_db
        self.config = config
        self.output_dir = output_dir
        self.pairing_engine = PairingEngine(agents)
        self.kanban = KanbanBoard(shared_db)
        self.metrics = SprintMetrics()
        
    async def run_sprint(self, sprint_num: int):
        \"\"\"Execute one complete sprint (20 min wall-clock).\"\"\"
        
        sprint_start = datetime.now()
        sprint_output = self.output_dir / f"sprint-{sprint_num:02d}"
        sprint_output.mkdir(parents=True, exist_ok=True)
        
        # Phase 1: Planning (not in 20min)
        print("📋 Sprint Planning...")
        await self.run_planning(sprint_num)
        
        # Phase 2: Development (20 minutes)
        print("💻 Development Phase (20 minutes)...")
        await self.run_development(sprint_num, duration_minutes=20)
        
        # Phase 3: Retrospective
        print("🔄 Retrospective...")
        retro_results = await self.run_retrospective(sprint_num)
        
        # Phase 4: Generate Artifacts
        print("📦 Generating Artifacts...")
        await self.generate_sprint_artifacts(sprint_num, sprint_output)
        
        # Update metrics
        result = await self.metrics.calculate_sprint_results(sprint_num, self.db, self.kanban)
        
        return result
    
    async def run_planning(self, sprint_num: int):
        \"\"\"Sprint planning meeting with full team.\"\"\"
        # PO presents prioritized backlog
        # Team estimates and selects work
        # Decompose into tasks
        pass
    
    async def run_development(self, sprint_num: int, duration_minutes: int):
        \"\"\"Main development phase with pairing.\"\"\"
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            # Get available pairs
            available_pairs = self.pairing_engine.get_available_pairs()
            
            # Assign work from Kanban
            for pair in available_pairs:
                task = await self.kanban.pull_ready_task()
                if task:
                    asyncio.create_task(
                        self.pairing_engine.run_pairing_session(pair, task)
                    )
            
            # Tick simulation forward
            await asyncio.sleep(1)  # 1 second real = ~4 minutes simulated
        
        # Wait for all pairing sessions to complete
        await self.pairing_engine.wait_for_completion()
    
    async def run_retrospective(self, sprint_num: int):
        \"\"\"Team retrospective - Keep/Drop/Puzzle format.\"\"\"
        # All agents participate
        # Generate retro notes
        # Update meta-learnings
        pass
    
    async def generate_sprint_artifacts(self, sprint_num: int, output_path: Path):
        \"\"\"Generate all required sprint artifacts.\"\"\"
        
        # 1. Kanban snapshot
        kanban_data = await self.kanban.get_snapshot()
        (output_path / "kanban.json").write_text(json.dumps(kanban_data, indent=2))
        
        # 2. Pairing log
        # 3. Retro notes  
        # 4. Test coverage
        # 5. ADRs
        pass
    
    async def stakeholder_review(self, sprint_num: int):
        \"\"\"Every 5 sprints: comprehensive stakeholder review.\"\"\"
        print(f"\n🎯 STAKEHOLDER REVIEW (Sprint {sprint_num})")
        # Present velocity, quality, escalations, demos
        pass
""")

# Configuration and utilities
write("config.yaml", """
# Agile Agent Team Experiment Configuration

experiment:
  name: "baseline-experiment"
  sprint_duration_minutes: 20
  sprints_per_stakeholder_review: 5

team:
  config_dir: "team_config"
  
  wip_limits:
    in_progress: 4
    review: 2
  
  quality_gates:
    min_test_coverage_lines: 85
    min_test_coverage_branches: 80
    max_cyclomatic_complexity: 10

  definition_of_done:
    - "All acceptance criteria met"
    - "Test coverage >= 85%"
    - "All tests passing"
    - "Code reviewed by pair"
    - "Deployed to staging"
    - "PO acceptance"

disturbances:
  enabled: true
  
  frequencies:
    dependency_breaks: 0.166  # 1 in 6 sprints
    production_incident: 0.125  # 1 in 8 sprints  
    flaky_test: 0.25  # 1 in 4 sprints
    scope_creep: 0.20  # 1 in 5 sprints
    junior_misunderstanding: 0.33  # 1 in 3 sprints
    architectural_debt_surfaces: 0.166  # 1 in 6 sprints
  
  blast_radius_controls:
    max_velocity_impact: 0.30  # Max 30% velocity drop
    max_quality_regression: 0.15  # Max 15% coverage drop

models:
  vllm_endpoint: "http://vllm-gh200-module-1:8000"
  
  agents:
    dev_lead:
      model: "Qwen/Qwen2.5-Coder-32B-Instruct"
      temperature: 0.7
      max_tokens: 4096
    
    qa_lead:
      model: "Qwen/Qwen2.5-72B-Instruct"
      temperature: 0.7
      max_tokens: 4096
    
    po:
      model: "Qwen/Qwen2.5-72B-Instruct"
      temperature: 0.8
      max_tokens: 4096
    
    developers_sr:
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
      temperature: 0.7
      max_tokens: 3072
    
    developers_mid:
      model: "Qwen/Qwen2.5-Coder-14B-Instruct"
      temperature: 0.7
      max_tokens: 2048
    
    developers_jr:
      model: "Qwen/Qwen2.5-Coder-7B-Instruct"
      temperature: 0.8
      max_tokens: 2048
    
    testers:
      model: "Qwen/Qwen2.5-14B-Instruct"
      temperature: 0.7
      max_tokens: 2048

database:
  url: "postgresql://postgres:password@shared-db:5432/team_context"
  redis_url: "redis://redis:6379"

monitoring:
  prometheus_port: 8080
  grafana_url: "http://grafana:3000"

profile_swapping:
  mode: "constrained"  # none | constrained | free
  
  allowed_scenarios:
    - "critical_production_incident"
    - "specialist_unavailable"
    - "deliberate_cross_training"
  
  penalties:
    context_switch_slowdown: 1.20  # 20% slower first task
    proficiency_reduction: 0.70  # 70% of true specialist
    knowledge_decay_sprints: 1  # Decays after 1 sprint if not used
""")

write("requirements.txt", """
# Core dependencies
asyncio-mqtt==0.16.1
pydantic==2.5.0
pyyaml==6.0.1
httpx==0.25.0
aiohttp==3.9.0

# Database
asyncpg==0.29.0
redis==5.0.1
sqlalchemy[asyncio]==2.0.23

# Metrics & Monitoring  
prometheus-client==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Development
black==23.11.0
mypy==1.7.0
ruff==0.1.6
""")

write(".gitignore", """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv
*.egg-info/
dist/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Outputs
outputs/
results/
*.log

# Secrets
.env
secrets/
*.key
*.pem

# OS
.DS_Store
Thumbs.db

# Kubernetes
*.kubeconfig

# Temporary
tmp/
temp/
*.tmp
""")

write("Dockerfile", """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY team_config/ ./team_config/
COPY config.yaml .

# Run orchestrator
CMD ["python", "-m", "src.orchestrator.main"]
""")

write("LICENSE", """
MIT License

Copyright (c) 2026 Agile Agent Team Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""")

print("\n✅ Repository structure created successfully!")
print(f"📁 Total files created in {BASE}")
