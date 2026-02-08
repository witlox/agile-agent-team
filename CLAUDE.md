# Agile Agent Team — CLAUDE.md

## Project Overview

This is a research project simulating an 11-agent software development team using LLMs operating under agile practices (XP + Kanban). The goal is to study AI team dynamics: pairing, seniority effects, meta-learning, and disturbance handling.

**Dual nature of this project:**
- It is a *research design* (hypotheses, agent profiles, process rules) — treat as authoritative
- It is an *implementation in progress* (~5% of business logic implemented) — stubs need completing

## Development Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest black mypy ruff  # dev tools
```

No Kubernetes or vLLM required for local development. Use mocked LLM responses (see below).

## Common Commands

```bash
# Run experiment (requires vLLM endpoint configured)
python src/orchestrator/main.py --sprints 10 --output results/experiment-001

# Tests
pytest tests/unit/
pytest tests/integration/
pytest tests/qualification/
pytest  # all

# Code quality
black src/
ruff check src/
mypy src/
```

## Architecture

```
src/
├── orchestrator/       # Sprint lifecycle management
│   ├── main.py         # Entry point, argparse, asyncio runner
│   ├── sprint_manager.py  # Planning → Development → Retro loop
│   └── config.py       # YAML config loader
├── agents/
│   ├── base_agent.py   # BaseAgent + AgentConfig dataclass
│   ├── agent_factory.py  # Creates agents from team_config profiles
│   └── pairing.py      # PairingEngine for TDD dialogue sessions
├── tools/
│   ├── shared_context.py  # PostgreSQL connection + schema
│   └── kanban.py          # Kanban board operations
└── metrics/
    ├── prometheus_exporter.py  # HTTP metrics server (port 8080)
    ├── custom_metrics.py       # Junior/senior-specific metrics
    └── sprint_metrics.py       # Per-sprint metric calculations

team_config/            # Agent prompts (Markdown) — do not change research design
config.yaml             # Experiment configuration
tests/                  # unit/, integration/, qualification/
outputs/                # Experiment artifacts (gitignored)
```

## Implementation Status

Most business logic is stubs (`pass`). Key areas needing implementation:

| Component | File | Status |
|---|---|---|
| Agent prompt loading | `agents/base_agent.py:_load_prompt` | Stub |
| Pairing dialogue | `agents/pairing.py` | All stubs |
| Sprint planning/retro | `orchestrator/sprint_manager.py` | Stubs |
| Kanban CRUD | `tools/kanban.py` | Stubs |
| Database operations | `tools/shared_context.py` | Schema only |
| Sprint metrics | `metrics/sprint_metrics.py` | Stub |
| Meta-learning system | `team_config/04_meta/` | No code |
| Disturbance injection | Referenced in `config.yaml` | No code |
| Profile swapping | Referenced in `config.yaml` | No code |

## Mocking for Local Development

When implementing stubs, add a mock mode so that `BaseAgent.generate()` can return scripted responses without a live vLLM endpoint. The config already has `vllm_endpoint`; a mock endpoint or environment variable override is the recommended pattern.

Example approach (to be implemented):
```python
# If MOCK_LLM=true or endpoint is "mock://", return canned responses
# based on role_id and message content
```

## What NOT to Change

- **Research hypotheses** in `README.md` and `RESEARCH_QUESTIONS.md` — these define the experiment
- **Agent profile markdown files** in `team_config/` — cognitive patterns and seniority levels are the independent variables
- **Experiment configuration semantics** in `config.yaml` — values may change but the structure models the research design

## Code Conventions

- Python 3.11+, async-first (`asyncio`)
- Type hints on all function signatures
- Docstrings on all public functions and classes
- Format with `black`, lint with `ruff`, type-check with `mypy`
- Commit message prefix: `Add:`, `Fix:`, `Improve:`, `Docs:`, `Refactor:`

## Key Concepts

- **Sprint**: 20-minute wall-clock window simulating a 2-week development sprint
- **Pairing**: Dialogue-driven TDD sessions — driver/navigator roles, checkpoint exchanges every 25% of implementation
- **WIP limits**: 4 in-progress, 2 in-review (enforced by KanbanBoard)
- **Meta-learning**: After each retro, agent prompts evolve based on Keep/Drop/Puzzle analysis
- **Profile swapping**: Agents can swap roles under defined scenarios (`none` / `constrained` / `free`)
- **Disturbances**: Randomly injected failures (flaky tests, scope creep, incidents) at configured frequencies

## Agent Prompt Composition

Each agent prompt is layered:
1. `team_config/00_base/base_agent.md` — universal behavior
2. `team_config/01_role_archetypes/<role>.md` — developer/tester/leader traits
3. `team_config/02_individuals/<profile>.md` — individual personality and expertise
4. Runtime context — current sprint state, task, conversation history

## Infrastructure (Production)

- **vLLM** on Kubernetes GH200 nodes (3-tier by model size)
- **PostgreSQL** for shared state (kanban, pairing logs, meta-learnings)
- **Redis** for coordination (not yet implemented)
- **Prometheus** metrics on port 8080, Grafana dashboards
- Artifacts written to `outputs/<experiment-id>/sprint-<N>/`
