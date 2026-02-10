# Sprint Planning - Two-Phase Process

Sprint planning happens on Day 0 of each sprint. The goal is to select and plan work for the next sprint (5 simulated working days by default, configurable via `num_simulated_days`).

## Overview

**Duration**: ~4 hours (simulated)
**Participants**: Entire team (PO, developers, testers, leads)
**Output**: Selected stories, broken down into tasks, with owners and pairs assigned

## Phase 1: Story Refinement (PO + Team)

**Duration**: ~2 hours
**Participants**: Everyone (PO, developers, testers, leads)
**Purpose**: Understand WHAT to build and WHY

### Your Role as a Team Member

1. **Listen** to PO's presentation of each story:
   - Business context (why are we building this?)
   - User need (what problem does it solve?)
   - Business value (what's the impact?)
   - Acceptance criteria (how do we know it's done?)
   - Constraints (deadlines, compliance, dependencies)

2. **Ask clarifying questions**:
   - **Technical depth**: "How complex is the authentication flow?"
   - **Edge cases**: "What happens if user loses their 2FA device?"
   - **Integration**: "Does this work with our existing OAuth system?"
   - **User experience**: "Should this be a modal or a new page?"
   - **Scope**: "Is SMS 2FA in scope or just authenticator apps?"
   - **Performance**: "What's the expected load?"

3. **Participate in estimation**:
   - Dev Lead facilitates discussion
   - Share your perspective on complexity
   - Consider: coding time, testing time, integration complexity
   - Use story points: 1 (trivial), 2 (simple), 3 (moderate), 5 (complex), 8 (very complex)
   - Consensus doesn't mean everyone agrees exactly, but everyone can live with it

4. **Help select sprint commitment**:
   - Team capacity = ~3 story points per developer per sprint
   - Don't overcommit - better to under-promise and over-deliver
   - Consider: available time, known risks, team stability

### Good Questions to Ask

**Juniors** - Ask about:
- "Can you explain what [technical term] means in this context?"
- "What's the simplest version of this we could build?"
- "Are there examples of similar features we've built?"

**Mid-levels** - Ask about:
- "How does this integrate with [existing system]?"
- "What are the performance requirements?"
- "Do we need to support backwards compatibility?"

**Seniors** - Ask about:
- "What are the architectural implications?"
- "Have we considered [alternative approach]?"
- "What's the migration strategy from current state?"

### Anti-Patterns to Avoid

❌ **Don't prescribe implementation**: "We should use Redis for this"
   ✅ **Instead**: "What are the data storage requirements?" (let Phase 2 decide how)

❌ **Don't nitpick wording**: "Should this say 'login' or 'sign in'?"
   ✅ **Instead**: "Is there a difference between login and sign-in for users?"

❌ **Don't scope creep**: "Can we also add [related feature]?"
   ✅ **Instead**: "Should we consider [feature] in a future sprint?"

---

## Phase 2: Technical Planning (Team Only - NO PO)

**Duration**: ~2 hours
**Participants**: Developers, testers, Dev Lead, QA Lead (NO PO)
**Purpose**: Decide HOW to build it

### Why PO is Not Present

The PO owns the WHAT and WHY. Phase 2 is about HOW:
- Technical architecture
- Task breakdown
- Implementation approach
- Testing strategy

The team needs freedom to make technical decisions without business stakeholders in the room.

### Your Role as a Developer

1. **Break down stories into tasks**:
   - Each story → 2-4 technical tasks
   - Tasks should be 4-16 hours of work
   - Example for "Add 2FA":
     - Task 1: Design TOTP schema (8h)
     - Task 2: Implement TOTP generation (8h)
     - Task 3: QR code API endpoint (4h)
     - Task 4: Integration tests (8h)

2. **Discuss architecture**:
   - "Should we use Redis or PostgreSQL for sessions?"
   - "REST or GraphQL for this API?"
   - "Sync or async processing?"
   - Dev Lead makes final call if team can't reach consensus

3. **Identify dependencies**:
   - "Task 3 needs Task 1's schema to be done first"
   - "This story depends on the auth service from last sprint"
   - Draw dependency arrows between tasks

4. **Volunteer for task ownership**:
   - Based on your specialization: Go specialist for Go tasks, etc.
   - Seniors often own complex/risky tasks
   - Juniors own simpler, well-defined tasks
   - Task owner provides continuity (stays on task all sprint)

5. **Plan initial pairing**:
   - Each task needs a pair: owner + navigator
   - Senior + Junior = mentoring pair
   - Senior + Senior = complex problem solving
   - Mid + Mid = collaborative learning

### Your Role as a Tester

1. **Identify testability concerns**:
   - "How will we test the QR code generation?"
   - "Do we need test data for different authenticator apps?"
   - "What edge cases should we cover?"

2. **Plan test tasks**:
   - Integration tests (API level)
   - E2E tests (user workflows)
   - Performance tests (load, stress)

3. **Participate as navigator**:
   - QA Lead often navigates on implementation tasks
   - Brings quality perspective to the code

### Dev Lead's Role

- **Facilitate discussion**: Ensure everyone speaks
- **Make tie-breaking decisions**: When team can't agree
- **Assign task owners**: Based on specialization and skill level
- **Identify risks**: "This task is risky because..."
- **Balance workload**: Ensure no one is overloaded

### Output of Phase 2

**For each story, you have**:
- List of technical tasks (2-4 per story)
- Task owners assigned (based on specialization)
- Initial pairs assigned (for Day 1)
- Dependencies identified (task A blocks task B)
- Architectural decisions made (Redis vs Postgres, etc.)

**Example**:
```
Story: US-042 - Add two-factor authentication

Tasks:
- T-01-001: Design TOTP schema
  Owner: Marcus (backend specialist)
  Navigator: Alex (senior networking)
  Hours: 8
  Dependencies: none

- T-01-002: Implement TOTP generation
  Owner: Maya (Go specialist)
  Navigator: Priya (senior DevOps)
  Hours: 8
  Dependencies: T-01-001 (needs schema)

- T-01-003: QR code API endpoint
  Owner: Elena (frontend)
  Navigator: Jamie (junior fullstack)
  Hours: 4
  Dependencies: T-01-002 (needs TOTP logic)

- T-01-004: Integration tests
  Owner: Yuki (QA lead)
  Navigator: Maria (mid-level tester)
  Hours: 8
  Dependencies: T-01-002, T-01-003
```

---

## After Planning

**Tasks added to Kanban**:
- All tasks move to "Ready" column
- Tasks with dependencies stay blocked until upstream completes
- Day 1: Initial pairs pull tasks and start work

**Pair rotation begins**:
- Day 1: Initial pairs work
- Day 2: Navigator rotates, owner stays
- Day 3: Navigator rotates again
- Continues daily until task complete

---

## Tips for Effective Planning

### For Juniors
- Don't be afraid to ask "basic" questions - they're often the most important
- If you don't understand something, others probably don't either
- Write down technical terms you don't know and ask after

### For Mid-Levels
- Bridge between juniors and seniors
- Explain concepts when seniors use jargon
- Challenge assumptions respectfully

### For Seniors
- Avoid jargon and acronyms
- Explain your reasoning, not just your conclusion
- Mentor through questions: "What do you think would happen if...?"

### For Everyone
- **Time-box** discussions: If you're debating for >10 minutes, make a decision
- **Defer detailed design**: Planning is not implementation time
- **Write it down**: Architectural decisions should be documented
- **Focus on value**: Don't gold-plate, build what's needed
