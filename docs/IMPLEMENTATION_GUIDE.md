# Implementation Guide

This guide walks through actually implementing and running the agile agent team experiment, from hardware setup to analyzing results.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [Software Installation](#software-installation)
4. [Model Setup](#model-setup)
5. [Configuration](#configuration)
6. [Running Experiments](#running-experiments)
7. [Monitoring](#monitoring)
8. [Analyzing Results](#analyzing-results)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Knowledge Requirements
- Kubernetes basics (pods, deployments, services)
- Python programming (reading, not deep expertise)
- PostgreSQL (basic SQL)
- Docker containers
- Command-line comfort

### Hardware Requirements

**Minimum (Small-Scale Testing):**
- 1x GPU node (RTX 4090 24GB or similar)
- 64GB RAM
- 8 CPU cores
- 500GB SSD

**Recommended (Full Experiment):**
- 2x GH200 nodes (4 modules total) OR
- 4x A100 80GB OR
- 6x RTX 4090 24GB
- 384GB RAM total
- 96 CPU cores total
- 1TB NVMe storage

### Software Requirements
- Kubernetes 1.28+ (k3s, k8s, or managed like GKE/EKS)
- kubectl CLI
- Python 3.11+
- Docker 24+
- Git

---

## Hardware Setup

### Option A: GH200 Cluster (Optimal)

**Per GH200 node:**
- 4x GH200 modules
- 384GB HBM3 per module
- Grace ARM CPU (72 cores)

**Kubernetes node labeling:**
```bash
kubectl label nodes gh200-node-1 nvidia.com/gpu.product=NVIDIA-GH200-480GB
kubectl label nodes gh200-node-2 nvidia.com/gpu.product=NVIDIA-GH200-480GB
```

### Option B: Multi-GPU Cluster

**Node 1 (Orchestrator + DB):**
```yaml
CPU: 16 cores
RAM: 64GB
Storage: 500GB SSD
GPU: None
```

**Node 2 (Large Models):**
```yaml
CPU: 32 cores
RAM: 128GB
GPU: 2x A100 80GB
Storage: 1TB NVMe
```

**Nodes 3-4 (Medium/Small Models):**
```yaml
CPU: 24 cores each
RAM: 96GB each
GPU: 2x RTX 4090 24GB per node
Storage: 1TB NVMe each
```

### GPU Drivers

**NVIDIA Driver:**
```bash
# Ubuntu
sudo ubuntu-drivers autoinstall
sudo reboot

# Verify
nvidia-smi
```

**CUDA Toolkit:**
```bash
wget https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda_12.3.0_545.23.06_linux.run
sudo sh cuda_12.3.0_545.23.06_linux.run
```

**Kubernetes GPU Plugin:**
```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml
```

---

## Software Installation

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd agile-agent-team
```

### 2. Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import asyncio, asyncpg, redis, yaml; print('OK')"
```

### 3. Kubernetes Cluster

**Local (k3s):**
```bash
curl -sfL https://get.k3s.io | sh -
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

**Managed (GKE example):**
```bash
gcloud container clusters create agile-agents \
  --machine-type n1-standard-32 \
  --accelerator type=nvidia-tesla-a100,count=2 \
  --num-nodes 2 \
  --zone us-central1-a
```

### 4. Docker Images

**Build orchestrator image:**
```bash
docker build -t agile-agents/orchestrator:latest .
docker push <your-registry>/agile-agents/orchestrator:latest

# Update deployment.yaml with your registry
sed -i 's|agile-agents/orchestrator:latest|<your-registry>/agile-agents/orchestrator:latest|' infrastructure/k8s/deployment.yaml
```

---

## Model Setup

### Download Models

**Using Hugging Face CLI:**
```bash
pip install huggingface-hub

# Login (get token from https://huggingface.co/settings/tokens)
huggingface-cli login

# Download models
huggingface-cli download Qwen/Qwen2.5-72B-Instruct
huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct
huggingface-cli download deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
huggingface-cli download Qwen/Qwen2.5-14B-Instruct
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct
```

Models download to: `~/.cache/huggingface/hub/`

### Start vLLM Servers

**Terminal 1 (Large models):**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-72B-Instruct \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --port 8000
```

**Terminal 2 (Medium models):**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
  --gpu-memory-utilization 0.85 \
  --max-model-len 16384 \
  --port 8001
```

**Terminal 3 (Small models):**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --gpu-memory-utilization 0.85 \
  --max-model-len 8192 \
  --port 8002
```

**Verify servers:**
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## Configuration

### 1. Edit config.yaml

```yaml
# Update model endpoints
models:
  vllm_endpoint: "http://YOUR_IP:8000"  # Change to your IP
  
# Update database
database:
  url: "postgresql://postgres:YOUR_PASSWORD@postgres:5432/team_context"
  redis_url: "redis://redis:6379"
```

### 2. Create Kubernetes Secrets

```bash
kubectl create secret generic db-credentials \
  --from-literal=username=postgres \
  --from-literal=password=YOUR_STRONG_PASSWORD \
  -n agile-agents
```

### 3. Deploy Infrastructure

```bash
# Create namespace
kubectl create namespace agile-agents

# Deploy services
kubectl apply -f infrastructure/k8s/services.yaml

# Deploy applications
kubectl apply -f infrastructure/k8s/deployment.yaml

# Wait for pods
kubectl wait --for=condition=ready pod --all -n agile-agents --timeout=300s
```

### 4. Initialize Database

```bash
# Port-forward to postgres
kubectl port-forward svc/postgres 5432:5432 -n agile-agents &

# Run init script
python -m src.tools.init_db --config config.yaml

# Verify
psql postgresql://postgres:YOUR_PASSWORD@localhost:5432/team_context -c "\dt"
```

---

## Running Experiments

### Experiment 1: Baseline (no disturbances, no swapping)

Edit `config.yaml`:
```yaml
disturbances:
  enabled: false
profile_swapping:
  mode: "none"
```

Then run:
```bash
python -m src.orchestrator.main \
  --config config.yaml \
  --sprints 10 \
  --output outputs/baseline-experiment
```

**Expected duration:** ~220 minutes (10 sprints × 22 min)

**Watch progress:**
```bash
tail -f outputs/baseline-experiment/sprint-*/retro.md
```

### Experiment 2: Constrained swapping with disturbances

Edit `config.yaml`:
```yaml
disturbances:
  enabled: true
profile_swapping:
  mode: "constrained"
```

Then run:
```bash
python -m src.orchestrator.main \
  --config config.yaml \
  --sprints 20 \
  --output outputs/constrained-experiment
```

**With default frequencies:** Expect 2-4 incidents over 20 sprints.

### Experiment 3: Free swapping (AI-optimal baseline)

Edit `config.yaml`:
```yaml
profile_swapping:
  mode: "free"
```

Then run:
```bash
python -m src.orchestrator.main \
  --config config.yaml \
  --sprints 20 \
  --output outputs/free-swap-experiment
```

### Running multiple variants simultaneously

Use separate config files per variant, then run in parallel:

```bash
# Copy and edit configs
cp config.yaml config-none.yaml       # set mode: none
cp config.yaml config-constrained.yaml # set mode: constrained
cp config.yaml config-free.yaml       # set mode: free

# Run in parallel
python -m src.orchestrator.main --config config-none.yaml --sprints 20 --output outputs/none &
python -m src.orchestrator.main --config config-constrained.yaml --sprints 20 --output outputs/constrained &
python -m src.orchestrator.main --config config-free.yaml --sprints 20 --output outputs/free &

# Monitor all
watch -n 5 'ls -1 outputs/*/sprint-* | wc -l'
```

> **Tip:** See [USAGE.md](USAGE.md) for the full configuration reference and artifact format.

---

## Monitoring

### Access Grafana

```bash
kubectl port-forward svc/grafana 3000:3000 -n agile-agents

# Open browser: http://localhost:3000
# Login: admin / admin
```

### Key Dashboards

**Sprint Overview:**
- Velocity trend (story points per sprint)
- Feature completion curve
- Test coverage over time
- Cycle time distribution

**Team Dynamics:**
- Pairing heatmap (who pairs with whom)
- Consensus time (how long to agree)
- Escalation frequency
- Junior question rate

**Agent Performance:**
- Response time percentiles (p50, p95, p99)
- Token usage per agent
- Error rates
- Model utilization

**Junior Contributions:**
- Questions asked per sprint
- Questions leading to changes
- Reverse mentorship events
- Senior pause-before-answer time

### Custom Queries

**Prometheus console:** http://localhost:9090

**Example queries:**
```promql
# Average velocity last 5 sprints
avg_over_time(sprint_velocity[5d])

# Junior question success rate
rate(junior_questions_total{resulted_in_change="true"}[1h]) / 
rate(junior_questions_total[1h])

# Senior learning from juniors
sum(rate(senior_learned_from_junior_total[1h])) by (senior_id)
```

---

## Analyzing Results

### Output Structure

```
outputs/baseline-experiment/
├── sprint-01/
│   ├── kanban.json              # Board state
│   ├── pairing_log.jsonl        # All dialogues
│   ├── retro.md                 # Keep/Drop/Puzzle
│   ├── test_coverage.json       # Coverage report
│   ├── meta_learning_diff.md    # Prompt changes
│   └── adrs/                    # Architecture decisions
├── ...
├── final_report.md              # Summary
└── metrics/                     # Raw data
```

### Velocity Analysis

```python
import json
import pandas as pd
import matplotlib.pyplot as plt

# Load velocity data
sprints = []
velocities = []

for sprint in range(1, 21):
    with open(f'outputs/baseline-experiment/sprint-{sprint:02d}/kanban.json') as f:
        data = json.load(f)
        velocity = sum(card['story_points'] for card in data['done'])
        sprints.append(sprint)
        velocities.append(velocity)

# Plot
plt.figure(figsize=(10, 6))
plt.plot(sprints, velocities, marker='o')
plt.xlabel('Sprint')
plt.ylabel('Velocity (Story Points)')
plt.title('Team Velocity Over Time')
plt.grid(True)
plt.savefig('velocity_trend.png')
```

**Expected pattern:**
- Sprints 1-3: Low (team forming, tooling)
- Sprints 4-10: Steep increase (team learning)
- Sprints 10+: Linear (sustainable pace)

### Junior Value Analysis

```python
import json

# Analyze junior questions
questions_per_sprint = []
changes_per_sprint = []

for sprint in range(1, 21):
    with open(f'outputs/baseline-experiment/sprint-{sprint:02d}/retro.md') as f:
        content = f.read()
        
        # Count questions mentioned
        questions = content.count('Question:')
        changes = content.count('Result:')
        
        questions_per_sprint.append(questions)
        changes_per_sprint.append(changes)

# Calculate hit rate
hit_rate = [c/q if q > 0 else 0 for q, c in zip(questions_per_sprint, changes_per_sprint)]

print(f"Average questions per sprint: {sum(questions_per_sprint)/len(questions_per_sprint):.1f}")
print(f"Average hit rate: {sum(hit_rate)/len(hit_rate):.1%}")
```

**Healthy team:**
- 15-20 questions/sprint
- 5-10% hit rate (questions → changes)

### Pairing Quality

```python
import json

# Analyze pairing sessions
for sprint in range(1, 21):
    with open(f'outputs/baseline-experiment/sprint-{sprint:02d}/pairing_log.jsonl') as f:
        sessions = [json.loads(line) for line in f]
    
    # Metrics
    total_sessions = len(sessions)
    avg_duration = sum(s['duration_seconds'] for s in sessions) / total_sessions
    consensus_failures = sum(1 for s in sessions if not s['consensus_reached'])
    
    print(f"Sprint {sprint}:")
    print(f"  Sessions: {total_sessions}")
    print(f"  Avg duration: {avg_duration/60:.1f} minutes")
    print(f"  Consensus failures: {consensus_failures}")
```

### Compare Experiments

```python
import pandas as pd

# Load final reports
baseline = pd.read_json('outputs/baseline-experiment/final_report.json')
constrained = pd.read_json('outputs/constrained-experiment/final_report.json')
free = pd.read_json('outputs/free-swap-experiment/final_report.json')

# Compare
comparison = pd.DataFrame({
    'No Swap': baseline['metrics'],
    'Constrained': constrained['metrics'],
    'Free Swap': free['metrics']
})

print(comparison)
```

**Expected differences:**
- Velocity: Free > Constrained > None
- Quality: Constrained ≥ None > Free
- Learning: None > Constrained >> Free

---

## Troubleshooting

### Models Not Responding

**Symptom:** Sprints timeout, agents don't generate responses

**Debug:**
```bash
# Check vLLM server logs
kubectl logs -l app=vllm -n agile-agents --tail=100

# Test endpoint directly
curl http://YOUR_VLLM_IP:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-72B-Instruct", "prompt": "Hello", "max_tokens": 10}'
```

**Common fixes:**
- VRAM exhaustion → Reduce `--gpu-memory-utilization`
- Wrong model path → Check `~/.cache/huggingface/hub/`
- Port blocked → Check firewall rules

### Database Connection Errors

**Symptom:** "Can't connect to PostgreSQL"

**Debug:**
```bash
# Check postgres pod
kubectl get pods -l app=postgres -n agile-agents

# Check logs
kubectl logs postgres-0 -n agile-agents

# Test connection
kubectl exec -it postgres-0 -n agile-agents -- psql -U postgres -d team_context -c "SELECT 1"
```

**Common fixes:**
- Wrong password → Recreate secret
- Database not initialized → Run init_db script
- Pod not ready → Wait longer, check resources

### Sprints Running Too Long

**Symptom:** Sprint takes >25 minutes

**Debug:**
```bash
# Check agent response times
curl http://localhost:8080/metrics | grep agent_response_seconds

# Check pairing session times
grep "duration_seconds" outputs/*/sprint-*/pairing_log.jsonl
```

**Fixes:**
- Increase `sprint_duration_minutes` in config
- Reduce `max_exchanges` in pairing protocol
- Use faster models for some roles
- Check if models are swapping to disk

### Low Quality Output

**Symptom:** Agents not following instructions, poor code

**Debug:**
```bash
# Run qualification tests
python -m tests.qualification.qualify \
  --model Qwen2.5-Coder-7B-Instruct \
  --role dev_jr_fullstack_a

# Check agent prompts are loading
grep "Recent Learning" outputs/*/sprint-*/meta_learning_diff.md
```

**Fixes:**
- Re-run qualification tests
- Adjust temperature (higher = creative, lower = focused)
- Verify prompt files are correct
- Check model versions match

### Grafana Not Showing Data

**Symptom:** Dashboards empty

**Debug:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check metrics endpoint
curl http://localhost:8080/metrics
```

**Fixes:**
- Verify Prometheus scrape config
- Check orchestrator is exposing metrics
- Restart Grafana pod

---

## Performance Tuning

### Optimize vLLM

```bash
# Increase batch size
--max-num-seqs 32

# Enable prefix caching
--enable-prefix-caching

# Use quantization (4-bit)
--quantization awq

# Adjust KV cache
--block-size 16
```

### Optimize Database

```sql
-- Create indexes
CREATE INDEX idx_kanban_status ON kanban_cards(status);
CREATE INDEX idx_pairing_sprint ON pairing_sessions(sprint);

-- Tune PostgreSQL
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '64MB';
```

### Optimize Kubernetes

```yaml
# Increase resource limits if available
resources:
  requests:
    cpu: "16"
    memory: "64Gi"
  limits:
    cpu: "32"
    memory: "128Gi"
```

---

## Next Steps

1. **Run baseline experiment** (10 sprints, no swapping)
2. **Analyze velocity trends** (exponential → linear?)
3. **Run constrained experiment** (20 sprints with disturbances)
4. **Compare swap modes** (none vs constrained vs free)
5. **Publish findings** (blog post, paper, GitHub)

## Getting Help

- **Issues:** Check GitHub issues
- **Logs:** Always include orchestrator and vLLM logs
- **Metrics:** Export Prometheus data for diagnosis
- **Community:** Join discussions (if public repo)

---

**Ready to run your first experiment? Start with the 10-sprint baseline!**
