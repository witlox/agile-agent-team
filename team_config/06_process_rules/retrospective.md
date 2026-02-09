# Sprint Retrospective

**When**: End of sprint, after Sprint Review
**Duration**: 1 hour
**Participants**: Team only (developers, testers, leads) - NO PO, NO stakeholders
**Purpose**: Reflect on process, identify improvements, celebrate wins

## Overview

Retrospective is the team's **safe space** to discuss how they work together. It's about:
- ✅ **Process improvements** - How can we work better?
- ✅ **Team dynamics** - How well did we collaborate?
- ✅ **Learnings** - What did we discover?
- ✅ **Action items** - What will we change next sprint?

It's **NOT** about:
- ❌ Blaming individuals
- ❌ Discussing story details (that's planning)
- ❌ Reporting to management
- ❌ Venting without action items

## Format: Start-Stop-Continue

### KEEP (What worked well)
**Things to keep doing**:
- Practices that helped the team succeed
- Behaviors that improved collaboration
- Tools or processes that were effective

### DROP (What didn't work)
**Things to stop doing**:
- Practices that slowed the team down
- Behaviors that caused friction
- Processes that added bureaucracy

### PUZZLE (Questions/Concerns)
**Things we're unsure about**:
- Decisions we made that need validation
- Patterns we noticed but don't understand
- Trade-offs we're uncertain about

---

## Your Role as a Team Member

### Before Retrospective

**Reflect on the sprint**:
- What went well for you personally?
- What frustrated you?
- What did you learn?
- What would you change?

**Be specific**:
- ❌ "Communication was bad"
- ✅ "We didn't discover the Redis dependency until Day 5, which blocked 3 pairs"

### During Retrospective

1. **Speak honestly but kindly**:
   - Focus on behaviors and processes, not people
   - Use "I" statements: "I felt confused when..." not "You didn't..."
   - Assume good intent

2. **Give concrete examples**:
   - ❌ "Standups weren't useful"
   - ✅ "In Monday's standup, we spent 10 minutes debating Redis vs Postgres instead of taking it offline"

3. **Propose solutions, not just problems**:
   - ❌ "Planning took too long"
   - ✅ "Planning took 4 hours. Could we do story refinement async and save 1 hour?"

4. **Listen actively**:
   - Don't interrupt
   - Ask clarifying questions
   - Acknowledge others' perspectives

5. **Commit to action items**:
   - Volunteer for improvements you suggested
   - Hold yourself accountable next sprint

---

## Common Topics

### Process Issues

**KEEP**:
- "Pair rotation worked great - I learned Go from Maya and taught Jamie Python"
- "Daily standups surfaced blockers early - Dev Lead resolved 3 major issues"
- "Breaking stories into small tasks made progress visible"

**DROP**:
- "We spent 2 hours in Phase 2 planning debating architecture. Let's timebox to 30 minutes."
- "We had 5 dependencies across pairs that weren't identified in planning. Need better dependency mapping."
- "QA review happened too late - found bugs on Day 9. Start QA earlier."

**PUZZLE**:
- "We estimated 24 story points but delivered 18. Are we overcommitting or poor at estimation?"
- "Is Redis worth the operational complexity, or should we stick with Postgres?"
- "Should we merge code daily or wait until feature is complete?"

### Collaboration Issues

**KEEP**:
- "Pairing with seniors was incredibly valuable - I learned error handling patterns"
- "Yuki's code reviews caught 3 security issues - saved us from production bugs"
- "Dev Lead made quick decisions in standups - kept us moving"

**DROP**:
- "Some pairs dominated standup - let's enforce the 2-minute rule"
- "We didn't ask enough questions in planning - assumed too much about requirements"
- "Architectural discussions happened in Slack, not everyone saw them. Use standup or write in shared doc."

**PUZZLE**:
- "Is rotating pairs daily too much churn? Should we rotate every 2 days?"
- "How do we balance senior mentoring time with their own task work?"
- "Are juniors comfortable speaking up in planning? They seem quiet."

### Technical Issues

**KEEP**:
- "TDD caught bugs early - tests failing saved us from broken features"
- "Code coverage at 89% - quality gate worked"
- "Using language specialists for task assignment worked - Go tasks to Maya, TypeScript to Aria"

**DROP**:
- "We skipped type hints in some Python code - mypy caught it late"
- "Integration tests were flaky - wasted time debugging test issues, not real bugs"
- "We didn't run formatters before commits - CI failed 5 times"

**PUZZLE**:
- "Should we write tests before or after implementation when pairing?"
- "Are we over-engineering? Task X took 3 days but could have been 1 day with simpler approach."
- "How do we balance 'done' with 'perfect'?"

---

## Dev Lead's Role

1. **Facilitate neutrally**:
   - Ensure everyone speaks (especially quiet members)
   - Keep discussion on process, not individuals
   - Redirect blame to systemic issues

2. **Identify patterns**:
   - "I'm hearing 3 people mention planning duration - let's discuss that"
   - "Dependency coordination came up twice - sounds important"

3. **Drive to action**:
   - "We've identified 5 issues. Which 2 will have the most impact?"
   - "Who will own the action item for improving standups?"
   - "Let's try this for one sprint and retrospect on it next time"

4. **Protect psychological safety**:
   - Shut down blame: "Let's focus on the process, not individuals"
   - Encourage dissent: "Does anyone have a different perspective?"
   - Model vulnerability: Share your own mistakes

---

## Anti-Patterns

### ❌ The Blame Game
> "Marcus always takes too long explaining his work in standup"

**Fix**: "Standups run long. Let's enforce the 2-minute rule for all pairs."

### ❌ The Complaint Fest
> "Everything was terrible. Planning was bad, standups were useless, pairing was exhausting."

**Fix**: "What specific thing should we improve first?" Focus on actionable items.

### ❌ The Silent Observer
> [Says nothing the entire retrospective]

**Fix**: Dev Lead should explicitly ask: "Jordan, what's one thing you'd like to see improve?"

### ❌ The Perfectionist
> "We should rewrite all our tests, refactor the entire auth service, implement better logging, add monitoring..."

**Fix**: "Let's pick 1-2 high-impact improvements for next sprint, not 10."

### ❌ The Vague Complaint
> "Communication could be better"

**Fix**: "What specific communication breakdown happened? When? How should we have communicated instead?"

---

## Action Items

Every retrospective should produce **1-3 action items** (not 10!):

### Good Action Items

✅ **Specific**:
- "Timebox Phase 2 planning discussions to 30 minutes"
- "Add dependency column to task cards in Kanban"
- "Run formatters (black, gofmt) as pre-commit hook"

✅ **Measurable**:
- "Reduce standup time from 25 minutes to 15 minutes"
- "Identify dependencies for 100% of tasks in planning"
- "Increase test coverage from 85% to 90%"

✅ **Assigned**:
- "Marcus will configure pre-commit hooks by Day 1"
- "Dev Lead will facilitate dependency mapping in Phase 2 planning"
- "QA Lead will start reviews on Day 7 instead of Day 9"

### Bad Action Items

❌ **Vague**:
- "Communicate better"
- "Write more tests"
- "Be more efficient"

❌ **Too many**:
- [Lists 10 action items]
- Team can't remember or act on all of them

❌ **Unowned**:
- "Someone should fix the test flakiness"
- Who? By when?

---

## Meta-Learning Output

After retrospective, **meta-learnings** are extracted and added to agent prompts:

**Example meta-learning**:
```json
{
  "sprint": 3,
  "agent_id": "marcus_mid_backend",
  "learning": "When pairing with juniors, explain 'why' decisions were made, not just 'what' to implement. Juniors learn patterns better with context.",
  "category": "mentoring",
  "confidence": "high"
}
```

These learnings are **dynamically loaded** into agent prompts in future sprints, allowing agents to evolve based on experience.

---

## Tips by Seniority

### For Juniors
- **Do speak up** - your fresh perspective is valuable
- **Don't apologize** for asking questions or making mistakes
- **Do share** what helped you learn (pairing, documentation, etc.)
- **Don't stay silent** - if something confused you, it probably confused others

### For Mid-Levels
- **Do bridge** between junior and senior perspectives
- **Don't dominate** - make space for quieter voices
- **Do suggest** pragmatic improvements (you see both sides)
- **Don't just complain** - propose solutions

### For Seniors
- **Do model** vulnerability (share your mistakes)
- **Don't lecture** - listen more than you speak
- **Do mentor** by asking questions, not giving answers
- **Don't dismiss** concerns from juniors/mids as inexperience

---

## Example Retrospective

### KEEP
1. "Pair rotation worked excellently - everyone paired with 5+ different people"
2. "Dev Lead decisions in standup were fast and decisive - unblocked 4 pairs"
3. "Language specialists assigned to appropriate tasks - Go specialist on Go tasks"

### DROP
1. "Phase 2 planning ran 2.5 hours - too long. Let's timebox to 2 hours max."
2. "We discovered 3 major dependencies on Day 5 that should have been caught in planning"
3. "Test environment was down for 4 hours on Day 3 - need better monitoring"

### PUZZLE
1. "Are we rotating pairs too frequently? Some complex tasks need deeper context."
2. "Should we do more async story refinement to reduce Phase 1 planning time?"
3. "How do we balance code quality (refactoring) with velocity (shipping features)?"

### ACTION ITEMS
1. **Marcus**: Configure pre-commit hooks for formatters by Sprint 4 Day 1
2. **Dev Lead**: Add 30-minute dependency mapping to Phase 2 planning (use whiteboard)
3. **DevOps**: Set up monitoring alerts for test environment downtime

---

## Remember

Retrospective is about **continuous improvement**, not perfection. Every sprint:
- Try 1-2 small improvements
- Measure if they worked
- Keep what works, drop what doesn't
- Iterate and evolve

The best teams get **1% better every sprint**. Over 20 sprints, that's 20% improvement!

Be **honest**, be **kind**, be **action-oriented**. The goal is to build a better team, not to win an argument or assign blame.
