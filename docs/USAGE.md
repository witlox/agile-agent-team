# Usage Guide

This guide covers everything you need to run experiments with agents that **generate real, tested code** — locally (mock mode) or against live LLM endpoints (vLLM or Anthropic API).

## Table of Contents

1. [Quick start (local / mock mode)](#1-quick-start-local--mock-mode)
2. [Deployment modes](#2-deployment-modes)
3. [Configuration reference](#3-configuration-reference)
4. [Remote git integration](#4-remote-git-integration)
5. [Code generation workflow](#5-code-generation-workflow)
6. [Disturbance injection](#6-disturbance-injection)
7. [Specialist consultant system](#7-specialist-consultant-system)
8. [Profile swapping](#8-profile-swapping)
9. [Team culture features](#9-team-culture-features)
10. [Test coverage (Hybrid: Real + Process)](#10-test-coverage-hybrid-real--process)
11. [Sprint artifacts](#11-sprint-artifacts)
12. [Prometheus metrics](#12-prometheus-metrics)

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
pytest                     # All 293 tests
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
| `--output` | `outputs/experiment` | Output directory |
| `--backlog` | `backlog.yaml` | Product backlog YAML |
| `--db-url` | _(from config)_ | Override database URL |

Everything else — runtimes, disturbances, profile swapping, WIP limits, team constraints — is set in `config.yaml`.

### Key config sections

```yaml
experiment:
  name: "my-experiment"
  sprint_duration_minutes: 20        # wall-clock time per sprint
  sprints_per_stakeholder_review: 5  # PO review cadence

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
    allowed_commands: ["git", "pytest", "python", "pip", ...]

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

## 6. Disturbance injection

Disturbances are controlled-chaos events that fire probabilistically each sprint. They model realistic team stress.

### How it works

After sprint planning, `DisturbanceEngine.roll_for_sprint()` runs a Bernoulli trial for each configured disturbance type. Those that fire are applied **before** development begins.

### Disturbance types

| Type | Effect | Frequency |
|------|--------|-----------|
| `dependency_breaks` | A random in-progress card is tagged `[BLOCKED: dependency unavailable]` | 16.6% (1 in 6) |
| `production_incident` | A `HOTFIX` card injected; all agents receive `[INCIDENT ALERT]` | 12.5% (1 in 8) |
| `flaky_test` | A random card is tagged `[FLAKY TESTS: intermittent failures detected]` | 25% (1 in 4) |
| `scope_creep` | A new unplanned card added mid-sprint; PO notified | 20% (1 in 5) |
| `junior_misunderstanding` | Random junior receives `[CONFUSION]` prompt to re-read | 33% (1 in 3) |
| `architectural_debt_surfaces` | Random card tagged `[TECH DEBT: refactoring required]` | 16.6% (1 in 6) |
| **`merge_conflict`** | Card tagged with merge conflict from parallel development; lead dev notified | **30% (1 in 3)** |

### Merge Conflict Disturbance (NEW)

Simulates realistic gitflow scenario:

```
[MERGE CONFLICT: main branch updated with overlapping changes]

Another pair merged changes to the same files you're working on.
You'll need to rebase your feature branch on main and resolve conflicts.
Reach out to the other pair if needed to understand their changes.
```

**Lead dev is notified** to be available for conflict resolution assistance.

### Blast radius controls

If velocity or coverage drops beyond configured thresholds (`max_velocity_impact`, `max_quality_regression`), the engine caps further injections.

### Disabling disturbances

```yaml
disturbances:
  enabled: false
```

---

## 7. Specialist consultant system

The specialist consultant system allows teams to bring in external experts when they encounter domain-specific blockers beyond their current capabilities. This provides a controlled mechanism for managing knowledge gaps while maintaining research validity.

### Overview

**Purpose**: Model realistic scenarios where teams need expertise they don't have (ML, security, performance optimization, etc.)

**Constraints**:
- **Max 3 consultations per sprint** (hard limit enforced)
- **Velocity penalty**: 2.0 story points per consultation (configurable cost)
- **Knowledge transfer**: Specialist pairs with junior/mid developer (learning opportunity)
- **Duration**: 1 day consultation (simulated)

### How it works

1. **Expertise Gap Detection**: System automatically detects when a blocker requires domain knowledge the team lacks
   - Compares blocker keywords against team's specializations
   - Triggers only when gap is genuine (team doesn't have that expertise)

2. **Specialist Request**: Dev Lead (or system) requests specialist for specific domain
   - Domain examples: `ml`, `security`, `performance`, `cloud`, `architecture`
   - System checks if consultations remaining < 3 for current sprint

3. **Temporary Agent Creation**: System creates specialist agent with domain profile
   - Loads from `team_config/08_specialists/{domain}_specialist.md`
   - Full domain expertise and teaching approach documented

4. **Knowledge Transfer Session**: Specialist pairs with team member
   - Prefers junior/mid developers (maximize learning)
   - 1-day consultation to unblock issue and teach patterns
   - Learnings recorded for team

5. **Velocity Impact**: 2.0 story points deducted from sprint velocity
   - Models time cost of onboarding and consultation
   - Tracked in sprint metrics

### Available specialist domains

| Domain | Expertise | Example Scenarios |
|--------|-----------|-------------------|
| `ml` | Machine Learning / AI | Model training issues, deployment, debugging neural networks |
| `security` | Auth, OWASP Top 10 | OAuth implementation, password hashing, XSS prevention |
| `performance` | Optimization, Profiling | API slowness, database query optimization, caching strategies |
| `cloud` | AWS, GCP, Azure, K8s | Cloud architecture, container orchestration, serverless |
| `architecture` | System design, Patterns | Scalability decisions, microservices, event-driven design |

### Configuration

```yaml
# config.yaml
specialist_consultants:
  enabled: true
  max_per_sprint: 3
  velocity_penalty: 2.0  # story points
```

### Manual usage (future enhancement)

In daily standups, if Dev Lead identifies a blocker requiring external expertise:

```python
from src.orchestrator.specialist_consultant import SpecialistRequest

request = SpecialistRequest(
    reason="Team stuck on ML model training - accuracy won't improve",
    domain="ml",
    requesting_agent_id="ahmed_dev_lead",
    sprint_num=3,
    day_num=5,
)

outcome = await specialist_system.request_specialist(request, team)
```

### Metrics

Specialist consultations are tracked in Prometheus metrics:

- `specialist_consultations_total` - Counter by domain, sprint, reason category
- `specialist_velocity_penalty` - Gauge tracking story points lost

### Research impact

This feature enables studying:
- How teams handle knowledge gaps under constraints
- Trade-offs between velocity and external help
- Impact of specialist knowledge transfer on team capabilities
- Optimal timing for bringing in external experts

**Balance**: Realistic (teams do need external help) but constrained (limited, costly) to maintain research validity

### Disabling specialist consultants

To disable for pure team-only experiments:

```yaml
specialist_consultants:
  enabled: false
```

Or simply don't configure the feature (defaults to disabled).

---

## 8. Profile swapping

Profile swapping lets agents temporarily work outside their specialisation. It models cross-training, incidents, and organizational resilience.

### Modes

| Mode | Behaviour |
|------|-----------|
| `none` | Agents never swap. Knowledge silos surface as bottlenecks. |
| `constrained` | Swaps only when an `allowed_scenario` triggers (e.g. `production_incident`). Penalties applied. |
| `free` | Any agent may cover any domain. No penalty. AI-optimal baseline. |

### What happens during a swap

1. A `production_incident` disturbance fires.
2. `SprintManager._check_swap_triggers()` finds the senior DevOps or networking agent.
3. `agent.swap_to(domain, proficiency)` appends a notice to the agent's prompt:

```
[PROFILE SWAP ACTIVE]
You are temporarily covering production incident response tasks. Proficiency: 70%.
You are less familiar with this domain — ask more questions, verify assumptions,
and expect to work 20% slower than your usual pace.
```

4. If the swapped agent is in a pairing session, an **extra checkpoint round** is added (simulating 20% slowdown).
5. After the sprint, `decay_swap()` reduces proficiency or reverts if `knowledge_decay_sprints` elapsed.

### Swap state

The `BaseAgent.is_swapped` property returns `True` while a swap is active. Swap state in `agent._swap_state`:

```python
{
  "role_id": "incident_responder",
  "domain": "production incident response",
  "proficiency": 0.70,
  "sprint": 3,
}
```

---

## 9. Team culture features

### Role-Based Pairing

Pairing role assignment follows team culture:

1. **Lead dev always navigates** (90%+ of sessions) - teaching role, team growth focus
2. **Testers always navigate** when pairing with devs - quality perspective
3. **Seniors navigate with juniors** - mentorship, knowledge transfer
4. **Same level pairs** - random assignment

**Example assignments**:
- Ahmed (lead dev) + Marcus (mid backend) → Marcus drives, Ahmed navigates
- Yuki (senior tester) + Elena (mid frontend) → Elena drives, Yuki navigates
- Alex (senior) + Jamie (junior) → Jamie drives, Alex navigates

### Git Workflow (Stable Main + Gitflow)

**Documented in** `team_config/03_process_rules/git_workflow.md`

- **Stable main**: Always deployable, always green, always tested
- **Feature branches**: Created automatically per story (`feature/<story-id>`)
- **Merge conflict resolution**: Expected, protocol documented
- **"You break it, you fix it"**: Build ownership with team support
- **Blameless post-mortems**: "We fix systems, not people"

### Hiring Protocol

**Documented in** `team_config/03_process_rules/hiring_protocol.md`

- **3 rounds**: Technical → Domain Fit → Pairing Under Pressure
- **Keyboard switching**: 5min → 3min → 2min → 1min (increasing pressure)
- **Lead dev observes** behavior in Round 3 (not just code)
- **A+ candidates only**: Must score A in all rounds

**Note**: In the simulation, agents are static, but this documents the "in-universe" hiring culture.

### Team Constraints

- **Max 10 engineers** (excluding testers)
- **Turnover simulation** (optional, for experiments >5 months)
- **Tester pairing** (20% of sessions, always as navigator)

---

## 10. Test coverage (Hybrid: Real + Process)

The system tracks **two types of coverage** to measure both code quality and process adherence:

### Real Coverage (pytest-cov)

**Actual line and branch coverage** from pytest-cov, measuring how much of the generated code is tested:

- Collected automatically during test execution via `--cov=src --cov-branch`
- Parses `coverage.json` for precise metrics
- Stored per session: `line_coverage`, `branch_coverage`, `covered_lines`, `total_lines`
- Sprint-level: story-point-weighted average across sessions

**Example metrics:**
```json
{
  "line_coverage": 87.5,
  "branch_coverage": 82.3,
  "covered_lines": 145,
  "total_lines": 166
}
```

### Process Coverage (TDD Protocol Adherence)

**Process-based metric** measuring how thoroughly the TDD pairing protocol was followed:

```
base_coverage = 70.0        # floor if no TDD checkpoints
per_checkpoint = 3.5        # each completed checkpoint adds coverage
consensus_bonus = 5.0       # both agents approve → bonus
max_coverage = 95.0

process_coverage = min(base + checkpoints_completed * per_checkpoint + bonus, max)
```

With default 4-checkpoint protocol + consensus:
- Process coverage ≈ 70 + 4×3.5 + 5 = **89%**

If agent is swapped (extra checkpoint from 20% slowdown):
- 5 checkpoints → 70 + 5×3.5 + 5 = **92.5%**

### Why Track Both?

| Metric | Measures | Research Value |
|--------|----------|----------------|
| **Real coverage** | Code quality | How thoroughly agents test their implementations |
| **Process coverage** | Team discipline | How well agents follow TDD practices |

**Example insights:**
- High process, low real → Team follows protocol but writes ineffective tests
- Low process, high real → Team skips checkpoints but writes good tests anyway
- High both → Mature team with strong practices
- Low both → Red flag for team dynamics

### Sprint-Level Aggregation

All coverage metrics are story-point-weighted averages:

```
sprint_metric = Σ(session_metric × story_points) / Σ(story_points)
```

Appears in `final_report.json`:
```json
{
  "sprint": 1,
  "test_coverage": 87.5,      # Real line coverage
  "branch_coverage": 82.3,    # Real branch coverage
  "process_coverage": 89.0    # TDD protocol adherence
}
```

### Prometheus Metrics

Three gauges exported:
- `test_coverage_percent` - Real line coverage from pytest-cov
- `branch_coverage_percent` - Real branch coverage from pytest-cov
- `process_coverage_percent` - Process-based TDD adherence

### Configuration

```yaml
code_generation:
  coverage:
    enabled: true  # Collect real coverage (default)
    source: "src"  # Directory to measure
    min_line_coverage: 85
    min_branch_coverage: 80
```

### Disabling Real Coverage

To use only process-based coverage (faster, no pytest-cov overhead):

```yaml
code_generation:
  coverage:
    enabled: false
```

Agents will still run tests, but won't collect coverage metrics.

---

## 11. Sprint artifacts

### Sprint Metadata (`<output>/sprint-NN/`)

| File | Contents |
|------|----------|
| `kanban.json` | Full board snapshot: `ready`, `in_progress`, `review`, `done` (includes PR URLs in card metadata) |
| `pairing_log.json` | All pairing session records (driver, navigator, outcomes, coverage, PR URLs) |
| `retro.md` | Keep / Drop / Puzzle retrospective notes |

### Generated Code Workspaces (`/tmp/agent-workspace/sprint-NN/<story-id>/`)

```
sprint-01/
├── us-001/
│   ├── features/
│   │   └── us-001.feature         # BDD Gherkin scenarios
│   ├── src/
│   │   └── registration.py        # Agent-generated implementation
│   ├── tests/
│   │   └── test_registration.py   # Agent-generated tests
│   └── .git/                      # Git repo on feature/us-001 branch
└── us-002/
    └── ...
```

### Final Report (`<output>/final_report.json`)

```json
{
  "experiment": "baseline-experiment",
  "total_sprints": 10,
  "avg_velocity": 5.2,
  "total_features": 21,
  "sprints": [
    {
      "sprint": 1,
      "velocity": 5,
      "features_completed": 2,
      "test_coverage": 89.0,
      "pairing_sessions": 3,
      "cycle_time_avg": 0.00012,
      "disturbances": ["merge_conflict", "flaky_test"]
    },
    ...
  ]
}
```

### Pairing Session Details (`pairing_log.json`)

```json
{
  "sprint": 1,
  "driver_id": "marcus_mid_backend",
  "navigator_id": "ahmed_senior_dev_lead",
  "task_id": 3,
  "start_time": "2026-02-08T14:05:11.123456",
  "end_time": "2026-02-08T14:05:11.234567",
  "outcome": "completed",
  "coverage_estimate": 89.0,
  "workspace": "/tmp/agent-workspace/sprint-01/us-001",
  "feature_file": "/tmp/agent-workspace/sprint-01/us-001/features/us-001.feature",
  "files_changed": ["src/registration.py", "tests/test_registration.py"],
  "test_results": {
    "passed": true,
    "iterations": 1,
    "output": "2 passed in 0.05s"
  },
  "commit_sha": "committed",
  "pr_url": "https://github.com/your-org/project/pull/42"
}
```

**Note:** `pr_url` is only present when `remote_git.enabled: true` and push/PR creation succeeded.

---

## 12. Prometheus metrics

The metrics server starts automatically on port 8080.

### Standard Sprint Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `sprint_velocity` | Gauge | Story points completed last sprint |
| `test_coverage_percent` | Gauge | Weighted coverage estimate last sprint |
| `pairing_sessions_total` | Counter | Cumulative sessions, labelled `driver`/`navigator` |
| `consensus_seconds` | Histogram | Time-to-consensus distribution |

These are updated via `update_sprint_metrics()` after each sprint completes.

### Custom Junior/Senior Metrics (NEW)

Research-focused metrics tracking team dynamics:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `junior_questions_total` | Counter | `junior_id`, `category`, `resulted_in_change` | Questions asked by juniors during ceremonies |
| `reverse_mentorship_events` | Counter | `junior_id`, `senior_id`, `topic` | Junior-led pairing sessions (junior drives, senior navigates) |
| `senior_learned_from_junior` | Counter | `senior_id`, `junior_id`, `learning_type` | Times senior updated knowledge based on junior input |
| `junior_question_rate_per_sprint` | Gauge | `junior_id` | Number of questions per sprint per junior |
| `question_dismissal_rate` | Gauge | `senior_id` | Percentage of junior questions dismissed without consideration |

**Recording Points**:
- `junior_questions_total`: Recorded during story refinement when juniors ask clarifying questions
- `reverse_mentorship_events`: Recorded at pairing session start when junior is driver
- Other metrics: Available for future enhancement

**Research Value**: These metrics enable measurement of:
- Junior engagement and curiosity
- Reverse knowledge transfer (junior → senior)
- Team learning culture health
- Impact of junior developers on team outcomes

**Access raw metrics:**

```bash
curl http://localhost:8080/metrics
```

**Grafana dashboards** (if deployed):
- Sprint Overview: Velocity, quality metrics, cycle time
- Team Health: Pairing activity, consensus time
- Agent Performance: Response times, token usage

---

## Advanced Usage

### Experiment Variants

| Goal | Config change |
|------|--------------|
| No disturbances (pure team dynamics) | `disturbances.enabled: false` |
| No profile swapping (stable roles) | `profile_swapping.mode: none` |
| Free swapping (AI-optimal baseline) | `profile_swapping.mode: free` |
| High disturbance rate (stress test) | Increase all `frequencies` values |
| Shorter sprints (rapid iteration) | `sprint_duration_minutes: 10` |
| Turnover simulation (long experiments) | `team.turnover.enabled: true` |
| More tester participation | `team.tester_pairing.frequency: 0.40` |

### Recommended Experiment Sequence

1. **Baseline**: `disturbances: false`, `swap: none` → 10 sprints
2. **Disturbances only**: `disturbances: true`, `swap: none` → 10 sprints
3. **Full chaos**: `disturbances: true`, `swap: constrained` → 20 sprints
4. **AI-optimal**: `disturbances: true`, `swap: free` → 20 sprints
5. **Long-term**: Enable turnover, run 30+ sprints

Compare `final_report.json` across runs to measure resilience and learning curves.

### Debugging

**Check agent pairing roles:**
```bash
cat /tmp/experiment/sprint-01/pairing_log.json | jq '.[] | {driver: .driver_id, navigator: .navigator_id}'
```

**Check generated code quality:**
```bash
cd /tmp/agent-workspace/sprint-01/us-001/
git log --oneline
pytest tests/
```

**Check disturbance impact:**
```bash
cat /tmp/experiment/final_report.json | jq '.sprints[] | {sprint, velocity, disturbances}'
```

**Check meta-learnings:**
```bash
cat team_config/04_meta/meta_learnings.jsonl | jq 'select(.agent_id == "alex_senior_networking")'
```

---

**Next**: See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details and [AGENT_RUNTIMES.md](AGENT_RUNTIMES.md) for runtime implementation.
