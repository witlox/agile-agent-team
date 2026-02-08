# Usage Guide

This guide covers everything you need to run the experiment locally (mock mode) or against a live vLLM cluster, and how to interpret the outputs.

## Table of Contents

1. [Quick start (local / mock mode)](#1-quick-start-local--mock-mode)
2. [Configuration reference](#2-configuration-reference)
3. [Disturbance injection](#3-disturbance-injection)
4. [Profile swapping](#4-profile-swapping)
5. [Simulated test coverage](#5-simulated-test-coverage)
6. [Sprint artifacts](#6-sprint-artifacts)
7. [Prometheus metrics](#7-prometheus-metrics)
8. [Running against a live vLLM endpoint](#8-running-against-a-live-vllm-endpoint)

---

## 1. Quick start (local / mock mode)

No Kubernetes, no GPU, no database required.

```bash
# Clone and set up
git clone https://github.com/witlox/agile-agent-team
cd agile-agent-team

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

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
  [DISTURBANCE] flaky_test
  [DISTURBANCE] junior_misunderstanding
  Development...
  QA review...
  Retrospective...
  Meta-learning...
  Artifacts...
  velocity=5pts  done=2  sessions=3
...
Experiment complete. Output: /tmp/my-first-run
```

### Mock mode activation

Mock mode is triggered by **either**:

| Method | Value |
|--------|-------|
| Environment variable | `MOCK_LLM=true` |
| vLLM endpoint in config | `mock://` |
| `--db-url` CLI flag | `mock://` |

In mock mode agents return canned responses keyed on `role_id`, and an in-memory store replaces PostgreSQL.

### Running the tests

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/qualification/
pytest          # all tests
```

---

## 2. Configuration reference

All experiment parameters live in `config.yaml`. The CLI only exposes:

| Flag | Default | Purpose |
|------|---------|---------|
| `--config` | `config.yaml` | Path to config file |
| `--sprints` | `10` | Number of sprints to run |
| `--output` | `outputs/experiment` | Output directory |
| `--backlog` | `backlog.yaml` | Product backlog YAML |
| `--db-url` | _(from config)_ | Override database URL |

Everything else — disturbances, profile swapping, WIP limits, model endpoints — is set in `config.yaml`.

### Key config sections

```yaml
experiment:
  name: "my-experiment"
  sprint_duration_minutes: 20        # wall-clock time per sprint
  sprints_per_stakeholder_review: 5  # PO review cadence

team:
  wip_limits:
    in_progress: 4
    review: 2

disturbances:
  enabled: true                      # set false to disable entirely
  frequencies:
    dependency_breaks: 0.166         # probability per sprint (1 in ~6)
    production_incident: 0.125       # 1 in ~8
    flaky_test: 0.25                 # 1 in 4
    scope_creep: 0.20                # 1 in 5
    junior_misunderstanding: 0.33    # 1 in 3
    architectural_debt_surfaces: 0.166
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

models:
  vllm_endpoint: "http://vllm-gh200-module-1:8000"
```

---

## 3. Disturbance injection

Disturbances are controlled-chaos events that fire probabilistically each sprint. They model realistic team stress: production fires, confused juniors, unplanned scope.

### How it works

After sprint planning, `DisturbanceEngine.roll_for_sprint()` runs a Bernoulli trial for each configured disturbance type. Those that fire are applied **before** development begins.

### Disturbance types

| Type | Effect |
|------|--------|
| `dependency_breaks` | A random in-progress card is tagged `[BLOCKED: dependency unavailable]` |
| `production_incident` | A `HOTFIX` card is injected into the backlog; all agents receive an `[INCIDENT ALERT]` system message |
| `flaky_test` | A random review/in-progress card is tagged `[FLAKY TESTS: intermittent failures detected]` |
| `scope_creep` | A new unplanned card is added to the sprint; the PO agent receives a scope-change notice |
| `junior_misunderstanding` | A random junior agent receives a `[CONFUSION]` system message prompting re-reading |
| `architectural_debt_surfaces` | A random in-progress card is tagged `[TECH DEBT: refactoring required]` |

### Blast radius controls

If too many disturbances fire at once and velocity or coverage would drop beyond the configured thresholds, the engine caps further injections. Thresholds are set in `blast_radius_controls`.

### Logged events

Every disturbance is written to the `disturbance_events` table (or in-memory store in mock mode) and appears in `final_report.json` under each sprint's `"disturbances"` list:

```json
{
  "sprint": 1,
  "velocity": 5,
  "test_coverage": 89.0,
  "disturbances": ["dependency_breaks", "junior_misunderstanding"]
}
```

### Disabling disturbances

```yaml
disturbances:
  enabled: false
```

---

## 4. Profile swapping

Profile swapping lets agents temporarily work outside their specialisation. It models cross-training, production incidents pulling specialists away, and organisational resilience.

### Modes

| Mode | Behaviour |
|------|-----------|
| `none` | Agents never swap. Bottlenecks surface as knowledge silos. |
| `constrained` | Swaps only when an `allowed_scenario` triggers (e.g. `production_incident`). Penalties applied. |
| `free` | Any agent may cover any domain. No penalty. AI-optimal baseline. |

### What happens during a swap

1. A `production_incident` disturbance fires.
2. `SprintManager._check_swap_triggers()` finds the senior DevOps or networking agent.
3. `agent.swap_to(domain, proficiency)` is called, which appends a notice to the agent's system prompt:

```
[PROFILE SWAP ACTIVE]
You are temporarily covering production incident response tasks. Proficiency: 70%.
You are less familiar with this domain — ask more questions, verify assumptions,
and expect to work 20% slower than your usual pace.
```

4. If the swapped agent is involved in a pairing session, an extra checkpoint round is added (simulating the 20% slowdown).
5. After the sprint ends, `decay_swap()` reduces proficiency or reverts the swap if `knowledge_decay_sprints` have elapsed.

### Checking swap state

The `BaseAgent.is_swapped` property returns `True` while a swap is active. Swap state is visible in `agent._swap_state`:

```python
{
  "role_id": "incident_responder",
  "domain": "production incident response",
  "proficiency": 0.70,
  "sprint": 3,
}
```

---

## 5. Simulated test coverage

Test coverage is a **process-based simulation** — it measures how thoroughly the TDD pairing protocol was followed, not actual code coverage.

### Formula

```
base_coverage = 70.0        # floor if no TDD checkpoints
per_checkpoint = 3.5        # each completed checkpoint adds coverage
consensus_bonus = 5.0       # both agents approve → bonus
max_coverage = 95.0

session_coverage = min(base + checkpoints_completed * per_checkpoint + bonus, max)
```

With the default 4-checkpoint protocol and consensus:
- Coverage per session ≈ 70 + 4×3.5 + 5 = **89%**

If an agent is swapped in (extra checkpoint from 20% slowdown):
- 5 checkpoints → 70 + 5×3.5 + 5 = **92.5%** (more careful review)

### Sprint-level aggregation

Sprint coverage = story-point-weighted average across all completed pairing sessions:

```
sprint_coverage = Σ(session_coverage × story_points) / Σ(story_points)
```

This appears in `final_report.json` as `test_coverage` and is exported to the `test_coverage_percent` Prometheus gauge.

---

## 6. Sprint artifacts

Each sprint writes to `<output>/sprint-NN/`:

| File | Contents |
|------|----------|
| `kanban.json` | Full board snapshot: `ready`, `in_progress`, `review`, `done` |
| `pairing_log.json` | All pairing session records for the sprint |
| `retro.md` | Keep / Drop / Puzzle retrospective notes |

The experiment-level `final_report.json` contains:

```json
{
  "experiment": "baseline-experiment",
  "total_sprints": 10,
  "avg_velocity": 5.0,
  "total_features": 20,
  "sprints": [
    {
      "sprint": 1,
      "velocity": 5,
      "features_completed": 2,
      "test_coverage": 89.0,
      "pairing_sessions": 3,
      "cycle_time_avg": 0.00012,
      "disturbances": ["flaky_test"]
    },
    ...
  ]
}
```

### Reading pairing session details

Each entry in `pairing_log.json`:

```json
{
  "sprint": 1,
  "driver_id": "dev_mid_backend",
  "navigator_id": "dev_jr_fullstack_a",
  "task_id": 3,
  "start_time": "2026-02-08T14:05:11.123456",
  "end_time": "2026-02-08T14:05:11.234567",
  "outcome": "completed",
  "coverage_estimate": 89.0,
  "decisions": {
    "approach": "...",
    "implementation": "..."
  }
}
```

---

## 7. Prometheus metrics

The metrics server starts automatically on port 8080 when the experiment runs.

| Metric | Type | Description |
|--------|------|-------------|
| `sprint_velocity` | Gauge | Story points completed last sprint |
| `test_coverage_percent` | Gauge | Weighted coverage estimate last sprint |
| `pairing_sessions_total` | Counter | Cumulative sessions, labelled `driver`/`navigator` |
| `consensus_seconds` | Histogram | Time-to-consensus distribution |

These are updated via `update_sprint_metrics()` after each sprint completes.

Access raw metrics:

```bash
curl http://localhost:8080/metrics
```

---

## 8. Running against a live vLLM endpoint

```bash
# Edit config.yaml first:
#   models.vllm_endpoint: "http://YOUR_HOST:8000"
#   database.url: "postgresql://user:pass@host:5432/team_context"

python -m src.orchestrator.main \
  --config config.yaml \
  --sprints 20 \
  --output outputs/live-run-001
```

### Experiment variants

| Goal | Config change |
|------|--------------|
| No disturbances (pure team dynamics) | `disturbances.enabled: false` |
| No profile swapping (stable roles) | `profile_swapping.mode: none` |
| Free swapping (AI-optimal baseline) | `profile_swapping.mode: free` |
| High disturbance rate (stress test) | Increase all `frequencies` values |
| Shorter sprints (rapid iteration) | `sprint_duration_minutes: 10` |

### Recommended experiment sequence

1. **Baseline**: `disturbances: false`, `swap: none` → 10 sprints
2. **Disturbances only**: `disturbances: true`, `swap: none` → 10 sprints
3. **Full chaos**: `disturbances: true`, `swap: constrained` → 20 sprints
4. **AI-optimal**: `disturbances: true`, `swap: free` → 20 sprints

Compare `final_report.json` across runs to measure resilience and learning curves.
