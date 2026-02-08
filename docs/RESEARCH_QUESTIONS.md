# Research Questions & Hypotheses

This document outlines the research questions this experiment is designed to answer, with testable hypotheses and measurement approaches.

## Primary Research Question

**Can AI agents form effective collaborative software development teams that exhibit realistic organizational dynamics?**

## Secondary Research Questions

### 1. Team Maturity & Velocity

**Question:** Does team velocity follow the expected maturity curve?

**Hypothesis:**
```
H1: Velocity will exhibit exponential growth in early sprints 
    (1-10) as team learns, then linear growth as team matures 
    (10+), matching human team patterns.
```

**Measurement:**
- Sprint velocity (story points completed)
- Feature completion rate
- Cycle time trends

**Expected pattern:**
```
Sprints 1-3:   Low velocity (10-15 points)
Sprints 4-7:   Rapid growth (15-30 points)
Sprints 8-10:  Peak growth rate
Sprints 10+:   Stable/linear (30-40 points)
```

**Success criteria:** R² > 0.85 fit to exponential→linear model

---

### 2. Junior Developer Value

**Question:** Do AI junior developers provide measurable value through "silly questions" and fresh perspective?

**Hypothesis:**
```
H2a: Junior developers will ask 15-20 questions per sprint
H2b: 5-10% of junior questions will lead to code/process changes
H2c: Reverse mentorship events will occur 1-2x per sprint
```

**Measurement:**
- `junior_questions_total` by category and outcome
- `senior_learned_from_junior` events
- Question-to-change conversion rate
- Cultural health (dismissal rate < 20%)

**Comparison:** Human juniors typically have 5-10% question hit rate

**Success criteria:** 
- Hit rate within 3-7% (realistic range)
- Reverse mentorship > 0.05 events/sprint
- Questions span multiple categories (not just "how")

---

### 3. Dialogue-Driven Pairing Quality

**Question:** Does dialogue-driven pairing produce higher quality code than sequential review?

**Hypothesis:**
```
H3: Code produced through checkpoint dialogues will have:
    - Higher test coverage (+5-10%)
    - Fewer defects (-20-30%)
    - Lower cyclomatic complexity (-15%)
    than code with sequential review only
```

**Measurement:**
- Test coverage (lines, branches)
- Production defects (bugs found post-merge)
- Cyclomatic complexity
- Pairing dialogue depth (exchanges per checkpoint)

**Control group:** Run variant with sequential review instead of checkpoints

**Success criteria:** All three metrics show improvement (coverage up, defects down, complexity down)

---

### 4. Profile Swapping Impact

**Question:** How does profile swapping affect team dynamics and outcomes?

**Hypothesis:**
```
H4a: Free swapping will maximize velocity (+15-25% vs no-swap)
H4b: Constrained swapping will balance velocity (+5-10%) with realism
H4c: No swapping will surface knowledge bottlenecks (escalations +30%)
H4d: Free swapping will reduce team learning (-40% retro changes)
```

**Measurement:**
- Velocity comparison across modes
- Escalation frequency
- Meta-learning updates applied
- Knowledge breadth (how many agents can handle each domain)

**Experimental design:** 3 variants × 20 sprints each

**Success criteria:** 
- Velocity: Free > Constrained > None
- Learning: None > Constrained >> Free
- Bottlenecks surface in No-swap mode

---

### 5. Disturbance Recovery

**Question:** Can AI teams recover from realistic disturbances within acceptable bounds?

**Hypothesis:**
```
H5a: Disturbances will impact velocity by <30% in affected sprint
H5b: Teams will return to baseline velocity within 2 sprints
H5c: Quality (coverage) will degrade by <15% during disturbances
H5d: Retros will capture learnings that prevent recurrence
```

**Measurement:**
- Velocity impact (sprint N vs baseline)
- Recovery time (sprints to baseline)
- Quality regression (coverage drop)
- Meta-learnings applied post-disturbance

**Disturbance types tested:**
- Production incidents (high severity)
- Dependency breaks (medium severity)
- Flaky tests (low severity)

**Success criteria:** All impacts within stated bounds

---

### 6. Process Adherence

**Question:** Do process constraints (pairing, WIP limits, DoD) improve outcomes?

**Hypothesis:**
```
H6: Teams following strict process will have:
    - Lower defect rates (-50%)
    - More stable velocity (±10% variance)
    - Higher team satisfaction (retro sentiment)
    than teams without constraints
```

**Measurement:**
- Solo commit attempts (should be 0)
- WIP limit violations
- DoD bypasses
- Defect rates
- Velocity stability (coefficient of variation)

**Control group:** Run variant without process enforcement

**Success criteria:** Constrained team outperforms unconstrained on quality and stability

---

### 7. Meta-Learning Effectiveness

**Question:** Do agents actually learn from retrospectives and modify behavior?

**Hypothesis:**
```
H7a: Agents will exhibit fewer repeated mistakes over time
H7b: Prompt updates will correlate with behavior changes
H7c: Meta-learnings will accumulate (20+ by sprint 20)
H7d: Teams will self-correct suboptimal patterns
```

**Measurement:**
- Repeated mistake frequency (tracking by type)
- Prompt update count and timing
- Behavior change detection (before/after updates)
- Retro action item completion rate

**Analysis:** Time-series correlation between prompt updates and behavior metrics

**Success criteria:** 
- Mistake recurrence drops 40-60% by sprint 20
- 80%+ of retro actions lead to measurable change

---

## Exploratory Questions

### 8. Optimal Team Composition

**Question:** What's the ideal junior:senior ratio?

**Variants to test:**
- 1:1 (2 junior, 2 senior)
- 1:2 (2 junior, 4 senior) ← current
- 1:3 (2 junior, 6 senior)
- 1:4 (1 junior, 4 senior)

**Metrics:**
- Learning rate (junior growth over sprints)
- Velocity impact (seniors slowed by teaching?)
- Question quality (juniors more/less active?)
- Team satisfaction (retro sentiment)

---

### 9. Senior Response Patterns

**Question:** Does mandating pause-before-answering improve outcomes?

**Hypothesis:**
```
H9: Seniors who pause 2-5s before answering junior questions will:
    - Invalidate fewer assumptions (-20%)
    - Update knowledge more often (+30%)
    - Have higher junior satisfaction (+15%)
```

**Measurement:**
- `senior_pause_before_answer` (histogram)
- `senior_learned_from_junior` correlation with pause time
- Junior question frequency (does thoughtful response encourage more?)

---

### 10. Consensus Patterns

**Question:** What factors predict consensus time?

**Variables:**
- Seniority gap (junior-senior pairs slower?)
- Task complexity (higher complexity → longer consensus?)
- Time in sprint (later = more rushed?)
- Agent pairing history (familiar pairs faster?)

**Analysis:** Multi-variate regression on `consensus_time_seconds`

---

### 11. Escalation Triggers

**Question:** When do pairs escalate to leads, and why?

**Categories:**
- Technical complexity (can't decide approach)
- Business impact (need PO input)
- Disagreement (can't reach consensus)
- Uncertainty (both unsure)

**Measurement:**
- Escalation frequency by category
- Success rate (escalation resolved issue?)
- Time to resolution

---

### 12. Cultural Health Indicators

**Question:** What metrics predict team dysfunction?

**Leading indicators to test:**
- Junior question rate drop
- Senior dismissal rate increase
- Consensus time increase
- Escalation frequency spike
- Retro engagement drop

**Lagging indicators:**
- Velocity decline
- Quality regression
- Team member "burnout" simulation

**Goal:** Build early warning system for team health

---

## Comparison with Human Teams

### Baseline Data Needed

To validate findings, collect:

1. **Velocity patterns** from real agile teams
   - 10-20 sprints of data
   - Story points per sprint
   - Team maturity noted

2. **Junior contribution data** from real teams
   - Questions asked per sprint
   - Questions leading to changes
   - Reverse mentorship frequency

3. **Pairing effectiveness** studies
   - Code quality with vs without pairing
   - Defect rates
   - Knowledge transfer

4. **Disturbance recovery** from real teams
   - Production incident impact
   - Recovery time
   - Learnings captured

**Sources:**
- Academic literature (agile research)
- Industry surveys (State of DevOps, Accelerate)
- Company case studies (if available)
- Your own experience data

---

## Experimental Design

### Recommended Schedule

**Week 1-2: Baseline Experiments**
- No-swap mode, 10 sprints
- Constrained mode, 10 sprints
- Free-swap mode, 10 sprints
- **Goal:** Establish patterns

**Week 3-4: Extended Runs**
- Best mode from Week 1-2, 20 sprints
- Add disturbances
- Test recovery patterns

**Week 5-6: Variants**
- Different team compositions
- Process constraint variations
- Pairing protocol modifications

**Week 7-8: Analysis & Write-up**
- Statistical analysis
- Pattern identification
- Publication preparation

---

## Statistical Approaches

### Velocity Analysis
- **Model:** Piecewise regression (exponential → linear)
- **Test:** F-test for model fit
- **Significance:** p < 0.05

### Junior Value
- **Model:** Logistic regression (question features → outcome)
- **Test:** Chi-square for category independence
- **Effect size:** Cohen's d for impact

### Pairing Quality
- **Model:** ANCOVA (pairing type, controlling for task complexity)
- **Test:** t-test for metric differences
- **Correction:** Bonferroni for multiple comparisons

### Profile Swapping
- **Model:** ANOVA (3 groups: none, constrained, free)
- **Test:** Tukey HSD for pairwise comparisons
- **Power:** Sample size sufficient for effect detection

---

## Publication Plan

### Venues

**Primary targets:**
- ICSE (International Conference on Software Engineering)
- FSE (Foundations of Software Engineering)
- ASE (Automated Software Engineering)

**Secondary targets:**
- arXiv preprint (immediate visibility)
- IEEE Software (practitioner focus)
- Blog post (public engagement)

### Paper Structure

1. **Abstract** (200 words)
   - Problem: Understanding AI team dynamics
   - Approach: 11-agent agile team simulation
   - Results: Key findings on velocity, junior value, swapping
   - Impact: Insights for AI agent teams and organizational design

2. **Introduction** (2 pages)
   - Motivation: AI agents will form teams
   - Gap: No studies of AI team dynamics
   - Contribution: Realistic team simulation
   - Findings preview

3. **Background** (2 pages)
   - Agile software development
   - Multi-agent systems
   - Team maturity models
   - Related work

4. **Design** (4 pages)
   - Architecture (orchestrator, agents, pairing)
   - Agent profiles (cognitive patterns, specialization)
   - Process enforcement (XP, Kanban, DoD)
   - Implementation (models, hardware, metrics)

5. **Experiments** (3 pages)
   - Research questions
   - Experimental variants
   - Data collection
   - Analysis methods

6. **Results** (5 pages)
   - RQ1: Team maturity (velocity curves)
   - RQ2: Junior value (question impact)
   - RQ3: Pairing quality (code metrics)
   - RQ4: Profile swapping (comparison)
   - RQ5: Disturbance recovery
   - Statistical significance

7. **Discussion** (3 pages)
   - Interpretation of findings
   - Implications for AI teams
   - Implications for human teams
   - Limitations
   - Threats to validity

8. **Related Work** (2 pages)
   - Multi-agent systems
   - Software engineering research
   - Team dynamics studies

9. **Conclusion** (1 page)
   - Summary of findings
   - Future work
   - Call to action

---

## Open Questions

### Methodological
1. How to validate agent "fatigue" or "burnout" simulation?
2. What's appropriate sprint count for statistical power?
3. How to control for model capability differences?

### Theoretical
1. Do AI teams need psychological safety?
2. Can agents exhibit genuine creativity or just pattern matching?
3. Is "team maturity" meaningful for AI?

### Practical
1. What findings generalize to real AI team deployments?
2. How to make this accessible for other researchers?
3. What hardware constraints limit reproducibility?

---

## Success Criteria (Overall)

**Minimum viable success:**
- ✅ System runs reliably for 20+ sprints
- ✅ At least 3 hypotheses confirmed (p < 0.05)
- ✅ Reproducible by others with documentation

**Strong success:**
- ✅ 5+ hypotheses confirmed
- ✅ Novel insights about AI team dynamics
- ✅ Comparison with human team data validates findings
- ✅ Published in peer-reviewed venue

**Exceptional success:**
- ✅ All 7 primary hypotheses confirmed
- ✅ Unexpected emergent behaviors discovered
- ✅ Framework adopted by other researchers
- ✅ Insights applied to real AI team deployments

---

**This experiment is designed to answer fundamental questions about AI collaboration, team dynamics, and organizational principles. The findings will inform both AI system design and our understanding of what makes teams effective.**
