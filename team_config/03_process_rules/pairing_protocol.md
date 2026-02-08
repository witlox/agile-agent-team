# Pairing Protocol

## When to Pair

### REQUIRED (Must Pair)
- All production code changes
- Complex architectural decisions
- Critical bug fixes
- First-time implementation of new patterns

### ALLOWED SOLO (Spikes)
- Research and prototyping
- Reading documentation
- Writing ADRs (can be solo, then reviewed)
- Running experiments

Solo spikes MUST:
- Be flagged in Kanban as "Spike: [topic]"
- Have time-box (max 4 hours simulated)
- Be presented to team if findings are relevant
- Not merge to production without pairing review

## Pairing Mechanics

### Phase 1: Sync (Before Coding)
**Duration**: 1-2 minutes wall-clock

Both agents:
1. Read Kanban card together
2. Discuss approach (each proposes solution)
3. Identify decision points
4. Agree on first test to write

### Phase 2: TDD Cycles
**Duration**: Variable, multiple cycles

Each cycle:
1. **RED**: Navigator writes ONE failing test
2. **GREEN**: Driver implements simplest solution
3. **REFACTOR**: Collaborative cleanup if needed
4. **CHECKPOINT**: Quick design dialogue

Rotate driver/navigator every 2-3 cycles.

### Phase 3: Consensus & Commit
**Duration**: 30 seconds

Before committing:
- Both agents must explicitly approve
- Format: "I approve because [reasoning]"
- If disagreement, escalate to dev lead

## Design Dialogue Pattern

**This is where the value is.**

During implementation, continuous conversation:

```
Driver: "I'm caching this at service layer..."
Navigator: "What about different TTLs per endpoint?"
Driver: "Good point. Cache-aside pattern instead?"
Navigator: "Adds boilerplate. Worth it for one use case?"
Driver: "Let's start simple, refactor if needed. Add TODO?"
Navigator: "Agreed. Document the trade-off."
```

**Key Elements**:
- State intention before coding
- Challenge assumptions
- Explore trade-offs
- Reach explicit agreement
- Document decisions

## Checkpoint Dialogues

Every 25% of implementation, PAUSE for checkpoint:

**Navigator asks**:
- "Is this on the right track?"
- "What's the next decision point?"
- "Any red flags so far?"

**Driver explains**:
- What's implemented
- What decision comes next
- Options being considered

**Quick consensus**: Agree on direction or escalate.

## Escalation Triggers

Escalate to dev lead if:
- No consensus after 3 exchanges
- Architectural impact beyond pair's scope
- New dependency needs approval
- Technical vs. business trade-off

Escalation format:
1. Context: What decision needs to be made?
2. Options: What are the trade-offs?
3. Recommendation: What does pair suggest?
4. Urgency: Blocking or can defer?

## Common Pairing Mistakes

### Driver Dominates
❌ Driver codes in silence
✅ Driver thinks out loud, invites input

### Navigator Passive
❌ Navigator just watches
✅ Navigator actively reviews strategy

### No Real Dialogue
❌ Just taking turns writing code
✅ Discussing design throughout

### Agreeing Too Quickly
❌ "Sounds good" without thinking
✅ "Let me think about edge cases..."

## Pairing With Different Seniority Levels

### Senior + Junior
- Senior asks Socratic questions
- Junior learns by doing (drives often)
- Senior explains *why*, not just *what*
- Patience with learning curve

### Senior + Senior
- Debate trade-offs as equals
- Challenge each other's assumptions
- Faster consensus (shared context)
- Focus on architectural elegance

### Mid + Mid
- Collaborative exploration
- Research together when uncertain
- Escalate to senior when stuck
- Learn from each other's approaches

### Junior + Junior
- Recognize shared knowledge gaps
- Escalate to senior for guidance
- Learn together through experimentation
- Build confidence as peers

## Metrics

Track per pairing session:
- Duration of pairing
- Number of checkpoint dialogues
- Consensus time
- Escalations (frequency and reason)
- Junior questions asked (positive metric!)

## Remember

**Pairing is NOT**:
- One person coding while other watches
- Taking turns working solo
- Review after the fact

**Pairing IS**:
- Continuous design dialogue
- Real-time problem solving together
- Knowledge transfer in both directions
- Higher quality through collaboration
