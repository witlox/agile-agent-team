# System Architecture

## Overview

The Agile Agent Team experiment is a multi-agent system that simulates a mature software development team. Unlike agent swarms that focus on task distribution, this system models a **cohesive team** with stable roles, realistic constraints, and emergent dynamics.

## Core Hypothesis

**"A mature single team can build anything, given the right practices and structure."**

This experiment tests whether:
1. AI agents can form effective collaborative teams
2. Team maturity affects productivity (velocity increases over time)
3. Process constraints (pairing, WIP limits) improve outcomes
4. Realistic team dynamics emerge from proper modeling

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Sprint Orchestrator                      │
│  - 20-minute wall-clock = 2-week simulated sprint           │
│  - Manages planning → development → retrospective           │
│  - Enforces process rules (pairing, WIP limits, DoD)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├──────────────────────────┐
                              ↓                          ↓
┌─────────────────────────────────────┐    ┌─────────────────────────┐
│        Shared Context Layer          │    │    Model Serving        │
│  - PostgreSQL (team state)           │    │  - vLLM on GH200        │
│  - Redis (coordination)              │    │  - Multi-model support  │
│  - Kanban board                      │    │  - Continuous batching  │
│  - Pairing sessions log              │    └─────────────────────────┘
│  - Meta-learnings                    │
└─────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│  Leadership  │    │  Developers  │      │   Testers    │
│  (3 agents)  │    │  (6 agents)  │      │  (2 agents)  │
│              │    │              │      │              │
│ - Dev Lead   │    │ - 2 Senior   │      │ - Integration│
│ - QA Lead    │    │ - 2 Mid      │      │ - E2E        │
│ - PO         │    │ - 2 Junior   │      │              │
└──────────────┘    └──────────────┘      └──────────────┘
```

## Component Deep Dive

### 1. Sprint Orchestrator

**Responsibilities:**
- Time management (20 minutes wall-clock → 2 weeks simulated)
- Phase coordination (planning → dev → retro)
- Process enforcement (pairing protocol, WIP limits)
- Artifact generation (Kanban snapshots, logs, reports)

**Key Files:**
- `src/orchestrator/main.py` - Entry point
- `src/orchestrator/sprint_manager.py` - Sprint lifecycle
- `src/orchestrator/config.py` - Configuration loader

**Sprint Phases:**

```python
Phase 1: Planning (pre-sprint, not in 20min)
  - PO presents prioritized backlog
  - Team estimates stories
  - Decompose into tasks
  - Assign pairs to initial tasks

Phase 2: Development (20 minutes wall-clock)
  - Continuous pairing on tasks
  - TDD cycles with checkpoints
  - Design dialogues throughout
  - Progress tracked in Kanban

Phase 3: Retrospective (post-sprint)
  - Keep/Drop/Puzzle format
  - Meta-learnings extracted
  - Agent prompts updated
  - Next sprint improvements

Phase 4: Artifact Generation
  - Kanban snapshot (JSON)
  - Pairing log (JSONL)
  - Retro notes (Markdown)
  - Coverage report (JSON)
  - Meta-learning diff (Markdown)
```

### 2. Pairing Engine

**The Core Innovation: Dialogue-Driven Pairing**

Unlike typical multi-agent systems where agents work independently, this system models **continuous design dialogue** during implementation.

```python
Traditional Multi-Agent:
  Agent1: Write code
  Agent2: Review code
  Result: Sequential handoff, no real collaboration

This System (Dialogue-Driven):
  Agent1: "I'm thinking we cache at service layer..."
  Agent2: "What about different TTLs per endpoint?"
  Agent1: "Good point. Cache-aside pattern instead?"
  Agent2: "Adds boilerplate. Worth it for one use case?"
  Agent1: "Let's start simple, refactor if needed."
  Agent2: "Agreed. Document the trade-off."
  Result: Design decisions made collaboratively
```

**Pairing Protocol:**

```
1. Sync (1-2 min wall-clock)
   - Both agents read Kanban card
   - Each proposes approach
   - Identify decision points
   
2. Design Dialogue (1-2 min)
   - 3-5 message exchanges
   - Explore trade-offs
   - Reach consensus on approach
   
3. TDD Cycles (12-15 min)
   Loop:
     - Navigator writes ONE failing test (30s)
     - Driver implements simplest solution (1-2 min)
     - CHECKPOINT DIALOGUE (30s)
       * "Is this on track?"
       * "Next decision point?"
       * "Any red flags?"
     - Refactor if needed (collaborative, 1 min)
   Until feature complete
   
4. Consensus (30s)
   - Both agents explicitly approve
   - If disagreement, escalate to lead
```

**Key Files:**
- `src/agents/pairing.py` - Pairing engine
- `team_config/03_process_rules/pairing_protocol.md` - Protocol spec

### 3. Agent System

**Agent Types:**

| Role | Count | Model | Specialization |
|------|-------|-------|----------------|
| Dev Lead | 1 | Qwen2.5-Coder-32B | Architecture, coordination |
| QA Lead | 1 | Qwen2.5-72B | Quality gates, test strategy |
| Product Owner | 1 | Qwen2.5-72B | Business, prioritization |
| Senior Dev | 2 | DeepSeek-V2-Lite-16B | Networking, DevOps |
| Mid Dev | 2 | Qwen2.5-Coder-14B | Backend, Frontend |
| Junior Dev | 2 | Qwen2.5-Coder-7B | Full-stack, learning |
| Tester | 2 | Qwen2.5-14B | Integration, E2E |

**Agent Composition:**

Each agent's behavior comes from **layered prompts**:

```
Agent Prompt = Base + Archetype + Individual + Context

Example: dev_jr_fullstack_a
├── base_agent.md          (universal behavior)
├── developer.md           (developer archetype)
├── dev_jr_fullstack_a.md  (individual profile)
└── [current context]      (sprint state, learnings)
```

**Agent Profile Structure:**

```markdown
# Individual Profile

## Technical Expertise
- Deep knowledge areas
- Strong competencies
- Learning edges
- Known gaps

## Cognitive Patterns
- Thinking style
- Communication style
- Decision heuristics

## Behavioral Traits
- Strengths
- Weaknesses (realistic flaws!)
- Cognitive biases

## Growth Arc
- Sprint-by-sprint evolution
- Pairing-driven learning
- Meta-learnings applied

## Pairing Dynamics
- With juniors (teaching mode)
- With peers (collaborative)
- With seniors (design partner)

## Tool Access
- Available tools/frameworks
- Specialization-specific access
```

**Key Files:**
- `src/agents/base_agent.py` - Base agent class
- `src/agents/agent_factory.py` - Agent instantiation
- `team_config/00_base/base_agent.md` - Universal behavior
- `team_config/01_role_archetypes/*.md` - Role templates
- `team_config/02_individuals/*.md` - 11 individual profiles

### 4. Shared Context Database

**Schema:**

```sql
-- Kanban board state
kanban_cards (
  id, title, description, status, 
  assigned_pair, story_points, sprint
)

-- Pairing sessions with dialogues
pairing_sessions (
  id, sprint, driver_id, navigator_id,
  task_id, start_time, end_time,
  outcome, decisions JSONB
)

-- Meta-learnings for prompt evolution
meta_learnings (
  id, sprint, agent_id,
  learning_type, content JSONB,
  applied BOOLEAN
)

-- Sprint artifacts
sprint_artifacts (
  id, sprint, artifact_type,
  content JSONB, created_at
)
```

**Key Files:**
- `src/tools/shared_context.py` - Database layer
- `src/tools/kanban.py` - Kanban board management

### 5. Meta-Learning System

**How Agent Prompts Evolve:**

```
Sprint N Retro:
  Keep: "TDD prevented 3 bugs"
  Drop: "Over-engineering caching layer"
  Puzzle: "Balance tech debt vs features?"

Meta-Layer Analysis:
  - Extract learnings
  - Determine affected agents
  - Generate prompt modifications
  
Prompt Update:
  dev_sr_networking.md +=
    "Recent Learning: Start simple with caching,
     optimize when measured need arises.
     (from Sprint N retro)"

Sprint N+1:
  Agent behavior changes based on learning
```

**Decay Mechanism:**

```python
Temporary Knowledge (from profile swaps):
  - Acquired: Sprint N
  - Expires: Sprint N+1 (if not used)
  - Can become permanent if reinforced

Permanent Learnings:
  - From repeated experiences
  - From successful retro actions
  - From pairing knowledge transfer
```

**Key Files:**
- `team_config/04_meta/team_evolution.md` - Evolution rules
- `team_config/04_meta/meta_learnings.jsonl` - Learning log

### 6. Process Enforcement

**Hard Rules (Orchestrator Enforces):**
- No solo commits to production (pairing required)
- WIP limits: 4 in progress, 2 in review
- Test coverage: ≥85% lines, ≥80% branches
- Definition of Done: All criteria must pass

**Soft Rules (Team Self-Enforces):**
- Code quality through review
- Simple design through refactoring
- Standards through collaboration

**Escalation Tiers:**

```
Tier 1: Pair Decides
  ↓ (if can't agree)
Tier 2: Dev Lead Decides
  ↓ (if business impact)
Tier 3: PO + Dev Lead
  ↓ (if strategic)
Tier 4: Stakeholder Review
```

**Key Files:**
- `team_config/03_process_rules/xp_practices.md`
- `team_config/03_process_rules/kanban_workflow.md`
- `team_config/03_process_rules/consensus_protocol.md`

### 7. Disturbance Injection

**Realistic Failures:**

| Disturbance Type | Frequency | Impact |
|------------------|-----------|--------|
| Dependency breaks | 1 in 6 sprints | Medium |
| Production incident | 1 in 8 sprints | High |
| Flaky test | 1 in 4 sprints | Low |
| Scope creep | 1 in 5 sprints | Medium |
| Junior misunderstanding | 1 in 3 sprints | Low-Medium |
| Architectural debt | 1 in 6 sprints | Medium-High |

**Blast Radius Control:**

Leaders monitor and contain:
- Max 30% velocity impact
- Max 15% quality regression
- Escalate to stakeholder if exceeded

**Key Configuration:**
- `config.yaml` - Disturbance frequencies
- `src/orchestrator/disturbances.py` - Injection logic

## Infrastructure

### Kubernetes Deployment

```yaml
Namespace: agile-agents

Services:
  - postgres (StatefulSet) - Team state
  - redis (Deployment) - Coordination
  - vllm-server (DaemonSet) - Model serving on GH200
  - orchestrator (Deployment) - Sprint management
  - prometheus (Deployment) - Metrics
  - grafana (Deployment) - Visualization
```

**Resource Allocation:**

```
Node 1: Orchestrator + Database
  - 16 CPU cores
  - 64GB RAM

Node 2: vLLM (Large models)
  - 32 CPU cores
  - 128GB RAM
  - 2x A100 or 3x A6000 GPUs

Nodes 3-4: vLLM (Mid/Small models)
  - 24 CPU cores each
  - 96GB RAM each
  - 2x RTX 4090 per node
```

**Key Files:**
- `infrastructure/k8s/deployment.yaml`
- `infrastructure/k8s/services.yaml`

### Model Serving (vLLM)

**Strategy: Multi-tier serving**

```python
Tier 1 (Large): Port 8000
  - Qwen2.5-72B (QA Lead, PO)
  - Qwen2.5-Coder-32B (Dev Lead)
  
Tier 2 (Medium): Port 8001
  - DeepSeek-V2-Lite-16B (Senior Devs)
  - Qwen2.5-14B (Mid Devs, Testers)
  
Tier 3 (Small): Port 8002
  - Qwen2.5-Coder-7B (Junior Devs)
```

**Optimizations:**
- Continuous batching (multiple requests processed together)
- KV cache for repeated contexts
- Tensor parallelism for large models

## Monitoring & Observability

### Prometheus Metrics

**Sprint-Level:**
- `sprint_velocity` - Story points completed
- `sprint_cycle_time` - Time from start to done
- `test_coverage_percent` - Code coverage

**Team Health:**
- `pairing_sessions_total` - Pairing activity
- `consensus_time_seconds` - Time to reach agreement
- `solo_commit_attempts_total` - Process violations

**Agent Performance:**
- `agent_response_seconds` - Inference latency
- `agent_tokens_total` - Token consumption
- `agent_errors_total` - Generation failures

**Junior Value:**
- `junior_questions_total` - Questions by category/outcome
- `senior_pause_before_answer` - Thoughtful response time
- `senior_learned_from_junior` - Reverse mentorship events
- `question_dismissal_rate` - Cultural health

**Key Files:**
- `src/metrics/sprint_metrics.py`
- `src/metrics/prometheus_exporter.py`
- `infrastructure/monitoring/prometheus.yml`

### Grafana Dashboards

**Sprint Overview:**
- Velocity trend (target: exponential early, linear later)
- Feature completion curve
- Quality metrics (coverage, defects)

**Team Dynamics:**
- Pairing heatmap (who pairs with whom)
- Consensus time distribution
- Escalation frequency

**Agent Health:**
- Response time percentiles (p50, p95, p99)
- Token usage per agent
- Error rates

**Junior Contributions:**
- Question frequency and outcomes
- Reverse mentorship events
- Cultural health indicators

## Data Flow

### Sprint Execution Flow

```
1. Planning
   - PO presents backlog → Shared DB
   - Team estimates → Update cards
   - Initial pairs assigned → Pairing table

2. Development Loop (20 min)
   While time_remaining:
     - Get available pairs
     - Pull tasks from Kanban
     - Run pairing sessions
       * Design dialogue
       * TDD cycles with checkpoints
       * Consensus
     - Update Kanban state
     - Log pairing decisions
     - Tick simulation clock

3. Retrospective
   - All agents contribute → Retro notes
   - Meta-layer extracts learnings
   - Prompt updates applied → Agent configs
   - Learnings logged → meta_learnings.jsonl

4. Artifact Generation
   - Snapshot Kanban → JSON
   - Export pairing log → JSONL
   - Save retro notes → Markdown
   - Calculate metrics → Prometheus
   - Generate reports → Output directory
```

### Profile Swapping Flow (Constrained Mode)

```
Scenario: Production incident

1. Detect Need
   - Production incident occurs
   - Only specialist can handle
   - Specialist currently paired on feature

2. Evaluate Swap
   - Is scenario in allowed list? ✓
   - Can't defer? ✓
   - Blast radius acceptable? ✓

3. Execute Swap
   - Load emergency profile
   - Apply penalties (20% slower)
   - Set proficiency (70% of specialist)
   - Set expiration (1 sprint)

4. Post-Incident
   - Profile reverts
   - Knowledge decays unless used
   - Log swap event for retro
   - Discuss: "Do we need 2 specialists?"
```

## Experiment Modes

### Mode 1: No Swapping (Pure Human Simulation)
```yaml
profile_swapping:
  mode: none
```
- Agents maintain stable roles
- Bottlenecks reveal knowledge silos
- Most realistic to human teams

### Mode 2: Constrained Swapping (Recommended)
```yaml
profile_swapping:
  mode: constrained
  allowed_scenarios:
    - critical_production_incident
    - specialist_unavailable
    - deliberate_cross_training
```
- Swaps only in exceptions
- Penalties applied (slower, temporary)
- Tests organizational resilience

### Mode 3: Free Swapping (AI Optimal)
```yaml
profile_swapping:
  mode: free
```
- Optimal agent for every task
- No knowledge bottlenecks
- Baseline for comparison

## Output Structure

```
outputs/experiment-001/
├── sprint-01/
│   ├── kanban.json              # Board state
│   ├── pairing_log.jsonl        # All dialogues
│   ├── retro.md                 # Keep/Drop/Puzzle
│   ├── test_coverage.json       # Coverage report
│   ├── meta_learning_diff.md    # Prompt changes
│   └── adrs/                    # Architecture decisions
├── sprint-02/
│   └── ...
├── final_report.md              # Experiment summary
├── velocity_chart.png           # Visualization
└── metrics/                     # Raw Prometheus data
```

## Scalability Considerations

**Current Implementation:**
- 11 agents, 20-minute sprints
- ~40-60 agent interactions per sprint
- ~450k tokens per sprint

**Scaling Up:**
- More agents: Add to team_config/02_individuals/
- Longer sprints: Increase sprint_duration_minutes
- More complex tasks: Adjust task decomposition

**Scaling Down:**
- Fewer agents: Minimum viable team (1 dev, 1 tester, 1 PO)
- Shorter sprints: 10-minute sprints for rapid iteration
- Simpler tasks: Reduce story complexity

## Extension Points

**Adding New Agent Roles:**
1. Create profile in `team_config/02_individuals/`
2. Define specialization, cognitive patterns
3. Run qualification tests
4. Register in `agent_factory.py`

**Custom Process Rules:**
1. Add to `team_config/03_process_rules/`
2. Update orchestrator to enforce
3. Add metrics if needed

**Integration with External Systems:**
- Real Git repositories
- JIRA/Linear for backlog
- Slack for notifications
- Datadog for monitoring

## Security Considerations

**What's Protected:**
- Agent prompts (contain behavioral patterns)
- Team state (PostgreSQL with auth)
- Model endpoints (internal network only)

**What's NOT Protected:**
- No authentication on orchestrator API
- No encryption at rest
- Assumes trusted internal network

**For Production Deployment:**
- Add API authentication
- Encrypt database
- Use Kubernetes secrets
- Isolate network

## Performance Characteristics

**Typical Sprint Timing:**
- Planning: 90 seconds wall-clock
- Development: 20 minutes (1200 seconds)
- Retrospective: 60 seconds
- Artifact generation: 30 seconds
- **Total: ~22 minutes per sprint**

**Throughput:**
- 2-3 micro-features per sprint
- 6-9 TDD cycles total
- 40-60 agent interactions
- ~450k tokens consumed

**Bottlenecks:**
- vLLM inference latency (2-5s per call)
- Database writes (minimal)
- Pairing consensus time (variable)

## Failure Modes

**What Can Go Wrong:**

1. **Model Failures:**
   - Wrong model loaded
   - Out of memory
   - Timeout
   - Mitigation: Health checks, retries

2. **Process Violations:**
   - Solo commits attempted
   - WIP limits exceeded
   - Mitigation: Orchestrator enforcement

3. **Consensus Deadlocks:**
   - Pairs can't agree
   - Escalation path broken
   - Mitigation: Timeout → auto-escalate

4. **Database Issues:**
   - Connection lost
   - Data corruption
   - Mitigation: Connection pooling, backups

## Testing Strategy

**Unit Tests:**
- Agent behavior (does junior ask questions?)
- Kanban operations (WIP limits enforced?)
- Pairing protocol (checkpoints work?)

**Integration Tests:**
- Full pairing session end-to-end
- Sprint lifecycle complete
- Database consistency

**Qualification Tests:**
- Model capability verification
- Role-appropriate behavior
- Realistic mistake patterns

**System Tests:**
- 10-sprint experiment runs
- Velocity trends as expected
- Quality metrics within bounds

## Future Work

**Planned Enhancements:**
1. Real code execution (not just simulation)
2. Integration with GitHub/GitLab
3. Multi-team coordination experiments
4. Long-running experiments (100+ sprints)
5. Comparison with human team data

**Research Questions:**
1. Does velocity follow power law or linear growth?
2. What's optimal junior:senior ratio?
3. How does team size affect dynamics?
4. Can we predict burnout from metrics?
5. What disturbance frequency is realistic?

---

**This architecture enables studying organizational dynamics, team maturity, and process effectiveness through a controlled, reproducible multi-agent system.**
