# Agile Agent Team Experiment

A simulation of a mature, high-performing agile development team implemented as a multi-agent AI system.

**_Critical remark:_** this whole thing is generated using AI, it stems from conversations with Claude to setup the premise and test the hypotheses.
Any code that is in this repo is AI generated as well, the experiment is thus 2-fold :)

## Overview

This project implements an 11-agent team that operates like a real software development team:
- **1 Dev Lead** (Kimi/Qwen2.5-Coder-32B)
- **1 QA Lead** (Kimi/Qwen2.5-72B)
- **1 Product Owner** (Opus/Qwen2.5-72B)
- **6 Developers** (2 senior, 2 mid-level, 2 junior - DeepSeek/Qwen variants)
- **2 Testers** (Qwen2.5-14B)

### Core Principles

- **20-minute sprints** (simulated 2 weeks)
- **XP practices**: Pair programming, TDD, continuous integration
- **Kanban workflow** with WIP limits
- **Clean house policy**: No technical debt beyond 1 sprint
- **Definition of Done**: All features must be fully tested and production-ready

## Quick Start

### Prerequisites

- Kubernetes cluster with GH200 nodes (4 GH200 superchips)
- Python 3.11+
- kubectl configured
- Docker

### Installation

```bash
# Clone repository
git clone https://github.com/witlox/agile-agent-team
cd agile-agent-team

# Install dependencies
pip install -r requirements.txt

# Deploy infrastructure
./scripts/deploy-infrastructure.sh

# Initialize team configuration
./scripts/init-team.sh

# Run qualification tests
python -m pytest tests/qualification/

# Start experiment
python src/orchestrator/main.py --sprints 10
```

## Architecture

### Technology Stack

- **Model Serving**: vLLM on GH200 nodes
- **Orchestration**: Python asyncio-based
- **State Management**: PostgreSQL + Redis
- **Monitoring**: Prometheus + Grafana
- **Container Platform**: Kubernetes

### Key Components

1. **Orchestrator** (`src/orchestrator/`): Manages sprint lifecycle, time simulation, process enforcement
2. **Agents** (`src/agents/`): Individual agent implementations with role-specific prompts
3. **Pairing Engine** (`src/agents/pairing.py`): Handles TDD dialogue-driven pairing
4. **Shared Context** (`src/tools/shared_context.py`): Database access layer
5. **Metrics** (`src/metrics/`): Prometheus instrumentation and custom metrics

## Team Configuration

Agent profiles are defined in `team_config/`:

```
team_config/
├── 00_base/
│   └── base_agent.md                 # Common agent behavior
├── 01_role_archetypes/
│   ├── developer.md                  # Base developer traits
│   ├── tester.md                     # Base tester traits
│   └── leader.md                     # Leadership overlay
├── 02_individuals/
│   ├── dev_lead.md                   # Development team leader
│   ├── qa_lead.md                    # Quality assurance leader
│   ├── po.md                         # Product owner
│   ├── dev_sr_networking.md          # Senior: Networking specialist
│   ├── dev_sr_devops.md              # Senior: DevOps specialist
│   ├── dev_mid_backend.md            # Mid-level: Backend focus
│   ├── dev_mid_frontend.md           # Mid-level: Frontend focus
│   ├── dev_jr_fullstack_a.md         # Junior: Learning phase
│   ├── dev_jr_fullstack_b.md         # Junior: Learning phase
│   ├── tester_integration.md         # Senior tester: Integration
│   └── tester_e2e.md                 # Senior tester: E2E
├── 03_process_rules/
│   ├── xp_practices.md               # TDD, pairing, refactoring
│   ├── kanban_workflow.md            # Flow management
│   ├── pairing_protocol.md           # Collaboration mechanics
│   ├── consensus_protocol.md         # Decision escalation
│   └── artifact_standards.md         # Sprint deliverables
└── 04_meta/
    ├── retro_template.md             # Keep/Drop/Puzzle format
    ├── meta_learnings.jsonl          # Append-only learning log
    └── team_evolution.md             # Prompt modification rules
```

## Running Experiments

### Basic Experiment

```bash
# Run 10 sprints with default configuration
python src/orchestrator/main.py --sprints 10 --output results/experiment-001
```

### With Disturbances

```bash
# Enable realistic failure injection
python src/orchestrator/main.py \
  --sprints 20 \
  --disturbances enabled \
  --disturbance-frequency 0.2 \
  --output results/experiment-002
```

### Profile Swapping Experiments

```bash
# No swapping (pure human simulation)
python src/orchestrator/main.py --sprints 10 --profile-swap none

# Constrained swapping (recommended)
python src/orchestrator/main.py --sprints 10 --profile-swap constrained

# Free swapping (AI-optimal baseline)
python src/orchestrator/main.py --sprints 10 --profile-swap free
```

## Monitoring

Access Grafana dashboard:
```bash
kubectl port-forward svc/grafana 3000:3000
# Visit http://localhost:3000
# Default credentials: admin/admin
```

Key dashboards:
- **Sprint Overview**: Velocity, quality metrics, cycle time
- **Team Health**: Pairing activity, consensus time, process compliance
- **Agent Performance**: Response times, token usage, error rates

## Artifacts

Each sprint produces:

1. **Kanban Board Snapshot** (JSON)
2. **Pairing Log** (JSONL)
3. **Retro Notes** (Markdown)
4. **Meta-Learning Diff** (changes to agent prompts)
5. **Test Coverage Report** (JSON)
6. **Architectural Decision Records** (ADRs)
7. **Code Repository** (Git-like structure)

Artifacts are stored in: `outputs/<experiment-id>/sprint-<N>/`

## Qualification System

Before running experiments, qualify models for each role:

```bash
# Qualify a specific agent
python -m tests.qualification.qualify \
  --model Qwen2.5-Coder-7B-Instruct \
  --role dev_jr_fullstack_a

# Qualify all agents
./scripts/qualify-all-agents.sh
```

Qualification tests:
- **Technical depth**: Can the model solve domain-specific problems?
- **Pairing collaboration**: Can it work with partners effectively?
- **Role-appropriate behavior**: Does it match expected seniority?
- **Mistake patterns**: Do juniors make realistic mistakes?

## Configuration

Edit `config.yaml` to customize:

```yaml
experiment:
  sprint_duration_minutes: 20
  sprints_per_stakeholder_review: 5
  
team:
  wip_limits:
    in_progress: 4
    review: 2
  
  test_coverage_minimum: 85
  
disturbances:
  enabled: true
  types:
    dependency_breaks: 0.16  # 1 in 6 sprints
    production_incident: 0.125  # 1 in 8 sprints
    flaky_test: 0.25  # 1 in 4 sprints

models:
  vllm_endpoint: "http://vllm-gh200-module-1:8000"
  temperature: 0.7
  max_tokens: 4096
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Qualification tests
pytest tests/qualification/

# All tests
pytest
```

### Adding New Agent Profiles

1. Create profile file in `team_config/02_individuals/`
2. Define specialization, cognitive patterns, growth arc
3. Run qualification tests
4. Update `src/agents/agent_factory.py` to register agent

### Custom Metrics

Add to `src/metrics/custom_metrics.py`:

```python
from prometheus_client import Counter

my_metric = Counter('my_metric_total', 'Description', ['label1'])
my_metric.labels(label1='value').inc()
```

## Research Questions

This experiment is designed to explore:

1. **Can LLMs form effective collaborative teams?**
   - Hypothesis: Dialogue-driven pairing produces better code than solo agents
   
2. **Do agent seniority levels create realistic dynamics?**
   - Hypothesis: Junior agents learn measurably from pairing with seniors
   
3. **How does team maturity affect productivity?**
   - Hypothesis: Velocity increases over first 10 sprints then stabilizes
   
4. **Are disturbances handled realistically?**
   - Hypothesis: Constrained teams surface real organizational issues
   
5. **Does profile-swapping break team dynamics?**
   - Hypothesis: Free swapping increases velocity but reduces learning

## Troubleshooting

### Models not responding
```bash
# Check vLLM health
kubectl get pods -l app=vllm
kubectl logs <vllm-pod-name>

# Verify model loading
curl http://<vllm-endpoint>/health
```

### Sprints timing out
- Reduce `max_exchanges` in pairing protocol
- Increase `sprint_duration_minutes` in config
- Check agent response time metrics in Grafana

### Pairing consensus failures
- Review `outputs/<experiment>/sprint-<N>/pairing_log.jsonl`
- Check if agents are actually disagreeing or timing out
- Adjust consensus detection threshold

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE)

## Citation

If you use this in research, please cite:

```bibtex
@software{agile_agent_team,
  title={Agile Agent Team: Multi-Agent Simulation of Software Development},
  author={Pim Witlox},
  year={2026},
  url={https://github.com/witlox/agile-agent-team}
}
```

## Acknowledgments

- Inspired by real-world agile teams and XP practices
- Built on vLLM, Qwen, DeepSeek, and other open-source models
- Thanks to the AI agent research community
