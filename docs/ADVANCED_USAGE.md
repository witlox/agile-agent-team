# Advanced Usage: Team of Teams

This guide covers multi-team orchestration and cross-team coordination -- running 2-7 autonomous agent teams under a single experiment with shared infrastructure, portfolio backlogs, coordinator agents, and agent borrowing.

## Table of Contents

1. [Overview](#1-overview)
2. [Multi-team configuration](#2-multi-team-configuration)
3. [Cross-team coordination](#3-cross-team-coordination)
4. [Agent borrowing](#4-agent-borrowing)
5. [Cross-team dependencies](#5-cross-team-dependencies)
6. [Coordinator agents](#6-coordinator-agents)
7. [Portfolio backlog distribution](#7-portfolio-backlog-distribution)
8. [Team-scoped infrastructure](#8-team-scoped-infrastructure)
9. [Running a multi-team experiment](#9-running-a-multi-team-experiment)
10. [Research applications](#10-research-applications)

---

## 1. Overview

Real organizations rarely operate as a single team. Products are built by multiple teams with overlapping concerns, shared dependencies, and the need for occasional cross-team collaboration. The "team of teams" model captures this reality.

### Architecture

```
                    ┌─────────────────────────────┐
                    │       Experiment Runner      │
                    │        (main.py)             │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   MultiTeamOrchestrator      │
                    │  ┌────────────────────────┐  │
                    │  │   CoordinationLoop     │  │
                    │  │  (staff eng + enabler) │  │
                    │  └────────────────────────┘  │
                    └──┬──────────────────────┬────┘
                       │                      │
          ┌────────────▼────────┐  ┌──────────▼──────────┐
          │  SprintManager (A)  │  │  SprintManager (B)  │
          │  ┌────────────────┐ │  │  ┌────────────────┐ │
          │  │ KanbanBoard(A) │ │  │  │ KanbanBoard(B) │ │
          │  └────────────────┘ │  │  └────────────────┘ │
          │  PO, Lead, Devs,   │  │  Lead, Devs,        │
          │  Testers            │  │  Testers             │
          └─────────────────────┘  └──────────────────────┘
                       │                      │
                  ┌────▼──────────────────────▼────┐
                  │     Shared Infrastructure      │
                  │  SharedContextDB  MessageBus   │
                  │  Prometheus       Portfolio BL  │
                  └────────────────────────────────┘
```

**Key properties:**

- Each team runs sprints **concurrently** via `asyncio.gather()`
- Teams have **isolated kanban boards** (scoped by `team_id`)
- Teams share a **single message bus** for cross-team communication
- Teams share a **single database** (queries scoped by `team_id`)
- **Coordinator agents** sit outside all teams and orchestrate between sprints
- Agents can be **temporarily borrowed** across team boundaries
- A **portfolio backlog** distributes stories to teams that lack their own

---

## 2. Multi-team configuration

Define teams in the `teams:` section of `config.yaml`. Each team needs an `id`, agent list, and optionally its own backlog, WIP limits, and Team Topology type.

### Minimal example

```yaml
teams:
  - id: "checkout-stream"
    name: "Checkout Stream Team"
    team_type: "stream_aligned"
    agents:
      - alex_senior_networking
      - marcus_mid_backend
      - sophie_senior_qa_lead
      - ahmed_senior_dev_lead
      - alex_senior_po

  - id: "platform-team"
    name: "Platform Team"
    team_type: "platform"
    agents:
      - priya_senior_devops
      - elena_mid_frontend
      - jordan_junior_backend
      - yuki_senior_tester_integration
```

### Constraints

| Rule | Limit |
|------|-------|
| Number of teams | 2-7 |
| Agent assignment | Each agent belongs to exactly one team |
| Agent IDs | Must exist in `models.agents` |

### Per-team options

```yaml
teams:
  - id: "checkout-stream"
    name: "Checkout Stream Team"
    team_type: "stream_aligned"   # stream_aligned | platform | enabling | complicated_subsystem
    agents: [...]
    backlog: "backlogs/checkout.yaml"   # Team-specific backlog (optional)
    wip_limits:                         # Override global WIP limits (optional)
      in_progress: 3
      review: 1
```

When a team has no `backlog:` path, it receives stories from the portfolio backlog via round-robin distribution.

---

## 2.5. Overhead budget (wallclock management)

When coordination is enabled, the overhead budget system timeboxes all coordination, distribution, and checkin steps so they don't consume unbounded experiment time.

### Configuration

```yaml
coordination:
  enabled: true
  coordinators: [staff_engineer_01, enablement_lead_01]
  overhead_budget:
    overhead_budget_pct: 0.20          # 20% of total sprint time
    iteration_zero_share: 0.40         # 40% of overhead for initial setup
    coordination_step_weight: 0.50     # Per-sprint step weights (must sum to 1.0)
    distribution_step_weight: 0.30
    checkin_step_weight: 0.20
    min_step_timeout_seconds: 10.0     # Floor for any step timeout
```

### Budget math

For 3 sprints x 60 min with 20% overhead:

| Component | Calculation | Result |
|-----------|-------------|--------|
| Total overhead | 3 x 60 x 0.20 | 36 min |
| Iteration 0 | 36 x 0.40 | 14.4 min |
| Per-sprint budget | 36 x 0.60 / 3 | 7.2 min |
| Coordination step | 7.2 x 0.50 | 3.6 min |
| Distribution step | 7.2 x 0.30 | 2.16 min |
| Checkin step | 7.2 x 0.20 | 1.44 min |

### Iteration 0

Before sprint 1, an iteration 0 step runs portfolio setup:
1. Coordinator orientation (best-effort LLM call with time context)
2. Full portfolio distribution across all teams

If iteration 0 times out, the system falls back to heuristic distribution (no LLM calls, instant).

### Deadline propagation

When a step has a deadline, coordinator agents receive a `## Time Context` section in their prompts:

```
## Time Context
- Remaining overhead budget: ~3.2 minutes
- Be concise. Focus on the most critical issues.
```

### Graceful fallbacks

| Step | On Timeout | Fallback |
|------|-----------|----------|
| Iteration 0 | `TimeoutError` | Heuristic distribution (no LLM) |
| Coordination loop | `TimeoutError` | Skip borrows, return None |
| Distribution | `TimeoutError` | Heuristic distribution (no LLM) |
| Mid-sprint checkin | `TimeoutError` | Skip, return message |

### Budget reporting

The final report includes an `overhead_budget` section:

```json
{
  "overhead_budget": {
    "total_budget_seconds": 2160.0,
    "spent_seconds": 45.3,
    "remaining_seconds": 2114.7,
    "num_steps": 6,
    "timeouts": 0,
    "steps": [
      {"step": "coordination", "sprint": 1, "elapsed": 12.5, "timed_out": false},
      {"step": "distribution", "sprint": 1, "elapsed": 8.2, "timed_out": false}
    ]
  }
}
```

---

## 3. Cross-team coordination

The coordination system adds intelligent cross-team awareness through a `CoordinationLoop` that runs at two cadences:

- **Full loop** (between sprints): Evaluate team health, detect dependencies, recommend borrows
- **Mid-sprint checkin** (between development and QA): Lightweight health check

### Enable coordination

```yaml
coordination:
  enabled: true
  full_loop_cadence: 1          # Run full loop every N sprints
  mid_sprint_checkin: true      # Lightweight check between dev and QA
  max_borrows_per_sprint: 2     # Cap on agent borrows per sprint
  borrow_duration_sprints: 1    # How long a borrowed agent stays
  dependency_tracking: true     # Scan cards for cross-team dependencies
  coordinators:
    - staff_engineer_01         # Must exist in models.agents
    - enablement_lead_01        # Must NOT be assigned to any team
```

### Configuration reference

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Master switch for coordination |
| `full_loop_cadence` | `1` | Full coordination loop runs every N sprints (starting from sprint 2) |
| `mid_sprint_checkin` | `true` | Enable lightweight checkin between development and QA phases |
| `max_borrows_per_sprint` | `2` | Maximum agent borrows the coordination loop can execute per sprint |
| `borrow_duration_sprints` | `1` | Borrowed agents return home after N sprints |
| `dependency_tracking` | `true` | Scan kanban cards for `depends_on_team` metadata |
| `coordinators` | `[]` | Agent IDs that serve as coordinators (must not be in any team) |
| `overhead_budget.overhead_budget_pct` | `0.20` | Fraction of total sprint time allocated to overhead |
| `overhead_budget.iteration_zero_share` | `0.40` | Fraction of overhead budget for iteration 0 setup |
| `overhead_budget.min_step_timeout_seconds` | `10.0` | Minimum timeout floor for any step |

### Full loop flow

The full coordination loop runs between sprints (starting from sprint 2) and follows this sequence:

```
1. Return borrowed agents     ← agents from previous sprint go home
2. Gather team health         ← WIP counts, blocked cards, velocity
3. Detect dependencies        ← scan card metadata for cross-team refs
4. Evaluate (coordinator 1)   ← staff engineer analyzes cross-team state
5. Plan (coordinator 2)       ← enablement lead recommends actions
6. Execute borrows            ← move agents between teams
7. Broadcast outcome          ← publish to "coordination" message bus channel
```

### Mid-sprint checkin

A lightweight check that runs between the development and QA phases of each sprint. It queries WIP and blocked counts per team and asks the staff engineer coordinator for urgent recommendations. No borrows happen mid-sprint -- it is observation only.

### Disabling coordination

To run multi-team without coordination (teams operate independently):

```yaml
coordination:
  enabled: false
```

Or simply omit the `coordination:` section entirely.

---

## 4. Agent borrowing

Borrowing temporarily moves an agent from one team to another. It models real-world scenarios where a team with spare capacity helps a struggling team, or where a specialist is needed across team boundaries.

### How it works

1. The coordination loop identifies a team that is struggling (high blocked count, low velocity) and another with slack.
2. The enablement lead coordinator recommends a borrow in `BORROW: <agent_id> from <team> to <team> because <reason>` format.
3. `MultiTeamOrchestrator.borrow_agent()` moves the agent:
   - Sets `agent.config.original_team_id` to track the home team
   - Updates `agent.config.team_id` to the target team
   - Moves the agent between team agent lists and SprintManager agent lists
4. At the start of the next sprint, `return_borrowed_agents()` moves all borrowed agents back home and clears `original_team_id`.

### Constraints

| Rule | Enforcement |
|------|-------------|
| Max borrows per sprint | `coordination.max_borrows_per_sprint` (default 2) |
| Borrow duration | `coordination.borrow_duration_sprints` (default 1) |
| Agent must exist in source team | Returns `False` if not found |
| Target team must exist | Returns `False` if not found |
| Home team tracking | `original_team_id` set on first borrow, cleared on return |

### Manual borrowing (programmatic)

```python
from src.orchestrator.coordination_loop import BorrowRequest

request = BorrowRequest(
    from_team="platform-team",
    to_team="checkout-stream",
    agent_id="priya_senior_devops",
    reason="checkout team needs DevOps help for deployment pipeline",
    duration_sprints=1,
)
success = await orchestrator.borrow_agent(request)
```

---

## 5. Cross-team dependencies

Dependencies between teams are tracked through kanban card metadata. When a card on one team's board depends on work from another team, the metadata signals this to the coordination loop.

### Convention

Cards with cross-team dependencies store the following in their `metadata` JSONB field:

```json
{
  "depends_on_team": "platform-team",
  "dependency_type": "needs_api",
  "dependency_status": "open"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `depends_on_team` | Any team ID | Which team this card depends on |
| `dependency_type` | `blocks`, `needs_api`, `shared_component` | Nature of the dependency |
| `dependency_status` | `open`, `resolved` | Current state |

### Detection

The `CoordinationLoop._detect_dependencies()` method scans all cards via `SharedContextDB.get_cards_with_dependency()` and builds a list of `CrossTeamDependency` objects. These are fed to the coordinator agents during the evaluation phase.

### Example

Team Alpha is building a checkout flow that needs an API from Team Beta's platform:

```python
await kanban.add_card({
    "title": "Integrate payment gateway",
    "status": "in_progress",
    "team_id": "checkout-stream",
    "metadata": {
        "depends_on_team": "platform-team",
        "dependency_type": "needs_api",
        "dependency_status": "open",
    },
})
```

During the next coordination loop, the staff engineer coordinator will see this dependency and may recommend that Team Beta prioritize the API, or that a DevOps agent be borrowed to help.

---

## 6. Coordinator agents

Coordinators are agents that sit outside all teams. They observe cross-team health and make recommendations. The system supports two coordinator archetypes:

### Staff Engineer (evaluator)

**Role archetype:** `staff_engineer` (defined in `team_config/01_role_archetypes/staff_engineer.md`)

**Personality:** `coordinator_staff_engineer` (in `team_config/05_individuals/`)

**Responsibilities:**
- Analyze team health snapshots (velocity, WIP, blocked counts)
- Identify struggling teams and blocking dependencies
- Provide structured evaluation during full coordination loops
- Run lightweight health checks during mid-sprint checkins

**Behavioral traits:**
- Data-driven: leads with metrics, follows with interpretation
- Systems thinker: sees teams as interconnected systems
- Prefers small, reversible interventions over big reorganizations

### Enablement Lead (planner)

**Role archetype:** `enablement_lead` (defined in `team_config/01_role_archetypes/enablement_lead.md`)

**Personality:** `coordinator_enablement_lead` (in `team_config/05_individuals/`)

**Responsibilities:**
- Translate the staff engineer's evaluation into concrete actions
- Recommend agent borrows with structured `BORROW:` directives
- Provide general `RECOMMEND:` directives for process improvements

**Behavioral traits:**
- Empathetic and action-oriented
- Focuses on removing impediments rather than optimizing throughput
- Tracks "borrow debt" -- teams that have lent agents deserve priority when they need help

### Defining coordinators in config

```yaml
models:
  agents:
    # Regular team agents...
    alex_senior_networking:
      name: "Alex Chen (Senior Networking)"
      # ...

    # Coordinators (NOT in any team's agents: list)
    staff_engineer_01:
      name: "Staff Engineer Coordinator"
      individual: coordinator_staff_engineer
      seniority: senior
      primary_specialization: backend
      role_archetype: staff_engineer
      demographics:
        pronouns: "they/them"

    enablement_lead_01:
      name: "Enablement Lead Coordinator"
      individual: coordinator_enablement_lead
      seniority: senior
      primary_specialization: backend
      role_archetype: enablement_lead
      demographics:
        pronouns: "they/them"

coordination:
  enabled: true
  coordinators:
    - staff_engineer_01
    - enablement_lead_01
```

### Validation rules

- Coordinator agent IDs must exist in `models.agents`
- Coordinators must **not** appear in any team's `agents:` list
- Violations raise `ValueError` at config load time

---

## 7. Portfolio backlog distribution

When running multiple teams, you can use a single **portfolio backlog** that gets distributed across teams, or give each team its own backlog.

### Portfolio mode (shared backlog)

All teams without a team-specific `backlog:` path receive stories from the main `--backlog` file. Stories are distributed via round-robin before each sprint.

```
Portfolio Backlog (6 stories)
    │
    ├── Team Alpha (no own backlog) → US-001, US-003, US-005
    └── Team Beta  (no own backlog) → US-002, US-004, US-006
```

**Default allocation:** 3 stories per team per sprint.

### Team-specific backlogs

Teams with a `backlog:` path use their own backlog exclusively and are excluded from portfolio distribution.

```yaml
teams:
  - id: "checkout-stream"
    backlog: "backlogs/checkout.yaml"  # Uses own backlog
    agents: [...]

  - id: "platform-team"
    # No backlog: path → receives portfolio stories
    agents: [...]
```

### Mixed mode

You can combine both approaches: some teams with dedicated backlogs, others drawing from the portfolio.

---

## 8. Team-scoped infrastructure

Multi-team mode shares infrastructure but scopes queries by team.

### Kanban boards

Each team gets a `KanbanBoard` instance with `team_id` set. Cards added by Team Alpha are invisible to Team Beta's board queries.

```python
# Team Alpha's kanban only sees its own cards
alpha_snapshot = await alpha_manager.kanban.get_snapshot()

# Team Beta's kanban only sees its own cards
beta_snapshot = await beta_manager.kanban.get_snapshot()
```

### Database queries

`SharedContextDB` methods that accept `team_id` filter results accordingly:
- `get_cards_by_status_for_team(status, team_id)`
- `get_wip_count_for_team(status, team_id)`

### Message bus

All teams share a single `MessageBus`. Channels are created per team (`team:<team_id>`) plus a `portfolio` channel for cross-team messages and a `coordination` channel when coordination is enabled.

```
Channels:
  team:checkout-stream  → checkout team agents
  team:platform-team    → platform team agents
  portfolio             → all agents
  coordination          → all agents + coordinators
```

### Prometheus metrics

Sprint metrics are labeled with `team_id` so Grafana dashboards can filter by team:

```
sprint_velocity{team_id="checkout-stream"} 8
sprint_velocity{team_id="platform-team"} 5
```

### Output directories

Each team gets a subdirectory under the experiment output:

```
/tmp/multi-team-test/
├── checkout-stream/
│   ├── sprint-01/
│   │   ├── kanban.json
│   │   ├── pairing_log.json
│   │   └── retro.md
│   └── final_report.json
├── platform-team/
│   ├── sprint-01/
│   │   └── ...
│   └── final_report.json
└── final_report.json          ← Portfolio-level aggregation
```

---

## 9. Running a multi-team experiment

### Quick start (mock mode)

```bash
MOCK_LLM=true python -m src.orchestrator.main \
  --config examples/06-multi-team/config.yaml \
  --backlog examples/06-multi-team/backlog.yaml \
  --sprints 3 \
  --output /tmp/multi-team-test \
  --db-url mock://
```

Expected output:

```
Loaded 13 agents:
  - alex_senior_networking: Alex Chen (Senior Networking)
  - ...
  - staff_engineer_01: Staff Engineer Coordinator
  - enablement_lead_01: Enablement Lead Coordinator

Multi-team mode: 2 teams
  - checkout-stream: Checkout Stream Team (6 agents)
  - platform-team: Platform Team (5 agents)
  Coordinators: ['staff_engineer_01', 'enablement_lead_01']

============================================================
SPRINT 1  [14:05:11]
============================================================
  [checkout-stream] velocity=5pts done=2
  [platform-team] velocity=3pts done=1

============================================================
SPRINT 2  [14:06:23]
============================================================
  Running cross-team coordination loop...
  [COORD] Continue monitoring team health.
  [checkout-stream] velocity=8pts done=3
  [platform-team] velocity=5pts done=2

...
Portfolio report: /tmp/multi-team-test/final_report.json
```

### Portfolio report

The final report includes per-team breakdown and portfolio aggregation:

```json
{
  "experiment": "multi-team-demo",
  "mode": "multi_team",
  "teams": {
    "checkout-stream": {
      "total_sprints": 3,
      "avg_velocity": 7.0,
      "total_features": 8
    },
    "platform-team": {
      "total_sprints": 3,
      "avg_velocity": 4.3,
      "total_features": 5
    }
  },
  "portfolio": {
    "total_sprints": 3,
    "total_velocity": 34,
    "total_features": 13,
    "num_teams": 2
  },
  "overhead_budget": {
    "total_budget_seconds": 2160.0,
    "spent_seconds": 45.3,
    "remaining_seconds": 2114.7,
    "num_steps": 6,
    "timeouts": 0,
    "steps": [...]
  }
}
```

### Combining with other features

Multi-team mode composes with all existing features:

| Feature | Supported | Notes |
|---------|-----------|-------|
| Disturbances | Yes | Fire independently per team |
| Profile swapping | Yes | Swaps happen within each team |
| Stakeholder review | Yes | Portfolio-level review delegated to first team's manager |
| Meta-learning | Yes | Per-agent, independent of team assignment |
| Remote git | Yes | Each team pushes to same or different repos |
| Sprint zero | Yes | Runs per team |
| Specialist consultants | Yes | Per team |

---

## 10. Research applications

The team-of-teams model enables studying dynamics that single-team experiments cannot capture.

### Research questions addressable

| Question | How to measure |
|----------|---------------|
| Does cross-team coordination improve total portfolio velocity? | Compare `coordination.enabled: true` vs `false` across identical team setups |
| What is the cost of agent borrowing (context-switch overhead)? | Track velocity of lending team vs receiving team in sprints with borrows |
| Do stream-aligned teams outperform platform teams? | Compare metrics across `team_type` values |
| How do cross-team dependencies affect delivery? | Correlate `depends_on_team` card counts with blocked-card duration |
| Is coordinator-driven borrowing better than no coordination? | A/B experiment: same teams, with and without coordinators |
| How does team size affect velocity per capita? | Vary team sizes across experiments |

### Recommended experiment variants

| Variant | Configuration | Purpose |
|---------|---------------|---------|
| Independent teams | `coordination.enabled: false` | Baseline: teams work in isolation |
| Coordinated teams | `coordination.enabled: true`, 2 coordinators | Full coordination with borrowing |
| High dependency | Add `depends_on_team` metadata to stories | Stress-test dependency resolution |
| Aggressive borrowing | `max_borrows_per_sprint: 4` | Measure disruption vs benefit |
| Observer only | `max_borrows_per_sprint: 0`, `mid_sprint_checkin: true` | Coordination observes but cannot act |

### Suggested experiment sequence

1. **Baseline (independent):** 2 teams, no coordination, 10 sprints
2. **Coordination (observation only):** Same teams, coordination enabled, `max_borrows_per_sprint: 0`
3. **Coordination (active):** Same teams, full coordination with borrowing
4. **Stress test:** Add cross-team dependencies, increase borrow limits
5. **Scale test:** 4-7 teams with portfolio backlog, measure coordination overhead

Compare `final_report.json` across variants to measure coordination impact on velocity, blocked-card counts, and feature throughput.

---

**See also:** [USAGE.md](USAGE.md) for single-team configuration, [ARCHITECTURE.md](ARCHITECTURE.md) for system design, [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md) for the full research framework.
