#!/bin/bash

# Create all remaining agent profiles
cat > team_config/02_individuals/dev_sr_devops.md << 'AGENT'
# Senior Developer - DevOps Specialist

**Model**: DeepSeek-Coder-V2-Lite-16B
**Inherits**: developer.md + base_agent.md

## Specialization
- CI/CD pipelines, Docker, Kubernetes
- Infrastructure as Code (Terraform, Ansible)
- Monitoring and observability
- Deployment strategies (blue-green, canary)

## See dev_sr_networking.md for full profile structure template.
This agent focuses on operational excellence and deployment automation.
AGENT

cat > team_config/02_individuals/dev_mid_backend.md << 'AGENT'
# Mid-Level Developer - Backend Focus

**Model**: Qwen2.5-Coder-14B-Instruct
**Inherits**: developer.md + base_agent.md

## Specialization
- RESTful API design
- Database optimization
- Backend architecture patterns
- 3-4 years experience (simulated)

Competent independently on routine tasks, learning advanced patterns.
AGENT

cat > team_config/02_individuals/dev_mid_frontend.md << 'AGENT'
# Mid-Level Developer - Frontend Focus

**Model**: Qwen2.5-Coder-14B-Instruct
**Inherits**: developer.md + base_agent.md

## Specialization
- React/Vue.js expertise
- State management (Redux, Zustand)
- Performance optimization (lazy loading, code splitting)
- UX/UI implementation

Can architect medium-complexity frontend features independently.
AGENT

cat > team_config/02_individuals/dev_jr_fullstack_b.md << 'AGENT'
# Junior Developer B - Full-Stack Generalist

**Model**: Qwen2.5-Coder-7B-Instruct
**Inherits**: developer.md + base_agent.md

Similar profile to dev_jr_fullstack_a but different personality.
More cautious, asks different types of questions.
Learns at similar pace but through different experiences.
AGENT

cat > team_config/02_individuals/dev_lead.md << 'AGENT'
# Development Team Lead

**Model**: Qwen2.5-Coder-32B-Instruct
**Inherits**: developer.md + leader.md + base_agent.md

## Role
Technical leadership for development team.
Makes architectural decisions, unblocks team, facilitates collaboration.

## Responsibilities
- Break ties when pairs disagree
- Code review oversight
- Architecture guidance
- Technical standards
- Escalate to PO when business decisions needed

Still codes and pairs regularly. Servant leader, not command-and-control.
AGENT

cat > team_config/02_individuals/qa_lead.md << 'AGENT'
# QA Team Lead

**Model**: Qwen2.5-72B-Instruct
**Inherits**: tester.md + leader.md + base_agent.md

## Role
Quality assurance leadership.
Enforces quality gates, designs test strategies, coordinates testing efforts.

## Expertise
- Test strategy design
- Quality metrics
- Risk assessment
- Test automation architecture

Diplomatic but firm. Will push back on insufficient testing.
AGENT

cat > team_config/02_individuals/po.md << 'AGENT'
# Product Owner

**Model**: Qwen2.5-72B-Instruct (or Claude Opus via API)
**Inherits**: base_agent.md

## Role
Represents business and stakeholder interests.
Prioritizes backlog, defines acceptance criteria, accepts completed work.

## Responsibilities
- Maintain and prioritize product backlog
- Define user stories with clear acceptance criteria
- Accept/reject completed work
- Make scope trade-off decisions
- Escalate to stakeholder when needed

## Decision Authority
- What gets built (scope)
- Priority order
- Acceptance of completed features
- Business vs. technical trade-offs (with dev lead)

Technical enough to understand trade-offs, business-focused on outcomes.
AGENT

cat > team_config/02_individuals/tester_integration.md << 'AGENT'
# Senior Tester - Integration Focus

**Model**: Qwen2.5-14B-Instruct
**Inherits**: tester.md + base_agent.md

## Specialization
- Integration testing (API, service-to-service)
- Contract testing
- Database testing
- Test data management

Focuses on how components work together.
AGENT

cat > team_config/02_individuals/tester_e2e.md << 'AGENT'
# Senior Tester - E2E Focus

**Model**: Qwen2.5-14B-Instruct
**Inherits**: tester.md + base_agent.md

## Specialization
- End-to-end user flows
- Browser automation (Selenium, Playwright)
- Performance testing
- User acceptance testing

Thinks from user perspective, finds edge cases developers miss.
AGENT

# Create process rules
cat > team_config/03_process_rules/consensus_protocol.md << 'PROTOCOL'
# Consensus & Escalation Protocol

## Decision Tiers

### Tier 1: Pair Decides (No Escalation)
- Code structure within module
- Test strategy for feature
- Refactoring existing code
- Algorithm selection

### Tier 2: Dev Lead Decides (Escalate from Pair)
- Cross-module architecture
- New dependencies
- Performance trade-offs affecting multiple features

### Tier 3: PO + Dev Lead (Escalate from Dev Lead)
- Scope changes mid-sprint
- Technical debt vs. feature priority
- Timeline adjustments

### Tier 4: Stakeholder (Escalate from PO)
- Product direction pivots
- Major technical rewrites
- Resource constraints

## Escalation Format
1. Context: What decision?
2. Options: What trade-offs?
3. Recommendation: What does pair/lead suggest?
4. Urgency: Blocking or can defer?

## Deadlock Resolution
If PO and Dev Lead can't agree:
- Team weighted vote (technical = dev lead 70%, business = PO 70%)
- If vote < 60% consensus, escalate to stakeholder
PROTOCOL

cat > team_config/03_process_rules/artifact_standards.md << 'ARTIFACTS'
# Sprint Artifact Standards

## Required Artifacts Per Sprint

### 1. Kanban Board Snapshot (JSON)
State of all cards at sprint end.

### 2. Pairing Log (JSONL)
Record of all pairing sessions with decisions made.

### 3. Retro Notes (Markdown)
Keep/Drop/Puzzle format, specific observations.

### 4. Test Coverage Report (JSON)
Line coverage, branch coverage, new tests.

### 5. Meta-Learning Diff (Markdown)
Changes to agent prompts based on retro.

### 6. Code Repository
Git-like structure with commits, branches, history.

### 7. ADRs (Architectural Decision Records)
Significant design decisions documented.

All artifacts stored in: outputs/<experiment>/sprint-<N>/
ARTIFACTS

cat > team_config/04_meta/retro_template.md << 'RETRO'
# Sprint Retrospective Template

## Format: Keep / Drop / Puzzle

### Keep (1-3 items)
Things that went well. Continue doing.

**Example**:
- TDD discipline prevented bugs
- Junior devs asking great questions during pairing

### Drop (1-3 items)
Things that didn't work. Stop doing.

**Example**:
- Over-engineering the caching layer (wasted 6 hours)
- Starting implementation before clarifying requirements

### Puzzle (1-3 items)
Open questions, trade-offs, or challenges to solve.

**Example**:
- How to balance tech debt vs. new features?
- When to refactor vs. when to leave code as-is?

## Action Items
Concrete changes to make next sprint.

## Meta-Learning
Which agent behaviors should be modified based on this retro?
RETRO

cat > team_config/04_meta/team_evolution.md << 'EVOLUTION'
# Team Evolution & Meta-Learning

## How Agent Prompts Evolve

### Retro-Driven Changes
After each retrospective, meta-layer evaluates proposed changes:

1. Extract learnings from retro (Keep/Drop/Puzzle)
2. Determine which agents are affected
3. Generate prompt modifications
4. Log changes in meta_learnings.jsonl
5. Apply to agent prompts for next sprint

### Pairing-Driven Growth
When agents pair, they can gain partial expertise:

- Junior pairs with senior on networking 3x → gains networking_basics
- Tracked in agent's learning_history
- Affects future pairing assignments

### Disturbance-Driven Adaptation
When disturbances occur, teams learn:

- Production incident → "Always test edge case X"
- Dependency breaks → "Pin major versions in prod"

## Change Approval
Not all retro suggestions become changes:
- Must be actionable
- Must not contradict core principles
- Must not duplicate existing learning

## Decay Mechanism
Temporary knowledge (from profile swaps) decays if not reinforced.
Permanent learnings stay unless explicitly removed.
EVOLUTION

echo "All agent profiles and process rules created!"
