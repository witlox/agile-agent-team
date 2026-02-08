# Agile Agent Team - Complete Setup Guide

## What You Have

This repository contains a **complete, runnable implementation** of an 11-agent software development team simulation:

- ✅ All 11 agent profiles (dev lead, QA lead, PO, 6 developers, 2 testers)
- ✅ Complete process rules (XP practices, Kanban, pairing, consensus)
- ✅ Full Python orchestration system
- ✅ Kubernetes deployment manifests
- ✅ Monitoring stack (Prometheus + Grafana)
- ✅ Configuration management
- ✅ Qualification test framework

## Repository Structure

```
agile-agent-team/
├── team_config/              # Agent profiles and process rules
│   ├── 00_base/             # Base agent behavior (all inherit)
│   ├── 01_role_archetypes/  # Developer, Tester, Leader templates
│   ├── 02_individuals/      # 11 individual agent profiles
│   ├── 03_process_rules/    # XP, Kanban, Pairing protocols
│   └── 04_meta/             # Retro templates, meta-learning
│
├── src/                     # Python source code
│   ├── orchestrator/        # Sprint management, main entry point
│   ├── agents/              # Agent implementations, pairing engine
│   ├── tools/               # Kanban, shared DB, utilities
│   └── metrics/             # Prometheus exporters
│
├── infrastructure/          # Deployment configurations
│   ├── k8s/                 # Kubernetes manifests
│   ├── monitoring/          # Prometheus/Grafana configs
│   └── vllm/                # vLLM model serving configs
│
├── tests/                   # Test suites
│   ├── qualification/       # Agent capability tests
│   ├── integration/         # System integration tests
│   └── unit/                # Unit tests
│
├── scripts/                 # Utility scripts
├── docs/                    # Additional documentation
├── config.yaml              # Main configuration file
└── README.md                # Full documentation
```

## Quick Start (30 Minutes to First Sprint)

### Prerequisites

**Hardware:**
- Kubernetes cluster with GH200 GPU nodes (or adapt for your GPUs)
- Minimum: 96 CPU cores, 384GB RAM, ~200GB GPU VRAM
- Storage: 500GB for models + data

**Software:**
- Python 3.11+
- kubectl configured
- Docker
- Helm (optional but recommended)

### Step 1: Extract Repository

```bash
tar -xzf agile-agent-team.tar.gz
cd agile-agent-team
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Configure for Your Environment

Edit `config.yaml`:

```yaml
# Update these for your setup
models:
  vllm_endpoint: "http://YOUR_VLLM_SERVER:8000"

database:
  url: "postgresql://user:pass@YOUR_DB_HOST:5432/team_context"
  redis_url: "redis://YOUR_REDIS_HOST:6379"
```

### Step 4: Deploy Infrastructure (Kubernetes)

```bash
# Create namespace
kubectl create namespace agile-agents

# Deploy database and services
kubectl apply -f infrastructure/k8s/services.yaml
kubectl apply -f infrastructure/k8s/deployment.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n agile-agents --timeout=300s
```

### Step 5: Initialize Database

```bash
# Run database migrations
python -m src.tools.init_db --config config.yaml
```

### Step 6: Download and Serve Models

**Option A: Using vLLM (Recommended)**

```bash
# Start vLLM server for each model tier
# Large models (Dev Lead, QA Lead, PO)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-72B-Instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --port 8000

# Mid-size models (Senior devs, testers)
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
  --gpu-memory-utilization 0.85 \
  --port 8001

# Small models (Junior devs)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --gpu-memory-utilization 0.85 \
  --port 8002
```

Update `config.yaml` with appropriate endpoints.

**Option B: Single Multi-Model Server**

Use vLLM's multi-model serving (see vLLM docs).

### Step 7: Qualify Agents (Optional but Recommended)

```bash
# Test if models can actually fulfill their roles
./scripts/qualify-all-agents.sh

# Or qualify individually
python -m tests.qualification.qualify \
  --model Qwen2.5-Coder-7B-Instruct \
  --role dev_jr_fullstack_a
```

This verifies:
- Juniors make realistic mistakes
- Seniors provide architectural guidance
- Testers enforce quality gates

### Step 8: Run First Experiment

```bash
# Run 10 sprints with default configuration
python src/orchestrator/main.py \
  --config config.yaml \
  --sprints 10 \
  --output outputs/experiment-001

# This will take ~200 minutes (10 sprints × 20 min each)
```

### Step 9: Monitor Progress

**Access Grafana:**
```bash
kubectl port-forward svc/grafana 3000:3000 -n agile-agents
# Visit http://localhost:3000
# Default login: admin/admin
```

**Watch Metrics:**
- Sprint velocity trend
- Test coverage
- Pairing activity
- Agent response times

### Step 10: Review Results

```bash
# Artifacts are in:
ls outputs/experiment-001/

# Each sprint has:
sprint-01/
  ├── kanban.json           # Board state
  ├── pairing_log.jsonl     # All pairing sessions
  ├── retro.md              # Keep/Drop/Puzzle
  ├── test_coverage.json    # Coverage report
  ├── meta_learning_diff.md # Prompt changes
  └── adrs/                 # Architectural decisions
```

## Configuration Options

### Experiment Variants

**No Profile Swapping (Pure Human Simulation):**
```bash
python src/orchestrator/main.py \
  --profile-swap none \
  --sprints 20 \
  --output outputs/no-swap
```

**Constrained Swapping (Recommended):**
```bash
python src/orchestrator/main.py \
  --profile-swap constrained \
  --sprints 20 \
  --output outputs/constrained
```

**Free Swapping (AI Optimal):**
```bash
python src/orchestrator/main.py \
  --profile-swap free \
  --sprints 20 \
  --output outputs/free-swap
```

### Disturbance Control

Edit `config.yaml`:

```yaml
disturbances:
  enabled: true
  
  frequencies:
    dependency_breaks: 0.166      # 1 in 6 sprints
    production_incident: 0.125    # 1 in 8 sprints
    flaky_test: 0.25              # 1 in 4 sprints
    scope_creep: 0.20             # 1 in 5 sprints
```

### Team Composition

To change team makeup, edit agent profiles in `team_config/02_individuals/`.

Example: Add a third senior developer:
1. Copy `dev_sr_networking.md` to `dev_sr_backend.md`
2. Modify specialization section
3. Update `config.yaml` to include new agent

## Troubleshooting

### Models Not Loading

```bash
# Check vLLM logs
kubectl logs -l app=vllm -n agile-agents

# Test endpoint
curl http://YOUR_VLLM_ENDPOINT:8000/health
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
kubectl get pods -l app=postgres -n agile-agents

# Check connection
psql postgresql://postgres:password@localhost:5432/team_context
```

### Sprints Timing Out

Increase sprint duration in `config.yaml`:

```yaml
experiment:
  sprint_duration_minutes: 30  # Increase from 20
```

### Low Quality Output

1. Check agent qualification results
2. Verify model parameters (temperature, max_tokens)
3. Review pairing dialogues in `pairing_log.jsonl`
4. Increase complexity of agent prompts

## Advanced Usage

### Custom Agent Profiles

Create new agent by:

1. Copy template from existing agent
2. Modify cognitive patterns, expertise
3. Run qualification tests
4. Register in agent factory

### Custom Metrics

Add to `src/metrics/custom_metrics.py`:

```python
from prometheus_client import Counter

custom_metric = Counter(
    'my_metric_total',
    'Description',
    ['label1', 'label2']
)

# In your code:
custom_metric.labels(label1='value1', label2='value2').inc()
```

### Integration with External Tools

The system can integrate with:
- Jira/Linear (for real backlog management)
- GitHub (for actual code repositories)
- Slack (for team notifications)
- Datadog (for enhanced monitoring)

See `docs/INTEGRATIONS.md` (create as needed).

## Research Questions

Use this experiment to explore:

1. **Team Dynamics**: Do LLMs form effective collaborative teams?
2. **Learning Curves**: Do junior agents measurably improve from pairing?
3. **Maturity Impact**: How does team maturity affect productivity?
4. **Disturbance Handling**: Are failures handled realistically?
5. **Profile Swapping**: Does it help or hurt team dynamics?

## Data Collection

Each experiment generates:

- Quantitative metrics (velocity, coverage, cycle time)
- Qualitative data (pairing dialogues, retro notes)
- Behavioral patterns (decision-making, escalations)
- Learning trajectories (skill acquisition over sprints)

## Next Steps

1. **Run Baseline**: 20 sprints with default config
2. **Analyze Results**: Review velocity trends, quality metrics
3. **Iterate**: Adjust agent prompts based on learnings
4. **Compare**: Run variants (no swap vs constrained vs free)
5. **Publish**: Share findings with research community

## Getting Help

- **Issues**: Check GitHub issues (if repo is public)
- **Documentation**: See `docs/` directory
- **Community**: Join discussions (if applicable)

## Citation

If you use this in research:

```bibtex
@software{agile_agent_team,
  title={Agile Agent Team: Multi-Agent Simulation of Software Development},
  author={Your Name},
  year={2026},
  url={https://github.com/yourusername/agile-agent-team}
}
```

## License

MIT License - See LICENSE file

---

**Ready to run?** Start with the Quick Start section above!

**Questions?** Review the comprehensive README.md

**Want to contribute?** See CONTRIBUTING.md
