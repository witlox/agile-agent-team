# Profile Restructure: Compositional Agent Architecture

**Date**: February 2026
**Status**: ✅ Implemented

## Overview

This document describes the major architectural refactor that separates agent definition into orthogonal dimensions: seniority, specialization, and personality.

## Motivation

**Before**: Monolithic profiles like `dev_sr_devops.md` mixed seniority + specialization + personality, making it hard to:
- Add new specializations (had to duplicate seniority traits)
- Experiment with seniority changes (rewrite entire profile)
- Scale team diversity (N personalities × M specializations × 3 seniorities = too many files)

**After**: Compositional profiles where agents are defined as:
```
Agent = Seniority + Specialization(s) + Personality + Role + Demographics
```

## New Directory Structure

```
team_config/
├── 00_base/
│   └── base_agent.md                    # Universal behavior
├── 01_role_archetypes/
│   ├── developer.md                     # Developer responsibilities
│   ├── tester.md                        # Tester responsibilities
│   └── leader.md                        # Leadership overlay
├── 02_seniority/                        # NEW: Behavioral maturity
│   ├── junior.md                        # 0-2 years: learning, questions, mistakes
│   ├── mid.md                           # 2-5 years: independence, emerging leadership
│   └── senior.md                        # 5+ years: architecture, mentorship, domain expertise
├── 03_specializations/                  # NEW: Technical expertise (20 files)
│   ├── backend.md
│   ├── frontend.md
│   ├── devops.md
│   ├── networking.md
│   ├── security.md
│   ├── database.md
│   ├── mobile_ios.md
│   ├── mobile_android.md
│   ├── embedded.md
│   ├── systems_programming.md
│   ├── machine_learning.md
│   ├── data_engineering.md
│   ├── cloud_architecture.md
│   ├── api_design.md
│   ├── ui_ux.md
│   ├── performance_optimization.md
│   ├── test_automation.md
│   ├── distributed_systems.md
│   ├── blockchain.md
│   └── accessibility.md
├── 04_domain_knowledge/                 # NEW: Product/industry context
│   ├── 00_saas_project_management.md    # TaskFlow product (all agents)
│   ├── 01_junior_domain.md              # Basic workflows, customer context
│   ├── 02_mid_domain.md                 # Integration patterns, edge cases
│   └── 03_senior_domain.md              # Historical incidents, compliance, strategy
└── 05_individuals/                      # NEW: Personality only (10 files)
    ├── jamie_rodriguez.md               # Latinx, non-binary, cautious, thorough
    ├── alex_chen.md                     # Chinese-American, confident, direct
    ├── priya_sharma.md                  # Indian, analytical, diplomatic
    ├── marcus_okafor.md                 # Nigerian, enthusiastic, collaborative
    ├── elena_volkov.md                  # Russian, pragmatic, blunt
    ├── yuki_tanaka.md                   # Japanese, quiet, observant
    ├── maria_santos.md                  # Brazilian, outgoing, creative
    ├── ahmed_hassan.md                  # Egyptian, methodical, patient
    ├── sophie_dubois.md                 # French, perfectionist, critical
    └── jordan_kim.md                    # Korean-American, fast-paced, innovative
```

## Composition Order

Agents are composed in this order:

1. **Base** (`00_base/base_agent.md`) — Universal team member behavior
2. **Role Archetype** (`01_role_archetypes/{developer,tester,leader}.md`) — Role responsibilities
3. **Seniority** (`02_seniority/{junior,mid,senior}.md`) — Behavioral maturity
4. **Specializations** (`03_specializations/*.md`) — Technical expertise (multiple allowed)
5. **Domain Knowledge** (`04_domain_knowledge/*.md`) — Cumulative by seniority
6. **Personality** (`05_individuals/{name}.md`) — Individual behavioral traits
7. **Demographics** — Pronouns, cultural background (from config)

## Configuration Example

**Old structure** (monolithic):
```yaml
agents:
  dev_sr_devops:
    model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
    temperature: 0.7
    max_tokens: 3072
```

**New structure** (compositional):
```yaml
agents:
  priya_senior_devops:
    name: "Priya Sharma (Senior DevOps Specialist)"
    individual: priya_sharma           # Personality
    seniority: senior                  # Behavioral maturity
    specializations: [devops, cloud_architecture]  # Technical expertise
    role_archetype: developer          # Role
    demographics:
      pronouns: "she/her"
      cultural_background: "Indian"
    model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
    temperature: 0.7
    max_tokens: 3072
```

## Domain Knowledge Layering

Domain knowledge is cumulative by seniority:

- **Juniors** load: `00_saas + 01_junior` (basics only)
- **Mids** load: `00_saas + 01_junior + 02_mid` (+ edge cases, integration patterns)
- **Seniors** load: `00_saas + 01_junior + 02_mid + 03_senior` (+ incidents, compliance, strategy)

This models realistic knowledge accumulation over years in an industry.

## Benefits

### Reusability
- 3 seniority profiles × 20 specializations × 10 personalities = 600 possible agents
- Without duplication: only 33 files to maintain

### Experimentation
- "What if Jamie were mid-level?" → change one line in config.yaml
- "Add a mobile security specialist" → combine `mobile_ios + security`
- "Test all-senior team" → change seniority field for all agents

### Diversity
- 10 culturally diverse personalities with authentic traits
- Configurable demographics (pronouns, cultural background)
- Communication styles: introvert/extrovert, direct/diplomatic, patient/impatient

### Realism
- Domain knowledge grows with seniority (just like real engineers)
- Specializations are deep technical profiles (150+ lines each)
- Personalities reflect actual engineering team diversity

## Code Changes

### `src/agents/base_agent.py`
- **AgentConfig**: Added `individual`, `seniority`, `specializations`, `role_archetype`, `demographics`
- **`_load_prompt()`**: Complete rewrite to support layered composition
- **`_load_prompt_legacy()`**: Backward compatibility for old structure

### `src/agents/agent_factory.py`
- **`create_all_agents()`**: Detects new vs. old structure automatically
- **`_create_agent_config_new()`**: Creates AgentConfig from new structure

### `config.yaml`
- **agents section**: Migrated all 11 agents to new structure
- Shows diverse team: 2 juniors, 2 mids, 7 seniors (includes 3 leads)

### `team_config/02_individuals/dev_lead.md`
- Clarified dev lead spends **70-80% coding**, 20-30% coordination

## Verification

```bash
# All tests pass
pytest tests/ -v
# 15 passed

# End-to-end test works
MOCK_LLM=true python -m src.orchestrator.main --sprints 1 --output /tmp/test --db-url mock://
# ✓ Loaded 11 agents with new structure
# ✓ Sprint completed successfully
```

## Migration Guide

To add a new agent:

1. **Choose personality** from `05_individuals/` (or create new)
2. **Choose seniority**: junior | mid | senior
3. **Choose specializations**: 1-3 from `03_specializations/`
4. **Choose role**: developer | tester | leader (or combine: "developer+leader")
5. **Add to config.yaml**:
```yaml
agents:
  new_agent_id:
    name: "Full Name"
    individual: personality_file
    seniority: junior
    specializations: [backend, security]
    role_archetype: developer
    demographics:
      pronouns: "they/them"
      cultural_background: "Background"
    model: "model-id"
    temperature: 0.7
    max_tokens: 2048
```

## Files Created/Modified

**Created** (37 files):
- 3 seniority profiles
- 20 specialization profiles
- 4 domain knowledge layers
- 10 personality profiles

**Modified** (5 files):
- `src/agents/base_agent.py` — New composition logic
- `src/agents/agent_factory.py` — New config parsing
- `config.yaml` — Agent definitions migrated
- `team_config/02_individuals/dev_lead.md` — Clarified coding time
- `docs/PROFILE_RESTRUCTURE.md` — This document

**Unchanged**:
- All tests still pass (backward compatible)
- Research hypotheses unchanged
- Experiment semantics unchanged

## Future Work

- Create more personalities (target: 20)
- Add more specializations (mobile, ML, security variations)
- Experiment with team composition (all-junior, all-senior, etc.)
- A/B test seniority effects on velocity

---

**This restructure enables systematic experimentation on team composition, seniority effects, and specialization diversity at scale.**
