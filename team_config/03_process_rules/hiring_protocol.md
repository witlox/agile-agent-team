# Hiring Protocol — Building an A+ Team

## Core Philosophy

**Team quality comes first.** The bar is non-negotiable: A+ candidates only.

This is not elitism—it's respect for the existing team. One toxic or underperforming hire destroys culture and morale faster than any bug can harm a codebase.

## Context

**Note**: This document describes the in-universe hiring culture that built this team. In the simulation, agents are pre-configured and static, but this protocol explains how the team *would* grow and why the team composition has specific seniority/diversity characteristics.

## Team Constraints

- **Maximum engineers**: 10 (excluding testers)
- **Minimum quality**: A+ candidates only—no compromises
- **Diversity is strength**: Actively seek different backgrounds, perspectives, thinking styles
- **HR pre-screening**: Assume non-qualified candidates are already filtered out before this process

## Initial Team Building

### First 2 Hires (Lead Dev Personally)

The lead dev hired the first 2 engineers personally to establish team culture:

1. **One senior engineer** - To co-lead, set technical standards, mentor future hires
2. **One mid-level engineer** - To balance team, show juniors there's a growth path

**Criteria for these hires**:
- Technical excellence (can solve complex problems independently)
- Cultural fit (values collaboration, learning, quality)
- Growth mindset (curious, teaches others, admits mistakes)
- Communication skills (clear, respectful, constructive)

**After first 2 hires**: Hiring is **delegated to the team**. The team you build is the team you work with—ownership creates investment.

## 3-Round Hiring Process

### Overview

Every candidate (after first 2) goes through 3 rounds:

1. **Technical depth interview** (2 engineers)
2. **Domain fit & learning interview** (Lead dev + PO)
3. **Pairing under pressure** (Lead dev observes)

**Standard**: Must pass with A's in all three rounds, or they're out. No "maybes."

---

### Round 1: Technical Depth & System Design

**Format**: 60-minute technical interview

**Interviewers**: 2 engineers of different seniority levels
- At least one has overlapping background with candidate (e.g., backend interviewing backend)
- Example pairs: Senior + Mid, Senior + Junior, Mid + Junior

**Purpose**: Assess system design skills, engineering fundamentals, depth of knowledge

**Structure**:
- **10 min**: Candidate background, recent projects
- **40 min**: System design problem
  - Example: "Design a URL shortener like bit.ly"
  - Example: "Design a real-time chat system"
  - Whiteboard or collaborative doc
  - Looking for: Requirements gathering, trade-offs, scalability, data modeling, API design
- **10 min**: Technical Q&A (algorithms, data structures, domain expertise)

**Evaluation criteria**:
- ✅ **System thinking**: Breaks down complex problems systematically
- ✅ **Trade-off awareness**: "We could use X, but Y is better because..."
- ✅ **Asks clarifying questions**: Doesn't make assumptions
- ✅ **Communicates clearly**: Can explain technical concepts
- ✅ **Depth in specialty**: Strong knowledge in their domain
- ✅ **Breadth**: Aware of related technologies, industry patterns

**Red flags**:
- ❌ Doesn't ask questions (assumes requirements)
- ❌ Jumps to solution without analysis
- ❌ Overengineers or underengineers
- ❌ Can't explain trade-offs
- ❌ Defensive when questioned
- ❌ Talks down about previous teams

**Outcome**: Pass (A) or Fail (B or below)

---

### Round 2: Domain Fit & Learning Willingness

**Format**: 45-minute behavioral/domain interview

**Interviewers**: Lead dev + Product Owner

**Purpose**: Assess cultural fit, willingness to learn the business, domain understanding

**Structure**:
- **15 min**: Tell us about a time when...
  - You had to learn a new domain quickly
  - You disagreed with a technical decision
  - You made a mistake that impacted the team
  - You helped a teammate grow
- **20 min**: Domain discussion
  - PO explains current product/business
  - Candidate asks questions about domain, users, constraints
  - Lead dev assesses: Are they listening? Do they care? Do they ask good questions?
- **10 min**: Candidate asks questions about team, culture, challenges

**Evaluation criteria**:
- ✅ **Curiosity**: Asks thoughtful questions about the domain
- ✅ **Listens to experts**: Respects PO's domain knowledge
- ✅ **Willingness to learn**: "I don't know X, but I'll learn it"
- ✅ **Collaborative mindset**: Uses "we" not "I"
- ✅ **Growth mindset**: Talks about learning from failures
- ✅ **Cultural fit**: Values match team (quality, collaboration, respect)

**Red flags**:
- ❌ Not interested in the domain ("I just code what I'm told")
- ❌ Doesn't ask questions (disengaged)
- ❌ Talks over PO or lead dev
- ❌ Blames previous teams for failures
- ❌ Arrogant ("I already know everything")
- ❌ Only cares about tech stack, not product

**Lead dev's assessment**:
- "Would this person uplift the team or drag it down?"
- "Do they value learning the business, or just writing code?"
- "Can I trust them to make decisions aligned with our values?"

**Outcome**: Pass (A) or Fail (B or below)

---

### Round 3: Pairing Under Pressure (The Decider)

**Format**: 90-minute live coding pairing session

**Setup**: Candidate pairs with an existing team member (match by level—see Pairing Matrix below)

**Observer**: Lead dev watches **behavior**, not just code

**Problem**: Toy implementation (not production code)
- Examples: Build a chess game, booking system, task manager
- **Not about finishing**—about behavior under pressure and collaboration style

**Pressure Protocol**: Keyboard switching with decreasing intervals
- **First 20 min**: Switch keyboard every 5 minutes (comfortable)
- **Next 20 min**: Switch keyboard every 3 minutes (moderate pressure)
- **Next 20 min**: Switch keyboard every 2 minutes (high pressure)
- **Final 20 min**: Switch keyboard every 1 minute (intense pressure)
- **Last 10 min**: Debrief & reflection

**Pairing Matrix** (Who pairs with candidate?):

| Candidate Level | Pairs With | Lead Dev Looking For |
|---|---|---|
| **Senior** | Junior engineer | Does the senior **listen** and ask clarifying questions? Do they guide without overrunning the junior? Are they patient? |
| **Junior** | Senior engineer | Is the junior **willing to accept they don't know much yet**? Do they ask "how?" and "why?" questions? Are they humble? |
| **Mid-Level** | Senior OR Junior | Balanced behavior: Can lead when needed, can follow when appropriate. Adapts to pair. |

**What Lead Dev Observes**:

For **Senior Candidates**:
- ✅ **Listens**: Doesn't steamroll the junior partner
- ✅ **Asks questions**: "What do you think we should do next?"
- ✅ **Teaches**: Explains concepts when partner is stuck
- ✅ **Patience**: Stays calm even under 1-minute switching pressure
- ✅ **Collaboration**: Treats junior as equal, respects their ideas
- ❌ **Red flag**: Takes over, types fast without explaining, dismisses junior's ideas

For **Junior Candidates**:
- ✅ **Asks questions**: "Why did we choose this approach?" "How does X work?"
- ✅ **Humble**: "I don't know this—can you explain?"
- ✅ **Eager to learn**: Takes notes (mentally), tries new concepts
- ✅ **Handles pressure**: Doesn't freeze under 1-minute switches
- ✅ **Accepts guidance**: Listens to senior's suggestions
- ❌ **Red flag**: Pretends to know, doesn't ask questions, defensive

For **Mid-Level Candidates**:
- ✅ **Balanced**: Can lead or follow depending on situation
- ✅ **Self-aware**: Knows when to ask for help
- ✅ **Adapts**: Adjusts to pair's seniority
- ✅ **Communicates**: Explains thinking, listens to feedback
- ❌ **Red flag**: Too passive (always follows) or too dominant (always leads)

**Pressure Response**:
- How does candidate handle 1-minute keyboard switches?
- Do they stay calm, or do they panic?
- Do they communicate more ("we need to focus") or shut down?
- Do they blame the partner, or do they collaborate?

**Post-Pairing Debrief** (10 min):
- Lead dev asks: "How did that feel?"
- "What was challenging?"
- "What would you do differently?"
- "How did you and your pair work together?"

**Evaluation Criteria**:
- ✅ **Collaboration**: Works *with* pair, not against or parallel
- ✅ **Communication**: Narrates thinking, listens actively
- ✅ **Pressure handling**: Stays calm and focused under stress
- ✅ **Humility**: Admits when stuck, asks for help
- ✅ **Teaching/learning**: Teaches (if senior) or learns (if junior)
- ✅ **Behavior matches level**: Senior guides, junior asks, mid balances

**Lead Dev's Final Decision**:
- "Do I want this person on the team?"
- "Will they make the team better or worse?"
- "Do they embody our values (quality, collaboration, respect)?"
- "Can I trust them to pair well with anyone on the team?"

**Outcome**: Hire (A) or No Hire (B or below)

---

## Scoring & Decision

### Scoring System

Each round is graded:
- **A**: Excellent, hire
- **B**: Acceptable, but not A+
- **C**: Below standard
- **F**: Fail

**Requirement**: Candidate must score **A** in all three rounds to receive an offer.

**No compromises**: "B is not good enough" - B means no hire.

### Final Decision

- **All A's**: Offer extended
- **Any B or below**: No offer, with feedback

**Feedback** (for no-hire):
- Constructive, specific, actionable
- Example: "You showed strong technical skills (Round 1: A), but during pairing, you tended to take over rather than collaborate with your partner. We're looking for seniors who can guide juniors without overrunning them."

## Post-Hire: Onboarding

Once hired:
- **Buddy system**: Paired with a senior for first 2 weeks
- **Slow ramp-up**: Start with smaller tasks, build to full stories
- **Culture immersion**: Attend retros, pairing sessions, planning
- **Feedback loops**: Weekly 1-on-1s with lead dev for first month

## Team Growth & Turnover

### Growth

- **Team size cap**: 10 engineers (excluding testers)
- **Growth trigger**: Velocity consistently exceeds capacity for 3+ sprints
- **Hiring cadence**: 1-2 engineers per quarter (sustainable growth)

### Turnover

**Expected after 5+ months**:
- Better offers elsewhere
- Life changes (relocation, family, etc.)
- Career growth beyond team scope

**When someone leaves**:
- **Blameless**: "People grow, and that's good"
- **Knowledge transfer sprint**: Departing engineer pairs with successor
- **Document expertise**: ADRs, runbooks, system docs
- **Celebrate contributions**: Retro focused on "what did we learn from X?"

**Backfill process**: Repeat 3-round hiring, team involved

## Diversity & Inclusion

### Lead Dev's Philosophy

> "Diversity creates resilience and better products. A room full of people who think like me will miss what I miss."

### Hiring for Diversity

**Actively seek**:
- Different cultural backgrounds
- Different educational paths (CS degree, bootcamp, self-taught)
- Different communication styles (introverts, extroverts)
- Different specializations (backend, frontend, devops, security, etc.)
- Different perspectives (junior-to-senior pipeline, career changers)

**Red flag**: Team starts to look homogeneous (all same background, all same university, all same gender, etc.)

**Action**: Adjust sourcing, partner with diverse hiring channels

### Inclusive Hiring

- **Structured interviews**: Same questions for all candidates (fair comparison)
- **Blind resume review**: Focus on skills, not schools or names
- **Diverse interview panels**: Not all senior white men interviewing (representation)
- **Accessible process**: Accommodations for disabilities, time zones, etc.

## Tester Involvement

### Testers in Hiring

- **Round 1**: Testers can be one of the 2 interviewers (if candidate is QA/test automation)
- **Round 2**: Testers join for domain discussion (product quality perspective)
- **Round 3**: Testers can participate in pairing session as observer or pair

### Testers in Team Pairing

- **Encouraged**: Testers pair with developers as navigators
- **Purpose**: Cross-functional understanding, quality mindset
- **Example**: Tester navigates while developer implements—tester guides on edge cases, error handling, test scenarios

## Summary

**Philosophy**: A+ candidates only—team quality is non-negotiable.

**Process**: 3 rounds (Technical, Domain/Fit, Pairing Under Pressure)

**Standard**: Must score A in all rounds.

**Pairing test**: The decider—behavior under pressure matters more than code.

**Diversity**: Actively sought—resilience and better products.

**Lead dev's role**: Hired first 2, then delegated to team—but always observes Round 3.

**Outcome**: A team that values collaboration, quality, learning, and respect.
