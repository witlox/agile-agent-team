# Agile Agent Team Experiment

A multi-agent AI system that operates as a mature, high-performing software development team that **produces actual working code**.

**_Critical remark:_** this whole thing is generated using AI, it stems from conversations with Claude to setup the premise and test the hypotheses.
Any code that is in this repo is AI generated as well, the experiment is thus 2-fold :)

## Overview

This project implements an 11-agent team that operates like a real software development team and **generates real, tested code**:
- **1 Dev Lead** (Qwen2.5-Coder-32B)
- **1 QA Lead** (Qwen2.5-72B)
- **1 Product Owner** (Qwen2.5-72B)
- **6 Developers** (2 senior, 2 mid-level, 2 junior - DeepSeek/Qwen variants)
- **2 Testers** (Qwen2.5-14B)

### Core Principles

- **20-minute sprints** (simulated 2 weeks)
- **XP practices**: Pair programming, TDD, continuous integration
- **Kanban workflow** with WIP limits
- **Clean house policy**: No technical debt beyond 1 sprint
- **Definition of Done**: All features must be fully tested and production-ready
- **BDD/DDD**: Behavior-Driven Development with Gherkin scenarios
- **Real code generation**: Agents use tools to write, test, and commit actual code
- **Greenfield & Brownfield**: Start fresh or build on existing codebases
- **GitHub/GitLab integration**: Push code, create PRs, review, and merge

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

- **Model Serving**: vLLM on GH200 nodes (offline) OR Anthropic API (online)
- **Tool-Using Agents**: File operations, git, bash, pytest execution
- **Orchestration**: Python asyncio-based
- **State Management**: PostgreSQL + Redis
- **Code Generation**: BDD/Gherkin → Implementation → Testing → Git commits
- **Remote Git Integration**: GitHub (gh CLI) / GitLab (glab CLI) for PRs and merges
- **Workspace Management**: Greenfield (fresh) and brownfield (incremental) modes
- **Monitoring**: Prometheus + Grafana
- **Container Platform**: Kubernetes

### Key Components

1. **Orchestrator** (`src/orchestrator/`): Manages sprint lifecycle, time simulation, process enforcement
2. **Agents** (`src/agents/`): Tool-using agents with compositional profiles (8 layers)
3. **Runtimes** (`src/agents/runtime/`): VLLMRuntime (offline) + AnthropicRuntime (online)
4. **Tool System** (`src/tools/agent_tools/`): Filesystem, git, bash, test execution
5. **Pairing Engines**:
   - `CodeGenPairingEngine`: BDD-driven real code generation
   - `PairingEngine`: Dialogue-based (legacy fallback)
6. **Code Generation** (`src/codegen/`):
   - `WorkspaceManager`: Per-sprint/story git workspaces
   - `BDDGenerator`: User stories → Gherkin features
7. **Shared Context** (`src/tools/shared_context.py`): Database access layer
8. **Metrics** (`src/metrics/`): Prometheus instrumentation and custom metrics

### Deployment Modes

**Fully Offline (Local vLLM)**
- All agents use local models
- XML-based tool calling
- No internet required
- Lower cost, full privacy

**Fully Online (Anthropic API)**
- All agents use Claude API
- Native tool use
- Requires ANTHROPIC_API_KEY
- Higher quality, faster responses

**Hybrid**
- Mix local and Anthropic per agent
- Balance cost/quality/latency
- Example: Seniors use Anthropic, juniors use local

## Team Configuration

### Compositional Agent Profiles (8 Layers)

Each agent's prompt is composed from 8 layers:

1. **Base** (`00_base/base_agent.md`) - Universal agent behavior
2. **Role Archetype** (`01_role_archetypes/`) - Developer/Tester/Leader traits
3. **Seniority** (`02_seniority/`) - Junior/Mid/Senior cognitive patterns
4. **Specializations** (`03_specializations/`) - Domain expertise (networking, backend, etc.)
5. **Domain Knowledge** (`04_domain/`) - Technical depth in specific areas
6. **Individual Personality** (`05_individuals/`) - Unique communication styles
7. **Demographics** (configured in YAML) - Pronouns, cultural background
8. **Meta-Learnings** (`04_meta/meta_learnings.jsonl`) - Dynamic, per-agent retrospective insights

```
team_config/
├── 00_base/
│   └── base_agent.md                 # Layer 1: Common agent behavior
├── 01_role_archetypes/
│   ├── developer.md                  # Layer 2: Base developer traits
│   ├── tester.md                     # Layer 2: Base tester traits
│   └── leader.md                     # Layer 2: Leadership overlay
├── 02_seniority/
│   ├── junior.md                     # Layer 3: Junior patterns
│   ├── mid.md                        # Layer 3: Mid-level patterns
│   └── senior.md                     # Layer 3: Senior patterns
├── 03_specializations/
│   ├── networking.md                 # Layer 4: Networking expertise
│   ├── devops.md                     # Layer 4: DevOps expertise
│   ├── backend.md                    # Layer 4: Backend expertise
│   └── ...                           # Other specializations
├── 04_domain/
│   └── (domain-specific knowledge)   # Layer 5: Deep technical content
├── 05_individuals/
│   ├── alex_chen.md                  # Layer 6: Individual personalities
│   ├── priya_sharma.md
│   └── ...
├── 03_process_rules/
│   ├── xp_practices.md               # TDD, pairing, refactoring
│   ├── kanban_workflow.md            # Flow management
│   ├── pairing_protocol.md           # Collaboration mechanics
│   ├── consensus_protocol.md         # Decision escalation
│   └── artifact_standards.md         # Sprint deliverables
└── 04_meta/
    ├── retro_template.md             # Keep/Drop/Puzzle format
    ├── meta_learnings.jsonl          # Layer 8: Append-only learning log
    └── team_evolution.md             # Prompt modification rules
```

### Runtime and Tool Configuration

In `config.yaml`:

```yaml
runtimes:
  anthropic:
    enabled: true
    api_key_env: "ANTHROPIC_API_KEY"
    default_model: "claude-sonnet-4-5"

  local_vllm:
    enabled: true
    endpoint: "http://vllm-gh200-module-1:8000"
    tool_use_protocol: "xml"

  tools:
    workspace_root: "/tmp/agent-workspace"
    allowed_commands: ["git", "pytest", "python", "pip", ...]

models:
  agents:
    alex_senior_networking:
      individual: alex_chen
      seniority: senior
      specializations: [networking, security]
      role_archetype: developer+leader
      runtime: "local_vllm"  # or "anthropic"
      tools: ["filesystem", "git", "bash"]
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
```

## Running Experiments

### Quick start (no GPU required)

```bash
# Mock mode — no vLLM or database needed, agents generate real code
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/test-run \
  --db-url mock://

# Generated code will be in: /tmp/agent-workspace/sprint-01/
```

### Basic Experiment (With Code Generation)

```bash
# Run 10 sprints with agents writing real code
python -m src.orchestrator.main --sprints 10 --output outputs/experiment-001

# View generated code:
ls -la /tmp/agent-workspace/sprint-01/*/
```

### Deployment Modes

**1. Fully Offline (No Internet)**
```yaml
# config.yaml
runtimes:
  local_vllm:
    enabled: true
    endpoint: "http://localhost:8000"
  anthropic:
    enabled: false

models:
  agents:
    all_agents:
      runtime: "local_vllm"
```

**2. Fully Online (Anthropic)**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# config.yaml - set all agents to runtime: "anthropic"
python -m src.orchestrator.main --sprints 10
```

**3. Hybrid (Mix)**
```yaml
models:
  agents:
    # Seniors use Anthropic for quality
    alex_senior_networking:
      runtime: "anthropic"

    # Juniors use local for cost
    jamie_junior_fullstack:
      runtime: "local_vllm"
```

### With Disturbances / Profile Swapping

Disturbances and profile-swapping modes are controlled via `config.yaml` (not CLI flags):

```yaml
disturbances:
  enabled: true          # flip to false to disable

profile_swapping:
  mode: "constrained"    # none | constrained | free
```

Then run as usual:

```bash
python -m src.orchestrator.main --sprints 20 --output outputs/experiment-002
```

See **[docs/USAGE.md](docs/USAGE.md)** for the complete usage guide: configuration reference, disturbance types, profile swapping modes, coverage formula, and artifact format.

## Defining Work: From Backlog to Working Software

### Input: User Stories in `backlog.yaml`

Stakeholders define work using standard user stories:

```yaml
product:
  name: "TaskFlow Pro"
  description: "SaaS project management platform"

stories:
  - id: "US-001"
    title: "User can create project"
    description: "As a user, I want to create a new project so that I can organize tasks"
    acceptance_criteria:
      - "User can click 'New Project' button"
      - "Form validates required fields"
      - "Project appears in project list"
    story_points: 3
    priority: 1

    # Optional: Explicit BDD scenarios
    scenarios:
      - name: "Create project with valid data"
        given: "I am logged in"
        when: "I create a project named 'Marketing Campaign'"
        then: "I should see 'Marketing Campaign' in my project list"
```

### Workflow: Sprint Planning → Implementation → QA

1. **PO Selects Stories**: PO agent reads backlog, selects stories for sprint based on priority and capacity
2. **BDD Generation**: Stories are converted to Gherkin feature files
3. **Pairing Sessions**: Dev pairs implement features using real tools (filesystem, git, pytest)
4. **Test-Driven**: Tests run iteratively, code refined until passing
5. **Git Commits**: Working code committed to feature branches
6. **QA Review**: QA lead reviews, approves/rejects
7. **Optional Push**: If remote git enabled, creates PR and merges

### Output: Working, Tested Code

**Greenfield (New Project):**
```yaml
# Default: Fresh git workspace per story
code_generation:
  workspace_mode: "per_story"
  repo_config:
    url: ""  # Empty = create fresh repos
```

Result: `/tmp/agent-workspace/sprint-01/us-001/` with fresh git repo

**Brownfield (Existing Project):**
```yaml
# Clone and build on existing codebase
code_generation:
  workspace_mode: "per_sprint"  # Shared workspace for all stories
  persist_across_sprints: true  # Continue from previous sprint
  repo_config:
    url: "https://github.com/your-org/existing-project.git"
    branch: "main"
    clone_mode: "incremental"  # Reuse workspace, pull latest
```

Result: Agents work on actual codebase, create feature branches, build incrementally

**With Remote Git (GitHub/GitLab):**
```yaml
remote_git:
  enabled: true
  provider: "github"  # or "gitlab"
  github:
    token_env: "GITHUB_TOKEN"
```

Result: Agents push code, create PRs, QA approves via PR reviews, auto-merge to main

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

1. **Kanban Board Snapshot** (JSON) - Card states and transitions
2. **Pairing Log** (JSONL) - Dialogue, decisions, checkpoints
3. **Retro Notes** (Markdown) - Keep/Drop/Puzzle retrospective
4. **Meta-Learning Updates** (JSONL) - New learnings added to prompts
5. **Test Coverage Report** (JSON) - Process-based coverage metrics
6. **Generated Code** (Git workspaces):
   ```
   /tmp/agent-workspace/sprint-01/us-001/
   ├── features/us-001.feature      # BDD Gherkin scenarios
   ├── src/implementation.py        # Agent-generated code
   ├── tests/test_implementation.py # Agent-generated tests
   └── .git/                        # Git repo with commits on feature branch
   ```
7. **Pull Requests** (if remote git enabled):
   - Created automatically after successful implementation
   - Approved by QA lead during review phase
   - Merged to main when card moves to "done"
   - PR URLs stored in kanban card metadata
8. **Architectural Decision Records** (ADRs) - Design choices

Artifacts are stored in:
- Sprint metadata: `outputs/<experiment-id>/sprint-<N>/`
- Code workspaces: `/tmp/agent-workspace/sprint-<N>/<story-id>/`
- Remote repositories: GitHub/GitLab (if configured)

## Qualification System

Before running experiments, qualify models for each role:

```bash
# Qualify all agents (mock mode, no vLLM required)
./scripts/qualify-all-agents.sh --mock

# Qualify against a live vLLM endpoint
./scripts/qualify-all-agents.sh --vllm-endpoint http://<host>:8000
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
  quality_gates:
    min_test_coverage_lines: 85
    min_test_coverage_branches: 80

disturbances:
  enabled: true
  frequencies:
    dependency_breaks: 0.166  # 1 in 6 sprints
    production_incident: 0.125  # 1 in 8 sprints
    flaky_test: 0.25  # 1 in 4 sprints

models:
  vllm_endpoint: "http://vllm-gh200-module-1:8000"
  agents:
    dev_lead:
      model: "Qwen/Qwen2.5-Coder-32B-Instruct"
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

The factory autodiscovers profiles via glob — no code registration needed.

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
