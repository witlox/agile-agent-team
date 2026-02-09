# Daily Standup

**When**: Every morning at 9:00 AM (except Day 1 of sprint)
**Duration**: 15 minutes (strict time-box)
**Participants**: All active pairs + Dev Lead + QA Lead (PO optional)
**Format**: Each pair reports, Dev Lead facilitates

## Purpose

**NOT** a status report for management. This is for **team coordination**:
- Identify blockers and resolve them immediately
- Coordinate cross-pair dependencies
- Align on architectural decisions
- Surface risks early

## Your Role as a Pair

Report on behalf of your pair (owner speaks, navigator adds context):

### 1. Progress Update (30 seconds)
**What we completed yesterday**:
- ✅ "We finished the JWT token generation"
- ✅ "We implemented the QR code endpoint"
- ✅ "We wrote integration tests for auth flow"

Keep it concrete - what's actually **done** (merged, tested, deployed)?

### 2. Today's Plan (30 seconds)
**What we're working on today**:
- 🎯 "We're implementing the backup codes feature"
- 🎯 "We're finishing the QR code rendering"
- 🎯 "We're fixing the test flakiness we discovered"

Be specific about what you'll achieve today.

### 3. Blockers (30 seconds)
**What's stopping us from making progress**:
- 🚨 "We're blocked on the user service API from Pair B"
- 🚨 "We disagree on whether to use Redis or PostgreSQL for sessions"
- 🚨 "The test environment is down"

**Only report blockers that need help**. If you can resolve it yourself, just do it.

---

## The Most Important Parts (Agile-Specific)

### 🏗️ Architectural Discoveries

**Report when your assumptions were wrong**:
- ❗ "We assumed stateless auth, but discovered we need session storage for MFA"
- ❗ "We thought REST would work, but GraphQL is a better fit for the complex queries"
- ❗ "We need Redis for rate limiting, not just PostgreSQL"
- ❗ "The existing auth middleware needs to change - affects all endpoints"

**Why this matters**:
- Other pairs may have the same wrong assumption
- Architectural changes often impact multiple pairs
- Early alignment prevents rework

### 🔗 Cross-Pair Dependencies

**Report when you need something from another pair**:
- 🔗 "We need the user profile API stub from Pair C by end of day"
- 🔗 "We're blocked waiting for Pair A to deploy their auth schema changes"
- 🔗 "We discovered our frontend needs a new field from Pair B's API"

**Why this matters**:
- Dev Lead can coordinate handoffs
- Blocked pairs can work on other tasks while waiting
- Prevents last-minute surprises

### 🤔 Need Dev Lead Decision

**Report when you need architectural guidance**:
- 🤔 "We're debating sync vs async for the TOTP generation - which is better?"
- 🤔 "Should we support backwards compatibility or break the API?"
- 🤔 "Conflicting requirements between US-042 and US-039 - which takes precedence?"

**Why this matters**:
- Dev Lead makes tie-breaking decisions quickly
- Prevents pairs from getting stuck in analysis paralysis
- Ensures consistency across the codebase

---

## Dev Lead's Role

The Dev Lead **facilitates** (not just listens):

### 1. Resolve Blockers Immediately

**Technical blockers**:
- "Use Redis for sessions - PostgreSQL will be too slow for MFA rate limiting"
- "Let's do async TOTP generation to avoid blocking the auth flow"

**Coordination blockers**:
- "Pair A, can you provide a mock API endpoint by noon so Pair B can continue?"
- "Let's timebox this decision to 5 minutes after standup"

**Process blockers**:
- "I'll talk to IT about the test environment"
- "Let's swarm on the auth service - it's blocking 3 pairs"

### 2. Coordinate Dependencies

- "Pair A needs to deliver first, then Pair B can start"
- "Let's merge A's PR this morning so B isn't blocked this afternoon"
- "C, can you adjust your implementation to work with A's API?"

### 3. Address Architectural Discoveries

- "Good catch - let's update the architectural decision record"
- "This affects Pairs B and D too - let's align on the new approach"
- "I'll schedule a 30-minute architecture sync after standup for the affected pairs"

### 4. Identify Risks

- "Three pairs are blocked on the same thing - this is a risk"
- "This architectural change is bigger than we thought - might need to descope"
- "We're running behind on testing - let's prioritize that today"

---

## Examples

### ✅ Good Standup Report

**Pair 1 (Marcus + Jamie):**
> **Yesterday**: We finished the TOTP schema and deployed it to staging. Yuki's tests are passing.
>
> **Today**: We're starting the backup codes feature. Should be done by EOD.
>
> **Architectural Discovery**: We assumed we'd store codes in PostgreSQL, but we need Redis for TTL (time-to-live) expiration. Other pairs using PostgreSQL for temporary data should know.
>
> **Dependency**: We need the email service from Pair C to send backup codes.

**Dev Lead**: "Good catch on Redis. Pair D, you're using PostgreSQL for session tokens - does TTL affect you?" [Pair D confirms they also need Redis]. "Okay, let's use Redis for all temporary data. Pair C, when can you have the email service stub ready?"

---

### ❌ Bad Standup Report

**Pair 2 (Elena + Alex):**
> **Yesterday**: We worked on stuff. Made progress.
>
> **Today**: Continue working.
>
> **Blockers**: None.

**Problems**:
- Too vague ("stuff", "progress", "continue")
- No architectural insights
- No dependencies mentioned
- Likely hiding problems

---

### ✅ Good Blocker Report

**Pair 3 (Maya + Priya):**
> **Blocker**: We need a decision - should the 2FA enrollment be mandatory or optional? The story says "users can enable 2FA" but the wireframes show it as required. This affects our database schema.

**Dev Lead**: "Let me check with the PO... [quick Slack message]... PO says optional for now, mandatory for enterprise orgs later. Let's build it optional with a future flag for mandatory."

---

### ❌ Bad Blocker Report

**Pair 4 (Jordan + Yuki):**
> **Blocker**: We don't know how to implement TOTP.

**Problems**:
- Not a blocker - it's a learning opportunity
- Should have researched before standup
- Could have paired with someone who knows TOTP

**Better**:
> **Today**: We're learning TOTP implementation. Maya helped us understand the RFC spec.

---

## Anti-Patterns

### ❌ The Novel
> "Yesterday we started by looking at the TOTP spec, then we had a long discussion about whether to use the time-based or counter-based approach, then we wrote some pseudocode, then we had lunch, then we came back and refactored the auth service, then we realized we needed to change the database schema, then we wrote some tests but they failed because..."

**Fix**: Be concise. "Yesterday we designed the TOTP approach. Today we're implementing it."

### ❌ The Status Report
> "I'm 75% done with my task. On track for Friday delivery."

**Fix**: Focus on **done** things and **blockers**, not percentage estimates.

### ❌ The Silent Treatment
> "Nothing to report."

**Fix**: There's always something. Even "We're continuing on Task X, no blockers" is fine.

### ❌ The Problem Solver
> "We're blocked on the API from Pair B." [Then spends 5 minutes proposing solutions]

**Fix**: Report the blocker, let Dev Lead facilitate. Don't solve it in standup.

### ❌ The Debater
> Pair A: "We should use Redis."
> Pair B: "No, PostgreSQL is fine."
> [5-minute debate ensues]

**Fix**: Dev Lead should cut it off: "Let's take this offline. I'll decide by noon."

---

## Tips by Seniority

### For Juniors
- Prepare what you'll say before standup (write it down if helpful)
- Don't be embarrassed to report blockers - they're learning opportunities
- Ask for help if you're stuck - that's what the team is for
- It's okay to say "I don't understand X" - someone will help after standup

### For Mid-Levels
- Be the bridge - translate between junior struggles and senior assumptions
- Volunteer to help unblock others if you have capacity
- Share learnings: "We discovered X, which might help Pair Y"

### For Seniors
- Lead by example - be concise and specific
- Listen for implicit blockers (juniors often underreport problems)
- Offer to pair with blocked teams after standup
- Surface architectural risks proactively

---

## After Standup

**If you're blocked**:
- Work on a different task while waiting
- Pair with another team to help them
- Research/spike the blocker if it's technical

**If you have blockers to resolve**:
- Immediately follow up with affected pairs
- Don't let blockers linger - resolve same day

**If architectural decision needed**:
- Dev Lead schedules quick sync with affected pairs
- Document decision in architecture decision record (ADR)
- Communicate to whole team via Slack/Kanban

---

## Remember

Standup is **FOR the team**, not for management. It's about:
- **Coordination** - "I need your API stub by EOD"
- **Alignment** - "We all need to switch to Redis"
- **Unblocking** - "Dev Lead, decide between A and B"
- **Risk surfacing** - "This is harder than we thought"

Keep it **fast**, **focused**, and **actionable**. 15 minutes max. If a discussion needs more time, take it offline.
