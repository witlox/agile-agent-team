# Usage Guide

This guide covers everything you need to run experiments with agents that **generate real, tested code** — locally (mock mode) or against live LLM endpoints (vLLM or Anthropic API).

## Table of Contents

1. [Quick start (local / mock mode)](#1-quick-start-local--mock-mode)
2. [Deployment modes](#2-deployment-modes)
3. [Configuration reference](#3-configuration-reference)
4. [Remote git integration](#4-remote-git-integration)
5. [Code generation workflow](#5-code-generation-workflow)

---

## 1. Quick start (local / mock mode)

No Kubernetes, no GPU, no database required. **Agents still generate real code even in mock mode.**

```bash
# Clone and set up
git clone https://github.com/witlox/agile-agent-team
cd agile-agent-team

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install  # Wire git hooks (black, ruff, mypy)

# Run 3 sprints with fully mocked LLM and in-memory database
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/my-first-run \
  --db-url mock://
```

You should see output like:

```
SPRINT 1  [14:05:11]
============================================================
  Planning...
  [DISTURBANCE] merge_conflict
  [DISTURBANCE] junior_misunderstanding
  Development...
  QA review...
  Retrospective...
  Meta-learning...
  Artifacts...
  velocity=5pts  done=2  sessions=3  coverage=89%

...
Experiment complete. Output: /tmp/my-first-run
```

**View generated code:**

```bash
# Sprint artifacts (kanban, pairing logs, retros)
ls -la /tmp/my-first-run/sprint-*/

# Generated code workspaces (BDD features, implementation, tests, git repos)
ls -la /tmp/agent-workspace/sprint-01/*/

# Check a BDD feature file
cat /tmp/agent-workspace/sprint-01/us-001/features/us-001.feature

# Check git commits
cd /tmp/agent-workspace/sprint-01/us-001/
git log --oneline
git branch
```

### Mock mode activation

Mock mode is triggered by **either**:

| Method | Value |
|--------|-------|
| Environment variable | `MOCK_LLM=true` |
| vLLM endpoint in config | `mock://` |
| `--db-url` CLI flag | `mock://` |

In mock mode:
- Agents return canned responses keyed on `role_id`
- In-memory store replaces PostgreSQL
- **Agents still execute tools and generate real code**

### Running the tests

```bash
pytest tests/unit/         # Tools, config, backlog, kanban, runtimes, multi-language
pytest tests/integration/  # Pairing, codegen, ceremonies, remote git, sprint workflow
pytest tests/qualification/  # Agent creation, prompts
pytest                     # All tests
```

---

## 2. Deployment modes

The system supports three deployment modes:

### Mode 1: Fully Offline (Local vLLM)

**No internet required.** All agents use local models with XML-based tool calling.

```yaml
# config.yaml
runtimes:
  local_vllm:
    enabled: true
    endpoint: "http://localhost:8000"  # or your vLLM server
    tool_use_protocol: "xml"
  anthropic:
    enabled: false

models:
  agents:
    all_agents:
      runtime: "local_vllm"
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
```

**Benefits:**
- ✅ Full privacy (no data leaves your network)
- ✅ No API costs
- ✅ Works in air-gapped environments

**Requirements:**
- vLLM server running (GPU-accelerated recommended)
- Models: DeepSeek, Qwen, or similar (70B+ recommended for quality)

### Mode 2: Fully Online (Anthropic API)

**Internet required.** All agents use Claude API with native tool use.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```yaml
# config.yaml
runtimes:
  anthropic:
    enabled: true
    api_key_env: "ANTHROPIC_API_KEY"
    default_model: "claude-sonnet-4-5"
  local_vllm:
    enabled: false

models:
  agents:
    all_agents:
      runtime: "anthropic"
```

**Benefits:**
- ✅ Highest quality (Claude Opus 4.6 / Sonnet 4.5)
- ✅ No infrastructure to manage
- ✅ Faster response times

**Costs:**
- API usage charges (varies by model)

### Mode 3: Hybrid (Mix Local and Anthropic)

**Balance cost, quality, and latency** by assigning different runtimes per agent.

```yaml
models:
  agents:
    # Seniors and leads use Anthropic for highest quality
    ahmed_senior_dev_lead:
      runtime: "anthropic"
      tools: ["filesystem", "git", "bash"]

    alex_senior_networking:
      runtime: "anthropic"
      tools: ["filesystem", "git", "bash"]

    # Mid-level use local for cost savings
    marcus_mid_backend:
      runtime: "local_vllm"
      tools: ["filesystem", "git"]

    # Juniors use local (appropriate for their level)
    jamie_junior_fullstack:
      runtime: "local_vllm"
      tools: ["filesystem"]
```

**Strategy:**
- High-stakes decisions → Anthropic
- Code generation → Anthropic for seniors, local for juniors
- Testing/QA → Local is often sufficient

---

## 3. Configuration reference

All experiment parameters live in `config.yaml`. The CLI only exposes:

| Flag | Default | Purpose |
|------|---------|---------|
| `--config` | `config.yaml` | Path to config file |
| `--sprints` | `10` | Number of sprints to run |
| `--duration` | _(from config)_ | Override sprint duration (minutes) |
| `--output` | `outputs/experiment` | Output directory |
| `--backlog` | `backlog.yaml` | Product backlog YAML |
| `--db-url` | _(from config)_ | Override database URL |

Everything else — runtimes, disturbances, profile swapping, WIP limits, team constraints — is set in `config.yaml`.

### Key config sections

```yaml
experiment:
  name: "my-experiment"
  sprint_duration_minutes: 20        # wall-clock time per sprint
  sprints_per_stakeholder_review: 3  # PO review cadence

team:
  max_engineers: 10                  # Excluding testers
  max_total_team_size: 13            # Including testers/PO/leads

  wip_limits:
    in_progress: 4
    review: 2

  # Turnover simulation (optional, for long experiments >5 months)
  turnover:
    enabled: false
    starts_after_sprint: 10          # ~5 months
    probability_per_sprint: 0.05     # 5% chance per sprint
    backfill_enabled: true

  # Tester participation in pairing
  tester_pairing:
    enabled: true
    frequency: 0.20                  # 20% of sessions
    role: "navigator"                # Testers always navigate

disturbances:
  enabled: true
  frequencies:
    dependency_breaks: 0.166         # 1 in ~6 sprints
    production_incident: 0.125       # 1 in ~8
    flaky_test: 0.25                 # 1 in 4
    scope_creep: 0.20                # 1 in 5
    junior_misunderstanding: 0.33    # 1 in 3
    architectural_debt_surfaces: 0.166
    merge_conflict: 0.30             # 1 in 3 (expected with gitflow)
  blast_radius_controls:
    max_velocity_impact: 0.30        # cap velocity drop at 30%
    max_quality_regression: 0.15     # cap coverage drop at 15%

profile_swapping:
  mode: "constrained"                # none | constrained | free
  allowed_scenarios:
    - "critical_production_incident"
    - "specialist_unavailable"
    - "deliberate_cross_training"
  penalties:
    context_switch_slowdown: 1.20    # 20% slower on first task
    proficiency_reduction: 0.70      # 70% of specialist capability
    knowledge_decay_sprints: 1       # revert after 1 sprint unused

# Runtime configurations
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
    allowed_commands:  # 48 commands: git, gh, glab, python, go, cargo, npm, cmake, etc.

# Agent definitions
models:
  agents:
    alex_senior_networking:
      runtime: "local_vllm"  # or "anthropic"
      tools: ["filesystem", "git", "bash"]
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
      temperature: 0.7
      max_tokens: 3072
```

---

## 4. Remote git integration

Agents can push code to GitHub or GitLab, create pull requests, and have QA leads approve and merge them automatically. This makes the simulation behave like a real development team working with remote repositories.

### Enable remote git

```yaml
# config.yaml
remote_git:
  enabled: true  # Set to true to enable push/PR workflow
  provider: "github"  # Options: github | gitlab
```

**Requirements:**
- GitHub: `gh` CLI installed, `GITHUB_TOKEN` environment variable set
- GitLab: `glab` CLI installed, per-agent tokens or single service token set

### GitHub configuration (single service account)

**Recommended approach:** One service account pushes for all agents, but git commits show individual agent attribution.

```yaml
remote_git:
  enabled: true
  provider: "github"

  github:
    token_env: "GITHUB_TOKEN"  # Environment variable containing token
    base_branch: "main"
    merge_method: "squash"  # Options: merge | squash | rebase
    draft_prs: false  # Create PRs as drafts initially

  author_email_domain: "agent.local"  # Generates alex_senior_networking@agent.local
```

**Setup:**
```bash
# Create GitHub personal access token with repo permissions
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Verify gh CLI authentication
gh auth status
```

**Git commits show:**
```
Author: Alex Chen <alex_senior_networking@agent.local>
Committer: Service Account <service@github.com>
```

### GitLab configuration (per-agent accounts)

**For self-hosted GitLab instances:** Each agent can have their own account with individual project access tokens.

```yaml
remote_git:
  enabled: true
  provider: "gitlab"

  gitlab:
    token_env_pattern: "GITLAB_TOKEN_{role_id}"  # Pattern for per-agent tokens
    base_branch: "main"
    merge_method: "squash"  # Options: merge | squash
    draft_prs: false

  author_email_domain: "agent.local"
```

**Setup:**
```bash
# Create project access tokens for each agent (or use personal access tokens)
export GITLAB_TOKEN_alex_senior_networking="glpat-xxxxxxxxxxxxxxxxxxxx"
export GITLAB_TOKEN_priya_senior_devops="glpat-xxxxxxxxxxxxxxxxxxxx"
export GITLAB_TOKEN_marcus_mid_backend="glpat-xxxxxxxxxxxxxxxxxxxx"
# ... one token per agent

# Verify glab CLI authentication
glab auth status
```

### Workflow with remote git

When `remote_git.enabled: true`:

1. **Feature branch creation:** Agents create `feature/<story-id>` branches as usual
2. **Implementation:** Agents write code, run tests, commit locally
3. **Push to remote:** After successful commit, agent pushes branch: `git push -u origin feature/us-001`
4. **PR/MR creation:** Agent uses `gh pr create` or `glab mr create` with:
   - Title: Story title
   - Body: Agent name, commit SHA, acceptance criteria
   - Base: `main`, Head: `feature/<story-id>`
5. **QA approval:** During QA review phase, if approved, QA lead uses `gh pr review --approve` or `glab mr approve`
6. **Merge:** When card moves to "done", agent merges PR/MR with configured merge method
7. **Branch cleanup:** Feature branch deleted after merge

**PR URLs are stored in kanban card metadata** for traceability.

### Disabling remote git

To work with local git only (no push/PR):

```yaml
remote_git:
  enabled: false
```

Agents still create git repos and commits locally, but nothing pushes to remote.

---

## 5. Code generation workflow

When agents have runtimes configured, the system uses **CodeGenPairingEngine** for real code generation:

### BDD-Driven Workflow

```
User Story (backlog.yaml with scenarios)
    ↓
Sprint Planning (PO selects stories)
    ↓
Workspace Setup
  - Create /tmp/agent-workspace/sprint-N/story-id/
  - Initialize git repo
  - Create feature branch: feature/story-id
    ↓
BDD Generation
  - Convert story to Gherkin feature file
  - Extract Given/When/Then scenarios
    ↓
Pairing Session (Driver + Navigator)
  - Driver uses execute_coding_task() with tools:
    • write_file() - Create implementation
    • edit_file() - Modify code
    • read_file() - Read existing code
    • bash() - Run commands
  - Navigator reviews, guides, asks questions
  - Checkpoints every 25% completion
    ↓
Test Execution (via RunTestsTool)
  - Agent runs: pytest tests/
  - Parse results: passed/failed/errors
  - If tests fail:
    • Read error output
    • Fix code
    • Re-run tests (max 3 iterations)
    ↓
Git Commit (if tests pass)
  - git_status() - Check changes
  - git_add() - Stage files
  - git_commit() - Commit with message:
    "feat: User registration (US-001)"
    ↓
Kanban Update
  - Move card from in_progress → review
```

### Workspace modes: Greenfield vs Brownfield

The system supports two workspace modes for different development scenarios:

#### Greenfield (fresh projects)

Each story gets an isolated workspace with a fresh git repository.

```yaml
# config.yaml
code_generation:
  workspace_mode: "per_story"  # Isolated workspace per story
  persist_across_sprints: false
  merge_completed_stories: false
  repo_config:
    url: ""  # Empty = create fresh repos
    branch: "main"
    clone_mode: "fresh"
```

**Result:** `/tmp/agent-workspace/sprint-01/us-001/` contains a fresh git repo for US-001

**Best for:**
- New projects starting from scratch
- Isolated feature prototypes
- Testing individual stories independently

#### Brownfield (existing codebases)

Clone an existing repository and build on it incrementally.

```yaml
# config.yaml
code_generation:
  workspace_mode: "per_sprint"  # Shared workspace for all stories in sprint
  persist_across_sprints: true  # Continue from previous sprint's main
  merge_completed_stories: true  # Auto-merge to main after QA approval
  repo_config:
    url: "https://github.com/your-org/existing-project.git"
    branch: "main"
    clone_mode: "incremental"  # Reuse workspace, pull latest
```

**Result:** All stories in sprint work on the same cloned repo, building on previous work

**Workflow:**
1. Sprint 1: Clone repo → work on stories → merge to local main
2. Sprint 2: Reuse workspace → pull latest → work on new stories → merge
3. Sprint N: Accumulated work from all previous sprints

**Best for:**
- Adding features to existing projects
- Multi-sprint product development
- Simulating long-term team dynamics

#### Workspace mode comparison

| Mode | Isolation | Git repos | Cross-sprint | Use case |
|------|-----------|-----------|--------------|----------|
| `per_story` | High | One per story | No | Greenfield, prototypes |
| `per_sprint` | Low | One per sprint | Optional | Brownfield, products |

#### Clone mode options

| Mode | Behavior | When to use |
|------|----------|-------------|
| `fresh` | Delete and re-clone each time | Testing, clean slate |
| `incremental` | Reuse workspace, `git pull` latest | Brownfield, continuity |

### Product Context (Mission, Vision, Goals)

The `product:` section in `backlog.yaml` carries stakeholder context that goes beyond individual stories — the "why" behind the product. When present, this context is automatically:

1. **Fed to the PO during Sprint 0** — the PO reads the context and produces a Business Knowledge Brief that informs all subsequent story presentations
2. **Injected into every story refinement** — the PO grounds story presentations in mission/vision when presenting to the team
3. **Available in stakeholder reviews** — context anchors periodic stakeholder review sessions

```yaml
# backlog.yaml
product:
  name: "TaskFlow - Collaborative Task Manager"
  description: >
    A lightweight task management app for small engineering teams.

  # Stakeholder context — these fields activate the context system.
  # If mission, vision, or goals are absent, context injection is silently skipped.
  mission: >
    Help small engineering teams stay focused on what matters by providing
    a frictionless, opinionated task management workflow that grows with them.
  vision: >
    Become the default task manager for teams of 5-50 engineers who value
    simplicity over feature bloat, shipping a focused product that
    integrates tightly with GitHub/GitLab and CI/CD pipelines.
  goals:
    - "Launch MVP with core task management within 3 months"
    - "Achieve 100 active teams within 6 months of launch"
    - "Maintain <500ms p95 API latency at scale"
    - "Reach feature parity with basic Trello workflows by v1.0"
  target_audience: >
    Small to mid-size software engineering teams (5-50 people) who
    currently use spreadsheets, sticky notes, or overly complex tools
    like Jira and want something lightweight and developer-friendly.
  success_metrics:
    - "Weekly active teams (WAT)"
    - "Task completion rate (tasks done / tasks created)"
    - "Time to first task (onboarding friction)"
    - "NPS score from team leads"

  # Technical setup (used by Sprint 0)
  languages: [python, typescript]
  tech_stack: [docker, github-actions, pytest, jest]
```

**Activation**: Automatic. If `mission`, `vision`, or `goals` are present under `product:`, the context system is active. No config flag needed. Remove those fields (or leave them empty) to disable.

**How the PO uses it**: During Sprint 0, the PO agent receives the context and produces a Business Knowledge Brief. This brief shapes how the PO presents stories throughout the experiment — grounding acceptance criteria, priorities, and trade-off decisions in the product's purpose.

### Domain Research (Context Documents + Web Search)

Beyond the static product context, the PO can perform active research during Sprint 0. Two optional layers enrich the PO's domain knowledge:

**Layer 1 — Context Documents**: Local files (markdown, text) that the PO reads during Sprint 0 to absorb stakeholder-provided knowledge.

```yaml
# backlog.yaml
product:
  context_documents:
    - "docs/product_vision.md"
    - "docs/competitive_analysis.md"
```

**Layer 2 — Web Search**: The PO searches the web for competitor analysis, market context, and technical landscape. Three runtime paths are supported:

| Runtime | Web Search Approach |
|---------|-------------------|
| **Anthropic** | Native `web_search` server tool in the API — no custom tool needed |
| **vLLM** | Custom `web_search` + `web_fetch` agent tools calling a configured search API |
| **Mock** | Canned search results for testing (no API key needed) |

**Configuration:**

```yaml
# config.yaml
domain_research:
  enabled: true                     # Master switch (default: false)
  context_documents:                # Local files for PO to read
    - "docs/product_vision.md"
  web_search:
    enabled: true                   # Enable web search (default: false)
    engine: "brave"                 # brave | google | kagi
    api_key_env: "BRAVE_API_KEY"    # Env var holding the search API key
    max_results: 5                  # Results per query
```

**Setup for each search engine:**

```bash
# Brave (recommended — generous free tier)
export BRAVE_API_KEY="BSA..."

# Google Custom Search
export GOOGLE_API_KEY="AIza..."
# Also set google_cx in config: web_search.google_cx: "your-cx-id"

# Kagi
export KAGI_API_KEY="..."
```

**How it works:**

1. During Sprint 0, if `domain_research.enabled: true` and the PO has a runtime:
   - PO reads any `context_documents` listed in backlog.yaml using `read_file`
   - PO searches the web using `web_search` (or Anthropic's native search)
   - PO fetches and reads key pages using `web_fetch`
2. PO writes a comprehensive **Business Knowledge Brief** covering:
   - Elevator pitch, key differentiators, competitive landscape
   - User personas, definition of success, scope boundaries
   - Technical landscape and trends
3. Brief stored in PO conversation history for the entire experiment

**Fallback**: If domain research is disabled or the PO has no runtime, the PO falls back to the original generate-only path (rephrasing the backlog context without external knowledge).

**Disabling domain research:**

```yaml
domain_research:
  enabled: false
```

Or simply omit the `domain_research` section entirely (backward compatible).

### Backlog Format with BDD

```yaml
# backlog.yaml
stories:
  - id: US-001
    title: "User registration"
    description: "As a new user I can register with email and password"
    acceptance_criteria:
      - "Email format validated"
      - "Password hashed with bcrypt"
    story_points: 3
    priority: 1
    scenarios:  # BDD scenarios (Given/When/Then)
      - name: "Successful registration"
        given:
          - "the system is ready"
          - "no user exists with email user@example.com"
        when:
          - "I register with email user@example.com and password SecurePass123"
        then:
          - "a new user account is created"
          - "the password is hashed with bcrypt"
```

The system auto-generates Gherkin feature files from these scenarios.

### Generated Artifacts

**Per story workspace**:
```
/tmp/agent-workspace/sprint-01/us-001/
├── features/
│   └── us-001.feature           # Generated Gherkin
├── src/
│   └── registration.py          # Agent-generated code
├── tests/
│   └── test_registration.py     # Agent-generated tests
└── .git/                        # Git repo on feature/us-001 branch
```

---

**Next**: See [ADVANCED_USAGE.md](ADVANCED_USAGE.md) for disturbances, profile swapping, team culture, metrics, experiment variants, and multi-team orchestration.
