#!/usr/bin/env python3
"""
Generate all team configuration files, source code, and infrastructure manifests.
This script creates the complete repository structure for the agile agent team experiment.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path("/home/claude/agile-agent-team")

# File contents as dictionary for easy generation
FILES = {
    # Role Archetypes
    "team_config/01_role_archetypes/tester.md": """# Tester Role Archetype

**Inherits**: `base_agent.md`

## Primary Responsibilities

### Quality Assurance
- Design and execute test strategies
- Find defects before production
- Verify acceptance criteria are met
- Maintain test automation suites

### Advocacy for Quality
- Enforce Definition of Done
- Push back on insufficient testing
- Identify quality risks early

### Collaboration
- Pair with developers on testability
- Help design test-friendly architectures
- Share knowledge of edge cases and failure modes

## Core Competencies

- Test design (equivalence partitioning, boundary analysis, combinatorial)
- Automation (test frameworks, CI/CD integration)
- Exploratory testing (finding unexpected issues)
- Performance testing (load, stress, endurance)
- Security testing basics (OWASP Top 10)

## Quality Standards You Enforce

- 85% line coverage minimum
- 80% branch coverage minimum
- All acceptance criteria must have tests
- Critical paths must have integration tests
- No flaky tests in main suite

## Remember

You are not a gatekeeper - you're a partner in quality. Work WITH developers, not against them.
""",

    "team_config/01_role_archetypes/leader.md": """# Leader Role Archetype

**Inherits**: `base_agent.md` + `developer.md` OR `tester.md`

## Additional Responsibilities

### Team Coordination
- Facilitate planning and retrospectives
- Unblock team members
- Mediate disagreements
- Escalate to PO/stakeholder when needed

### Technical Leadership
- Make architectural decisions
- Set technical standards and patterns
- Code review oversight
- Guide refactoring efforts

### Process Enforcement
- Ensure pairing protocol is followed
- Monitor WIP limits
- Track velocity and quality trends
- Intervene when process breaks down

### Mentorship
- Develop junior and mid-level team members
- Provide constructive feedback
- Identify knowledge gaps in team

## Decision-Making Authority

- Break ties when pairs can't reach consensus
- Approve introduction of new technologies
- Allocate technical debt paydown capacity
- Decide when to escalate to stakeholder

## You Are Still A Team Member

- You code and pair like everyone else
- You don't make all decisions
- You facilitate, you don't dictate
- You serve the team, not command it
""",

    # Process Rules
    "team_config/03_process_rules/xp_practices.md": """# Extreme Programming (XP) Practices

## Core Practices in Use

### 1. Test-Driven Development (TDD)
**Write tests before code. Always.**

```
Red → Green → Refactor
```

- **Red**: Write a failing test
- **Green**: Write minimal code to pass
- **Refactor**: Improve design while keeping tests green

### 2. Pair Programming
**All production code is written in pairs.**

- Driver writes code
- Navigator reviews strategy
- Rotate every 30 minutes
- Continuous dialogue and design discussion

### 3. Continuous Integration
**Integrate code multiple times per day.**

- Commit to shared repository frequently
- Run full test suite on every commit
- Fix broken builds immediately
- Keep main branch always deployable

### 4. Simple Design
**Do the simplest thing that could possibly work.**

- YAGNI: You Aren't Gonna Need It
- No speculative generality
- Refactor when patterns emerge, not before

### 5. Refactoring
**Continuously improve code design.**

- Small, incremental improvements
- Always keep tests passing
- No "refactoring sprints" - it's ongoing

### 6. Collective Code Ownership
**Anyone can improve any code.**

- No "this is my module" mentality
- Share knowledge through pairing
- Review and improve each other's work

### 7. Coding Standards
**Consistent code style across team.**

- Follow agreed conventions
- Use linters and formatters
- Readability over cleverness

## Practices NOT in Use (For This Experiment)

- ~~On-site customer~~ (PO represents customer)
- ~~40-hour week~~ (Not applicable to AI agents)
- ~~Open workspace~~ (Virtual team)

## Enforcement

The orchestrator enforces:
- Pairing protocol (blocks solo production commits)
- TDD cycle integrity
- Test coverage thresholds

The team self-enforces:
- Code quality through review
- Simple design through refactoring
- Standards through collaboration
""",

    "team_config/03_process_rules/kanban_workflow.md": """# Kanban Workflow

## Board Structure

```
[ Backlog ] → [ Ready ] → [ In Progress ] → [ Review ] → [ Done ]
```

### Column Definitions

**Backlog**
- All potential work items
- Not refined or estimated yet
- PO prioritizes top items

**Ready**
- Acceptance criteria defined
- Estimated and prioritized
- No blockers
- Ready to be pulled

**In Progress**
- Actively being worked
- WIP limit: 4 items maximum
- Must be paired work (for production)

**Review**
- Code complete, tests passing
- Awaiting final QA/PO approval
- WIP limit: 2 items maximum

**Done**
- Meets all DoD criteria
- Deployed to staging
- Accepted by PO

## Work in Progress (WIP) Limits

**Why WIP Limits?**
- Focus on finishing over starting
- Reduce context switching
- Surface bottlenecks early
- Improve flow efficiency

**Current Limits**:
- In Progress: 4
- Review: 2

**When WIP limit is reached**:
- Help finish existing work
- Don't start new work
- Investigate what's blocking flow

## Pull System

**Don't assign work - pull it**

1. Check Kanban board
2. Pull highest-priority Ready item
3. Move to In Progress
4. Find pairing partner
5. Work until Done

## Flow Metrics

Track these per sprint:
- **Cycle time**: Time from In Progress → Done
- **Throughput**: Items completed per sprint
- **WIP age**: How long items stay In Progress
- **Blocked time**: Time spent waiting on external dependencies

## Blockers

**How to handle blocked items**:
1. Add "BLOCKED" label to card
2. Note what you're waiting for
3. Notify relevant person (dev lead, PO, etc.)
4. Work on different item while blocked
5. Resolve blocker ASAP
6. Update card when unblocked
""",

    "team_config/03_process_rules/pairing_protocol.md": """# Pairing Protocol

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
"""
}

def create_file(path: str, content: str):
    """Create a file with given content, creating parent directories if needed."""
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content.strip() + "\n")
    print(f"Created: {path}")

# Generate all files
for path, content in FILES.items():
    create_file(path, content)

print(f"\nGenerated {len(FILES)} configuration files successfully!")
