# Agile Agent Team — CLAUDE.md

## Project Overview

This is a research project implementing an 11-agent software development team using LLMs operating under agile practices (XP + Kanban). The agents **produce actual working code** using BDD/DDD practices. The goal is to study AI team dynamics: pairing, seniority effects, meta-learning, disturbance handling, and code generation quality.

**Current State:**
- ✅ **Fully operational** - End-to-end sprint loop working
- ✅ **Code generation** - Agents write, test, and commit real code
- ✅ **Tool-using agents** - File operations, git, bash, pytest
- ✅ **BDD/DDD workflow** - Gherkin scenarios drive implementation
- ✅ **Three deployment modes** - Offline (vLLM), online (Anthropic), hybrid
- ✅ **Remote git integration** - Push to GitHub/GitLab, create PRs, auto-merge
- ✅ **Brownfield support** - Clone existing repos, incremental builds
- ✅ **Meta-learning** - Dynamic prompt evolution from retrospectives
- ✅ **Disturbance injection** - Realistic failure scenarios
- ✅ **Profile swapping** - Agents cover roles outside specialization

## Development Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest black mypy ruff  # dev tools
```

No Kubernetes or vLLM required for local development. Use mock mode (see below).

## Common Commands

```bash
# Run experiment in mock mode (no LLM calls, agents generate real code)
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/test-run \
  --db-url mock://

# View generated code
ls -la /tmp/agent-workspace/sprint-01/*/

# Tests (24 tests, all passing)
pytest tests/unit/            # Kanban, tools, runtimes
pytest tests/integration/     # Pairing, codegen, sprint workflow
pytest tests/qualification/   # Agent prompt loading
pytest                        # all tests

# Code quality
black src/
ruff check src/
mypy src/
```

## Architecture

```
src/
├── orchestrator/              # Sprint lifecycle management
│   ├── main.py                # Entry point, argparse, asyncio runner
│   ├── sprint_manager.py      # Planning → Disturbances → Dev → QA → Retro → Meta
│   ├── config.py              # YAML config loader
│   ├── backlog.py             # Product backlog management
│   └── disturbances.py        # Random failure injection
├── agents/
│   ├── base_agent.py          # BaseAgent + AgentConfig (8-layer composition)
│   ├── agent_factory.py       # Creates agents from team_config profiles
│   ├── pairing.py             # Dialogue-based pairing (legacy)
│   ├── pairing_codegen.py     # BDD-driven code generation pairing ⭐
│   └── runtime/
│       ├── base.py            # Abstract Runtime interface
│       ├── vllm_runtime.py    # Local vLLM with XML tool calling
│       └── anthropic_runtime.py  # Claude API with native tool use
├── codegen/                   # Code generation infrastructure ⭐
│   ├── workspace.py           # Per-sprint/story git workspaces
│   └── bdd_generator.py       # User stories → Gherkin features
├── tools/
│   ├── shared_context.py      # PostgreSQL/mock database
│   ├── kanban.py              # Kanban board with WIP limits
│   └── agent_tools/           # Tool system for agents ⭐
│       ├── base.py            # Tool interface
│       ├── filesystem.py      # Read/write/edit/list/search
│       ├── git.py             # Git status/diff/add/commit/remote/push
│       ├── bash.py            # Shell command execution
│       ├── test_runner.py     # Pytest execution ⭐
│       ├── remote_git.py      # GitHub/GitLab provider abstraction ⭐
│       └── factory.py         # Tool registry and creation
└── metrics/
    ├── prometheus_exporter.py # HTTP metrics server (port 8080)
    ├── custom_metrics.py      # Junior/senior-specific metrics
    └── sprint_metrics.py      # Per-sprint calculations

team_config/                   # Agent prompts (Markdown) — compositional
├── 00_base/                   # Layer 1: Universal behavior
├── 01_role_archetypes/        # Layer 2: Developer/Tester/Leader
├── 02_seniority/              # Layer 3: Junior/Mid/Senior patterns
├── 03_specializations/        # Layer 4: Domain expertise
├── 04_domain/                 # Layer 5: Deep technical knowledge
├── 05_individuals/            # Layer 6: Personalities
├── 06_process_rules/          # XP, Kanban, pairing protocols
└── 07_meta/
    ├── meta_learnings.jsonl   # Layer 8: Dynamic learnings (JSONL)
    └── ...

config.yaml                    # Experiment + runtime + tool configuration
backlog.yaml                   # Product backlog with BDD scenarios
tests/                         # unit/, integration/, qualification/
outputs/                       # Experiment artifacts (gitignored)
/tmp/agent-workspace/          # Generated code workspaces
```

## Implementation Status

| Component | Status | Details |
|---|---|---|
| **Agent system** | ✅ Complete | 8-layer compositional prompts, runtime support |
| **Tool system** | ✅ Complete | Filesystem, git (6 tools), bash, test execution |
| **Runtime system** | ✅ Complete | VLLMRuntime (XML), AnthropicRuntime (native) |
| **Code generation** | ✅ Complete | BDD → implement → test → commit → push workflow |
| **Pairing engines** | ✅ Complete | Dialogue (legacy) + CodeGen (BDD-driven) |
| **Workspace management** | ✅ Complete | Greenfield/brownfield, per-story/per-sprint modes |
| **Remote git integration** | ✅ Complete | GitHub/GitLab push, PR creation, QA approval, merge |
| **BDD/Gherkin** | ✅ Complete | Story → feature generation, step definitions |
| **Sprint lifecycle** | ✅ Complete | Planning → Dev → QA → Retro → Meta |
| **Kanban** | ✅ Complete | WIP limits, card transitions, snapshots |
| **Database** | ✅ Complete | PostgreSQL + in-memory mock mode |
| **Meta-learning** | ✅ Complete | JSONL storage, dynamic loading per agent |
| **Disturbances** | ✅ Complete | 6 types, blast radius controls, **detection wired** |
| **Profile swapping** | ✅ Complete | Swap/revert/decay, proficiency penalties |
| **Metrics** | ✅ Complete | Prometheus integration, **custom metrics recording** |
| **Testing** | ✅ Complete | 138/138 tests passing (unit/integration/qualification) |

## Code Generation Workflow

When agents have runtimes configured, the system uses **CodeGenPairingEngine**:

1. **Workspace Setup**: Create isolated git repo for story
   ```
   /tmp/agent-workspace/sprint-01/us-001/
   ```

2. **BDD Generation**: Convert story to Gherkin feature
   ```gherkin
   Feature: User registration
     Scenario: Successful registration
       Given the system is ready
       When I register with email user@example.com
       Then a new user account is created
   ```

3. **Implementation**: Driver agent uses tools to write code
   - `write_file()` - Create implementation files
   - `read_file()` - Read existing code
   - `edit_file()` - Modify code
   - `bash()` - Run commands

4. **Test Execution**: Run pytest with iteration (max 3 attempts)
   - `run_tests()` - Execute pytest
   - Parse results (passed/failed/errors)
   - On failure: read errors, fix code, re-test

5. **Git Commit**: If tests pass
   - `git_status()` - Check changes
   - `git_add()` - Stage files
   - `git_commit()` - Commit with message

6. **Kanban Update**: Move card to review

## Remote Git Integration & Brownfield Support

### Remote Git (GitHub/GitLab)

When `remote_git.enabled: true`, agents push code and create pull requests:

**Configuration:**
```yaml
# config.yaml
remote_git:
  enabled: true
  provider: "github"  # or "gitlab"

  github:
    token_env: "GITHUB_TOKEN"  # Single service account
    base_branch: "main"
    merge_method: "squash"

  gitlab:
    token_env_pattern: "GITLAB_TOKEN_{role_id}"  # Per-agent tokens
    base_branch: "main"
    merge_method: "squash"
```

**Workflow:**
1. After commit, agent pushes: `git push -u origin feature/us-001`
2. Agent creates PR/MR via `gh pr create` or `glab mr create`
3. PR URL stored in kanban card metadata
4. During QA review, if approved: `gh pr review --approve` or `glab mr approve`
5. When card moves to done: `gh pr merge --squash` or `glab mr merge --squash`

**Authentication:**
- GitHub: Single `GITHUB_TOKEN` env var (service account)
- GitLab: Per-agent tokens `GITLAB_TOKEN_{role_id}` (self-hosted)
- Git commits: Per-agent author attribution (name/email)

### Brownfield Development

**Greenfield mode** (default): Fresh git repos per story
```yaml
code_generation:
  workspace_mode: "per_story"  # Isolated workspaces
  repo_config:
    url: ""  # Empty = create fresh repos
```

**Brownfield mode**: Clone existing repos, build incrementally
```yaml
code_generation:
  workspace_mode: "per_sprint"  # Shared workspace
  persist_across_sprints: true  # Continue from previous sprint
  merge_completed_stories: true  # Auto-merge to main after QA
  repo_config:
    url: "https://github.com/your-org/existing-project.git"
    branch: "main"
    clone_mode: "incremental"  # Reuse workspace, pull latest
```

**Cross-sprint workflow:**
1. Sprint 1: Clone repo → work on stories → merge to main
2. Sprint 2: Reuse workspace → `git pull` latest → work on new stories
3. Sprint N: Accumulated work from all previous sprints

## Agent Prompt Composition (8 Layers)

Each agent's prompt is composed from 8 layers, loaded at initialization and reloaded when meta-learnings are added:

1. **Base** (`00_base/base_agent.md`) - Universal agent behavior
2. **Role Archetype** (`01_role_archetypes/`) - Developer/Tester/Leader traits
3. **Seniority** (`02_seniority/`) - Junior/Mid/Senior cognitive patterns
4. **Specializations** (`03_specializations/`) - Domain expertise (networking, backend, etc.)
5. **Domain Knowledge** (`04_domain/`) - Technical depth in specific areas
6. **Individual Personality** (`05_individuals/`) - Communication styles, quirks
7. **Demographics** (from config.yaml) - Pronouns, cultural background
8. **Meta-Learnings** (`04_meta/meta_learnings.jsonl`) - Dynamic retrospective insights

Example composition for Alex (Senior Networking Specialist):
```
Layer 1: base_agent.md
Layer 2: developer.md + leader.md
Layer 3: senior.md
Layer 4: networking.md + security.md
Layer 5: (domain files if exist)
Layer 6: alex_chen.md
Layer 7: he/him, Chinese-American
Layer 8: Filtered learnings from meta_learnings.jsonl where agent_id="alex_senior_networking"
```

## Deployment Modes

### 1. Fully Offline (Local vLLM)

```yaml
# config.yaml
runtimes:
  local_vllm:
    enabled: true
    endpoint: "http://localhost:8000"
    tool_use_protocol: "xml"  # XML-based tool calling

models:
  agents:
    all_agents:
      runtime: "local_vllm"
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
```

No internet required. Lower cost. Full privacy.

### 2. Fully Online (Anthropic API)

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

models:
  agents:
    all_agents:
      runtime: "anthropic"
```

Higher quality. Faster responses. Native tool use.

### 3. Hybrid (Mix Local and Anthropic)

```yaml
models:
  agents:
    # Seniors use Anthropic for quality
    alex_senior_networking:
      runtime: "anthropic"
      tools: ["filesystem", "git", "bash"]

    # Juniors use local for cost
    jamie_junior_fullstack:
      runtime: "local_vllm"
      tools: ["filesystem"]  # Limited tools
```

Balance cost/quality/latency per agent.

## Mock Mode for Testing

Set `MOCK_LLM=true` or use `db-url mock://` to run without LLM calls:

```bash
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/test \
  --db-url mock://
```

Mock mode returns canned responses based on role and context. **Agents still execute tools and generate real code**, but LLM generation is simulated.

## What NOT to Change

- **Research hypotheses** in `README.md` and `RESEARCH_QUESTIONS.md` — these define the experiment
- **Agent profile markdown files** in `team_config/` — cognitive patterns and seniority levels are the independent variables
- **Experiment configuration semantics** in `config.yaml` — values may change but the structure models the research design

You CAN:
- Add new tools to `src/tools/agent_tools/`
- Add new metrics to `src/metrics/`
- Improve test iteration strategies
- Enhance BDD scenario generation
- Add new disturbance types
- Improve coverage simulation formulas

## Code Conventions

- Python 3.11+, async-first (`asyncio`)
- Type hints on all function signatures
- Docstrings on all public functions and classes
- Format with `black`, lint with `ruff`, type-check with `mypy`
- Commit message prefix: `Add:`, `Fix:`, `Improve:`, `Docs:`, `Refactor:`

## Key Concepts

- **Sprint**: 60-minute wall-clock window simulating a 2-week development sprint
- **Pairing**: TDD-driven code generation — driver implements, navigator reviews, checkpoints every 25%
- **BDD/DDD**: User stories with Gherkin scenarios drive implementation
- **Tool-using agents**: Agents execute file operations, git, bash, tests via runtime
- **WIP limits**: 4 in-progress, 2 in-review (enforced by KanbanBoard)
- **Meta-learning**: After each retro, agent prompts evolve based on Keep/Drop/Puzzle analysis (stored in JSONL)
- **Profile swapping**: Agents can swap roles under defined scenarios (`none` / `constrained` / `free`)
- **Disturbances**: Randomly injected failures (flaky tests, scope creep, incidents) at configured frequencies
- **Simulated coverage**: Process-based metric (checkpoints + consensus → ~70-95% coverage)

## Infrastructure (Production)

- **vLLM** on Kubernetes GH200 nodes (3-tier by model size) OR **Anthropic API** (online)
- **PostgreSQL** for shared state (kanban, pairing logs, meta-learnings)
- **Redis** for coordination (not yet implemented)
- **Prometheus** metrics on port 8080, Grafana dashboards
- **Code artifacts** written to `/tmp/agent-workspace/sprint-<N>/<story-id>/`
- **Sprint artifacts** written to `outputs/<experiment-id>/sprint-<N>/`

## Common Development Tasks

### Run End-to-End Test

```bash
# 3 sprints, mock mode, agents generate real code
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/e2e-test \
  --db-url mock://

# Verify:
# - 3 sprint directories in /tmp/e2e-test/
# - Code workspaces in /tmp/agent-workspace/
# - meta_learnings.jsonl has new entries
# - All tests pass: pytest tests/
```

### Add a New Tool

1. Create tool class in `src/tools/agent_tools/my_tool.py`
2. Implement `Tool` interface (name, description, parameters, execute)
3. Register in `src/tools/agent_tools/factory.py` → `TOOL_REGISTRY`
4. Add to agent configs in `config.yaml` → `models.agents.*.tools`
5. Test: `pytest tests/unit/test_my_tool.py`

### Modify Agent Behavior

1. Edit relevant layer in `team_config/`
2. Run qualification tests: `pytest tests/qualification/ -v`
3. Run integration test: `MOCK_LLM=true python -m src.orchestrator.main --sprints 1 ...`
4. Verify behavior in artifacts

### Debug Pairing Session

```bash
# Run 1 sprint in mock mode
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 1 \
  --output /tmp/debug \
  --db-url mock://

# Check pairing log
cat /tmp/debug/sprint-01/pairing_log.json

# Check generated code
ls -la /tmp/agent-workspace/sprint-01/*/
```

## Testing

```bash
# All tests (24/24 passing)
pytest

# By category
pytest tests/unit/              # Kanban, tools, runtimes (10 tests)
pytest tests/integration/       # Pairing, codegen, sprint (8 tests)
pytest tests/qualification/     # Agent creation, prompts (6 tests)

# Specific test
pytest tests/integration/test_sprint_codegen.py -v
```

## Troubleshooting

### "No runtime configured" error

**Cause**: Agent has no runtime in config.yaml

**Fix**: Add runtime to agent config:
```yaml
models:
  agents:
    my_agent:
      runtime: "local_vllm"  # or "anthropic"
      tools: ["filesystem", "git"]
```

### Mock mode not activating

**Cause**: Neither MOCK_LLM=true nor db-url mock:// set

**Fix**: Use either:
```bash
MOCK_LLM=true python -m src.orchestrator.main ...
# or
python -m src.orchestrator.main --db-url mock:// ...
```

### Tests failing with path errors

**Cause**: Tool workspace sandboxing

**Fix**: Use `Path.resolve()` for temp directories:
```python
workspace = Path(tmpdir).resolve()
```

### Agents not generating code

**Cause**: Using legacy PairingEngine instead of CodeGenPairingEngine

**Fix**: Ensure agents have runtimes configured. SprintManager auto-detects and uses CodeGenPairingEngine when `_agents_have_runtimes()` returns True.

## References

- **Research design**: `README.md`, `RESEARCH_QUESTIONS.md`
- **Usage guide**: `docs/USAGE.md` (configuration, disturbances, profile swapping)
- **Implementation summary**: `docs/IMPLEMENTATION_STATUS.md` (code generation architecture)
- **Contributing**: `CONTRIBUTING.md`
- **Auto memory**: `~/.claude/projects/-Users-witlox-src-agile-agent-team/memory/MEMORY.md`
