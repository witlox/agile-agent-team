# Advanced Usage

This guide covers advanced features for tuning experiments — disturbance injection, specialist consultants, profile swapping, team culture, metrics — as well as multi-team orchestration and cross-team coordination.

## Table of Contents

1. [Disturbance injection](#1-disturbance-injection)
2. [Specialist consultant system](#2-specialist-consultant-system)
3. [Profile swapping](#3-profile-swapping)
4. [Team culture features](#4-team-culture-features)
5. [Test coverage (Hybrid: Real + Process)](#5-test-coverage-hybrid-real--process)
6. [Sprint artifacts](#6-sprint-artifacts)
7. [Prometheus metrics](#7-prometheus-metrics)
8. [Experiment variants](#8-experiment-variants)
9. [Multi-team overview](#9-multi-team-overview)
10. [Multi-team configuration](#10-multi-team-configuration)
11. [Overhead budget (wallclock management)](#11-overhead-budget-wallclock-management)
12. [Cross-team coordination](#12-cross-team-coordination)
13. [Agent borrowing](#13-agent-borrowing)
14. [Cross-team dependencies](#14-cross-team-dependencies)
15. [Coordinator agents](#15-coordinator-agents)
16. [Portfolio backlog distribution](#16-portfolio-backlog-distribution)
17. [Team-scoped infrastructure](#17-team-scoped-infrastructure)
18. [Running a multi-team experiment](#18-running-a-multi-team-experiment)
19. [Research applications](#19-research-applications)

---

## 1. Disturbance injection

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

## 2. Specialist consultant system

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

### Available specialist domains (37)

The system ships with curated specialist profiles in `team_config/08_specialists/`. Each profile includes expertise areas, consultation approach, common scenarios, and knowledge transfer focus.

| Category | Domains |
|----------|---------|
| **Core** | `ml`, `security`, `performance`, `cloud`, `architecture`, `database`, `frontend`, `distributed`, `data`, `mobile` |
| **Infrastructure** | `backend`, `devops`, `networking`, `embedded`, `systems`, `observability`, `sre`, `platform`, `admin` |
| **Development** | `api_design`, `ui_ux`, `test_automation`, `quality`, `accessibility`, `blockchain`, `event_driven`, `search`, `i18n`, `business_processes`, `iam`, `mlops`, `data_science` |
| **Language** | `python`, `golang`, `rust`, `typescript`, `cpp` |

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

## 3. Profile swapping

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

## 4. Team culture features

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

**Documented in** `team_config/06_process_rules/git_workflow.md`

- **Stable main**: Always deployable, always green, always tested
- **Feature branches**: Created automatically per story (`feature/<story-id>`)
- **Merge conflict resolution**: Expected, protocol documented
- **"You break it, you fix it"**: Build ownership with team support
- **Blameless post-mortems**: "We fix systems, not people"

### Hiring Protocol

**Documented in** `team_config/06_process_rules/hiring_protocol.md`

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

## 5. Test coverage (Hybrid: Real + Process)

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

## 6. Sprint artifacts

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

## 7. Prometheus metrics

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

## 8. Experiment variants

### Configuration variants

| Goal | Config change |
|------|--------------|
| No disturbances (pure team dynamics) | `disturbances.enabled: false` |
| No profile swapping (stable roles) | `profile_swapping.mode: none` |
| Free swapping (AI-optimal baseline) | `profile_swapping.mode: free` |
| High disturbance rate (stress test) | Increase all `frequencies` values |
| Shorter sprints (rapid iteration) | `sprint_duration_minutes: 10` |
| Turnover simulation (long experiments) | `team.turnover.enabled: true` |
| More tester participation | `team.tester_pairing.frequency: 0.40` |

### Example configurations

The `examples/` directory contains 6 ready-to-use config+backlog pairs:

| Example | Team | Runtime | Language | Key Feature |
|---------|------|---------|----------|-------------|
| `01-startup-mvp/` | 5 agents | Anthropic | Python | Small team, no disturbances, 45-min sprints |
| `02-enterprise-brownfield/` | 11 agents | vLLM | Go+Python | Brownfield, GitHub PRs, full disturbances |
| `03-oss-rust-library/` | 7 agents | Hybrid | Rust | Seniors on Anthropic, juniors on vLLM, GitLab MRs |
| `04-chaos-experiment/` | 11 agents | Both | Python+TS | Max disturbances, free swapping, 20 sprints |
| `05-quick-demo/` | 3 agents | Mock | Python | Minimal setup, 15-min sprints, 3 stories |
| `06-multi-team/` | 13 agents | Mock | Python | 2 teams, cross-team coordination, overhead budget |

```bash
# Try the quick demo (no API keys needed)
MOCK_LLM=true python -m src.orchestrator.main \
  --config examples/05-quick-demo/config.yaml \
  --backlog examples/05-quick-demo/backlog.yaml \
  --sprints 2 \
  --duration 15 \
  --output /tmp/quick-demo \
  --db-url mock://
```

### Continuing experiments

If an experiment finishes and you want more data, use `--continue N` instead of re-running from scratch:

```bash
# Initial 10-sprint experiment
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 10 \
  --output /tmp/baseline \
  --db-url mock://

# Add 10 more sprints (starts at sprint 11)
MOCK_LLM=true python -m src.orchestrator.main \
  --continue 10 \
  --output /tmp/baseline \
  --db-url mock://
```

The resume logic restores backlog progress and sprint results from the output directory's `final_report.json` and `kanban.json` snapshots. The final report is rewritten to include both old and new sprint results. Works for both single-team and multi-team modes.

### Recommended experiment sequence

1. **Baseline**: `disturbances: false`, `swap: none` → 10 sprints
2. **Disturbances only**: `disturbances: true`, `swap: none` → 10 sprints
3. **Full chaos**: `disturbances: true`, `swap: constrained` → 20 sprints
4. **AI-optimal**: `disturbances: true`, `swap: free` → 20 sprints
5. **Long-term**: Enable turnover, run 30+ sprints (use `--continue` to extend)

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
cat team_config/07_meta/meta_learnings.jsonl | jq 'select(.agent_id == "alex_senior_networking")'
```

---

## 9. Multi-team overview

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

## 10. Multi-team configuration

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

## 11. Overhead budget (wallclock management)

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

## 12. Cross-team coordination

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

## 13. Agent borrowing

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

## 14. Cross-team dependencies

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

## 15. Coordinator agents

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

## 16. Portfolio backlog distribution

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

## 17. Team-scoped infrastructure

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

## 18. Running a multi-team experiment

### Quick start (mock mode)

```bash
MOCK_LLM=true python -m src.orchestrator.main \
  --config examples/06-multi-team/config.yaml \
  --backlog examples/06-multi-team/backlog.yaml \
  --sprints 3 \
  --output /tmp/multi-team-test \
  --db-url mock://

# Continue the multi-team experiment for 2 more sprints
MOCK_LLM=true python -m src.orchestrator.main \
  --config examples/06-multi-team/config.yaml \
  --backlog examples/06-multi-team/backlog.yaml \
  --continue 2 \
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

## 19. Research applications

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

**See also:** [USAGE.md](USAGE.md) for core configuration, [ARCHITECTURE.md](ARCHITECTURE.md) for system design, [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md) for the full research framework.
