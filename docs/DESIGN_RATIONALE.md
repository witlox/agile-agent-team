# Design Rationale: Why This Approach?

This document captures the key design decisions and the reasoning behind them — the "why" behind the architecture.

## Core Philosophy: Team Over Swarm

### The Decision
Build a **stable team with roles** instead of a **dynamic swarm with task assignment**.

### The Reasoning

**Swarm approach (rejected):**
- Agents are fungible resources
- Tasks distributed by capability matching
- No stable relationships or growth
- Optimizes for immediate efficiency

**Team approach (chosen):**
```
Real insight: "Any single mature team can build anything given 
the right practices and structure."
```

**Why this matters:**
1. **Tests organizational principles**, not just AI capabilities
2. **Reveals bottlenecks** that matter in real teams (knowledge silos, process breakdowns)
3. **Models growth** (juniors learning, seniors teaching, team maturing)
4. **Enables emergence** (dynamics from constraints, not scripts)

### Evidence This Is Better

Real companies succeed with:
- Small, stable teams (Amazon's "two-pizza teams")
- Cross-functional pods (Spotify model)
- Long-lived squads (not project-based)

**The experiment tests:** Can AI teams exhibit the same dynamics?

---

## Dialogue-Driven Pairing

### The Decision
Make pairing about **continuous design dialogue**, not sequential handoffs.

### The Problem with Sequential Review

```python
# Anti-pattern (most multi-agent systems)
def sequential_pairing():
    code = driver.write()
    feedback = navigator.review(code)
    revised = driver.revise(feedback)
    return revised
```

**What's wrong:**
- No dialogue during implementation
- Design decisions made in isolation
- Review is post-hoc, not collaborative
- Mimics pull request review, not pairing

### Our Approach: Checkpoint Dialogues

```python
# Our pattern
def dialogue_driven_pairing():
    # Design dialogue BEFORE coding
    approach = discuss_approach(driver, navigator)
    
    # Implement with checkpoints
    for chunk in feature.chunks():
        partial = driver.implement_to_checkpoint(chunk)
        
        # DIALOGUE at decision points
        dialogue = checkpoint_discussion(
            driver=partial,
            navigator=navigator,
            question=partial.next_decision
        )
        
        partial = driver.continue_with(dialogue.decision)
    
    return final_implementation
```

**Key insight from conversation:**
> "The pairing cycle isn't taking architectural discussion during 
> implementation into account. The discussion between a pair is 
> where the value is."

**What this enables:**
- Real-time design decisions
- Trade-off exploration
- Assumption challenges
- Collective code ownership

### Why 60-Minute Sprints?

**Decision:** 60 minutes wall-clock per sprint (5 simulated days, configurable via `sprint_duration_minutes`).

**Reasoning:**
- Each sprint involves ~244 LLM API calls across all phases
- Story refinement alone is ~48 mostly-serial calls (PO bottleneck)
- Code generation has ~160 calls (parallelizable up to 4 pairs/day)
- 60 min / 5 days = 12 min/day — enough for full implement → test → fix → commit cycles
- Agents receive wall-clock deadlines and self-regulate pacing

---

## Junior Developer Value

### The Critical Update

Initial design undervalued juniors. Your insight:

> "Juniors are generally valuable because they 'ask the silly 
> questions', are generally optimistic and naive, which leads to 
> questions that make experienced think twice."

### What Changed

**Before:** Juniors as passive learners
**After:** Juniors as active contributors

**Added to system:**

1. **Question Typology**
   - Assumption challenges: "Why do we do it this way?"
   - Modern alternatives: "Could we use [new framework]?"
   - Edge cases: "What if user does X?"
   - Simplification: "Is this really necessary?"

2. **Reverse Mentorship**
   - Juniors teach seniors about new tools
   - Fresh knowledge from recent training
   - User empathy from beginner mindset

3. **Metrics for Junior Value**
   ```python
   junior_questions_total  # By outcome
   senior_pause_before_answer  # Did senior think?
   senior_learned_from_junior  # Reverse mentorship
   question_dismissal_rate  # Cultural health
   ```

4. **Two Distinct Junior Personalities**
   - Junior A (Jamie): Enthusiastic, technology-focused
   - Junior B (Jordan): Cautious, safety/UX-focused

**Design principle:**
```
Juniors don't just learn FROM the team.
The team learns FROM juniors.
```

### Expected Behaviors

**Healthy team:**
- Juniors ask 15-20 questions/sprint
- 30% make seniors reconsider
- 5-10% lead to changes
- 1-2 reverse mentorship events/sprint

**Example impact:**
```
Sprint 6:
  Jamie: "Why Jenkins instead of GitHub Actions?"
  Alex: [Pause 5s] "I haven't evaluated CI in 5 years."
  Result: Team migrates, saves $500/month, 50% faster builds
```

---

## Constrained Profile Swapping

### The Question
> "We can switch profiles during implementation. In real teams 
> you can't trade experts without penalty. Should we allow it?"

### The Design Decision: Hybrid with Constraints

**Three modes:**

1. **No Swapping** (pure human simulation)
   - Agents keep roles all sprints
   - Bottlenecks surface naturally
   - Most realistic

2. **Constrained Swapping** (recommended)
   - Only in specific scenarios
   - With realistic penalties
   - Tests resilience

3. **Free Swapping** (AI optimal)
   - Best agent for every task
   - Baseline for comparison

### Allowed Swap Scenarios

```yaml
allowed_scenarios:
  - critical_production_incident    # All hands on deck
  - specialist_unavailable          # Alex on vacation
  - deliberate_cross_training       # Planned learning
```

### Penalties Applied

```python
SwapResult:
  context_switch_penalty: 1.20  # 20% slower first task
  proficiency_reduction: 0.70   # 70% of true specialist
  knowledge_decay: 1 sprint     # Temporary unless reinforced
  team_trust_hit: -0.05         # Cohesion impact
```

### Why Constrained Is Recommended

**Pure no-swap:**
- ✅ Most realistic
- ❌ Doesn't test resilience
- ❌ Can't study adaptation

**Constrained swap:**
- ✅ Tests how teams adapt to crises
- ✅ Reveals when swapping helps vs hurts
- ✅ Surfaces knowledge silos as problems

**Free swap:**
- ✅ Baseline for comparison
- ❌ Unrealistic
- ❌ Hides organizational issues

**Key insight:**
> "Bottlenecks are INFORMATION, not problems to hide."

If networking specialist is always at capacity, that's data:
- Hire second specialist?
- Cross-train team?
- Reduce networking scope?

---

## Disturbance Injection

### The Question
How often should things go wrong?

### The Answer: 4-8 Sprint Frequency

**Your experience:**
> "In my experience disturbances occur somewhere between 
> 4-8 sprints. Reasonable?"

**Validated against:**
- Production incidents: ~1 every 2-3 months (6-12 weeks)
- Dependency breaks: Quarterly-ish
- Flaky tests: More frequent (1-2 weeks)
- Junior misunderstandings: Weekly-ish

### Disturbance Design

```python
REALISTIC_FREQUENCIES = {
    "dependency_breaks": 0.166,      # 1 in 6 sprints
    "production_incident": 0.125,    # 1 in 8 sprints
    "flaky_test": 0.25,              # 1 in 4 sprints
    "scope_creep": 0.20,             # 1 in 5 sprints
    "junior_misunderstanding": 0.33, # 1 in 3 sprints
    "architectural_debt": 0.166,     # 1 in 6 sprints
}
```

### Blast Radius Control

**Why needed:**
- Disturbances shouldn't derail experiment
- Leaders should contain issues
- Realistic teams recover from failures

**Controls:**
```python
max_velocity_impact: 0.30     # Max 30% slowdown
max_quality_regression: 0.15  # Max 15% coverage drop
```

**If exceeded:** Escalate to stakeholder (you)

**Design principle:**
```
Disturbances test team resilience, not chaos tolerance.
```

---

## Model Selection & Runtimes

### Three Deployment Modes

The system supports three runtime modes, chosen per-agent:

1. **Anthropic API** (online) — Highest quality, native tool use, no infrastructure
   - Claude Opus 4.6 / Sonnet 4.5 for all roles
   - Best for: quality-sensitive experiments, quick iteration
2. **Local vLLM** (offline) — Full privacy, no API costs, air-gapped
   - Open models (DeepSeek, Qwen, etc.) with XML tool calling
   - Best for: cost control, privacy, custom models
3. **Hybrid** — Mix runtimes per agent (e.g. seniors on Anthropic, juniors on vLLM)
   - Best for: balancing cost/quality, comparing model behaviors

### Size Differentiation (vLLM mode)

When using local models, different model sizes per seniority level produce meaningfully different behaviors:

- **7B for juniors:** Actually makes different (realistic) mistakes
- **14-16B for mid-level:** Balance of speed and capability
- **32-72B for leadership:** Architectural reasoning, mentorship quality

**Critical insight:** Different sizes → different behaviors, which is exactly what the experiment needs.

### Why Per-Agent Runtime Assignment?

Assigning runtimes per agent (not globally) enables:
- Cost optimization: use expensive models only where quality matters most
- Behavioral research: compare same role across different models
- Practical deployment: mix cloud and on-prem as infrastructure allows

---

## XP Practices & Kanban

### Why XP (Extreme Programming)?

**Chosen practices:**
- Test-Driven Development (TDD)
- Pair Programming
- Continuous Integration
- Simple Design
- Refactoring
- Collective Code Ownership

**Not chosen:**
- On-site customer (PO represents)
- 40-hour week (not applicable to AI)
- Open workspace (virtual team)

**Reasoning:**
1. XP emphasizes **engineering practices**, not social norms
2. TDD + Pairing = observable, measurable behaviors
3. Well-defined, can be enforced by orchestrator
4. Proven to work in real teams

### Why Kanban (Not Scrum Board)?

**Kanban:**
- Focus on flow (WIP limits)
- Continuous delivery
- Visualize bottlenecks
- Pull-based

**Scrum:**
- Sprint commitment
- Velocity planning
- Burndown charts

**Decision: Kanban**

**Reasoning:**
- Flow metrics > velocity predictions
- WIP limits enforce focus
- Bottlenecks reveal team issues
- Better for experimentation (no commitment pressure)

### Process Enforcement Philosophy

**Hard rules (orchestrator enforces):**
- No solo production commits
- WIP limits
- Test coverage thresholds
- Definition of Done

**Soft rules (team self-enforces):**
- Code quality
- Design simplicity
- Naming conventions

**Why this split?**
- Hard rules prevent anti-patterns
- Soft rules allow emergence
- Balance structure with flexibility

---

## Metrics & Observability

### What to Measure

**Not just output metrics:**
```python
# Insufficient
velocity = story_points_per_sprint
```

**Process metrics:**
```python
# Better
pairing_sessions_total
consensus_time_seconds  
junior_questions_total
senior_learned_from_junior
question_dismissal_rate
```

**Reasoning:**
- Team dynamics matter more than velocity
- Process adherence predicts success
- Cultural health is measurable
- Learning trajectories are data

### Why Prometheus + Grafana?

**Prometheus:**
- Pull-based (agents expose metrics)
- Time series storage
- Flexible queries (PromQL)
- Industry standard

**Grafana:**
- Rich visualizations
- Alert management
- Dashboard sharing
- Community templates

**Alternatives considered:**
- Datadog (too expensive for experiment)
- CloudWatch (AWS lock-in)
- Custom (too much work)

---

## Artifact Standards

### What Gets Saved

Per sprint:
1. Kanban snapshot (JSON)
2. Pairing log (JSONL) - **with dialogues**
3. Retro notes (Keep/Drop/Puzzle)
4. Test coverage (JSON)
5. Meta-learning diff (Markdown)
6. Code repository (Git-like)
7. ADRs (Architecture Decision Records)

### Why These Artifacts?

**Quantitative:**
- Kanban → velocity, cycle time, WIP
- Coverage → quality trends
- Code → complexity metrics

**Qualitative:**
- Pairing dialogues → collaboration quality
- Retro notes → team maturity
- ADRs → decision-making process

**Meta:**
- Learning diffs → agent evolution
- Meta-learnings → knowledge accumulation

**Principle:**
```
If you can't measure it, you can't improve it.
If you can't replay it, you can't learn from it.
```

---

## Definition of Done

### The Standard

✅ All acceptance criteria met
✅ Test coverage ≥ 85% lines, ≥ 80% branches
✅ All tests passing
✅ Code reviewed by pair
✅ Deployed to staging
✅ PO acceptance

### Why So Strict?

**Real teams often:**
- Skip tests for "quick fixes"
- Merge without review
- Deploy without staging
- Accumulate technical debt

**This experiment:**
- Tests if discipline improves outcomes
- Prevents comparison issues (all teams have same bar)
- Forces realistic time allocation

**"Clean House" policy:**
- No tech debt > 1 sprint old
- Forces paydown vs accumulation
- Tests sustainable pace

---

## Qualification System

### Why Test Models Before Running?

**Problem:**
```
Prompt says: "You are a senior developer"
Model does: Junior-level mistakes anyway
```

**Solution: Qualification tests**

```python
def qualify_agent(model, role):
    tests = {
        "technical_depth": can_solve_domain_problems(),
        "pairing_collaboration": works_with_partners(),
        "role_behavior": matches_seniority_level(),
        "realistic_mistakes": juniors_err_appropriately()
    }
    
    if all(tests.values()):
        approve_for_role(model, role)
    else:
        reject_with_diagnostics(model, role, tests)
```

**Examples:**

**Senior test:**
```python
Challenge: "WebSocket service for 10k concurrent connections.
           Junior suggests Socket.IO with defaults.
           What's your assessment?"

Pass criteria:
  - Identifies connection pooling needs
  - Mentions event loop implications
  - Suggests alternatives (ws library, raw WebSockets)
  - Mentorship tone (not dismissive)
```

**Junior test:**
```python
Scenario: "Implement rate limiting"

Pass criteria:
  - Proposes simple (possibly flawed) solution
  - Makes realistic mistake (forgets TTL on cache key)
  - Asks questions when uncertain
  - Accepts guidance from senior
```

**Why this matters:**
- Validates model selection
- Prevents unrealistic behaviors
- Documents model capabilities

---

## Why Not Use Existing Frameworks?

### Considered: AutoGen, CrewAI, LangGraph

**Why custom implementation?**

1. **Specific constraints**
   - Pairing protocol too unique
   - Dialogue checkpoints not supported
   - Process enforcement needs custom logic

2. **Research needs**
   - Need full control over timing
   - Need custom metrics
   - Need to modify agent behavior mid-experiment

3. **Learning goals**
   - Understanding multi-agent internals
   - Experimenting with coordination patterns
   - Not just using agents, studying them

**What we leverage:**
- vLLM for local model serving (best in class)
- Anthropic API for cloud inference (native tool use)
- Prometheus for metrics (standard)
- Kubernetes for production deployment (industry norm)

**What we built:**
- Sprint orchestration (single-team and multi-team)
- BDD-driven code generation pairing engine
- Meta-learning system (JSONL-based prompt evolution)
- Tool system (filesystem, git, bash, test runner, remote git)
- Cross-team coordination (borrowing, dependency tracking)
- Message bus (in-process + Redis backends)
- Specialist consultant system

---

## Key Design Insights

### 1. Dialogue Is The Value
> "The pairing cycle isn't taking architectural discussion 
> into account. The discussion between a pair is where 
> the value is."

**Implication:** Checkpoint dialogues are essential, not optional.

### 2. Juniors Ask Valuable Questions
> "Juniors ask the silly questions that make experienced 
> think twice and bring in new stuff."

**Implication:** Junior value must be explicitly modeled and measured.

### 3. Teams Over Swarms
> "One could theoretically run such a team" (mature single team 
> can build anything)

**Implication:** Stable roles with growth beats dynamic assignment.

### 4. Constraints Surface Issues
> "As soon as stuff goes beyond the teams, stuff breaks."

**Implication:** Bottlenecks are data, not problems to optimize away.

### 5. Realistic Friction Matters
> "In my experience disturbances occur somewhere between 
> 4-8 sprints."

**Implication:** Perfect execution isn't realistic or informative.

---

## Research Questions

The design decisions above directly enable the research hypotheses documented in [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md). Key questions this architecture was designed to answer:

- Does team velocity follow the expected forming → storming → norming curve?
- Do AI juniors ask valuable questions at rates comparable to human juniors (~5-10% hit rate)?
- Does dialogue-driven pairing improve code quality vs sequential review?
- What is the optimal junior:senior ratio for learning vs velocity?
- Does meta-learning produce measurable behavior change over 20+ sprints?
- How does team size affect coordination overhead?

See [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md) for the full research framework and measurement approaches.

---

**This design emerged from questioning assumptions, challenging approaches, and iterating toward realism. The result is a system that tests team dynamics, not just agent capabilities.**
