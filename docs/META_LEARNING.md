# Meta-Learning System

**Date**: February 2026
**Status**: ✅ Implemented (Dynamic Loading)

## Overview

The meta-learning system allows agents to evolve their behavior based on retrospective insights from past sprints. Learnings are stored separately from profile files and injected dynamically at prompt composition time.

## Architecture

### Storage: JSONL Format

Learnings are stored in `team_config/07_meta/meta_learnings.jsonl`:

```json
{"sprint": 1, "agent_id": "priya_senior_devops", "learning_type": "drop", "content": {"text": "Stop merging PRs without integration tests"}, "applied": true}
{"sprint": 2, "agent_id": "jamie_junior_fullstack", "learning_type": "keep", "content": {"text": "Continue asking clarifying questions before implementing"}, "applied": true}
```

### Prompt Composition (Layer 8)

Meta-learnings are the **final layer** in agent prompt composition:

1. Base agent behavior (`00_base/`)
2. Role archetype (`01_role_archetypes/`)
3. Seniority level (`02_seniority/`)
4. Specializations (`03_specializations/`)
5. Domain knowledge (`04_domain_knowledge/`)
6. Personality (`05_individuals/`)
7. Demographics (injected text)
8. **Meta-learnings (dynamic from JSONL)** ← NEW

### Dynamic Loading

```python
# In BaseAgent._load_prompt()
meta_learnings = self._load_meta_learnings(team_config_dir)
if meta_learnings:
    parts.append(meta_learnings)
```

Each agent loads **only their own learnings** by filtering on `agent_id`:

```python
if entry.get("agent_id") == self.config.role_id:
    learnings.append(f"- **Sprint {sprint_num} ({learning_type})**: {text}")
```

### Prompt Injection Format

```
[META-LEARNINGS]
Insights from past retrospectives that should inform your behavior:

- **Sprint 1 (drop)**: Stop merging PRs without integration tests
- **Sprint 2 (keep)**: Continue asking clarifying questions before implementing
- **Sprint 3 (puzzle)**: Need to improve estimation accuracy for API integrations
```

## Retrospective Processing

After each sprint retrospective, learnings are extracted from Keep/Drop/Puzzle items and stored:

```python
async def apply_meta_learning(self, sprint_num: int, retro: Dict):
    # Extract learnings from retro items
    for learning_type in ["keep", "drop", "puzzle"]:
        for item in retro.get(learning_type, []):
            agent_id = item.get("agent", "")
            learning_text = item.get("text", "")

            # Store in JSONL
            entry = {
                "sprint": sprint_num,
                "agent_id": agent_id,
                "learning_type": learning_type,
                "content": {"text": learning_text},
                "applied": True,
            }
            # Append to meta_learnings.jsonl

    # Reload all agent prompts to pick up new learnings
    for agent in self.agents:
        agent.prompt = agent._load_prompt()
```

## Benefits

### 1. Clean Separation
- Base personality files remain pristine and reusable
- Learnings are experiment-specific and don't pollute team_config
- Easy to reset or prune old learnings

### 2. Compositional
- Learnings compose naturally with other prompt layers
- Each agent sees only their own learnings (privacy)
- No file system complexity (just append to JSONL)

### 3. Queryable
- JSONL format makes it easy to analyze learnings
- Can filter by sprint, agent, learning type
- Can implement decay policies (e.g., prune learnings > 10 sprints old)

### 4. Experiment Isolation
- Different experiments can have separate JSONL files
- Learnings don't carry over between experiments (unless explicitly copied)
- Baseline experiments start with clean slate

## Future Enhancements

### Learning Decay
Implement time-based decay for old learnings:

```python
# Only load learnings from last N sprints
current_sprint = get_current_sprint()
if current_sprint - entry["sprint"] <= 10:
    learnings.append(...)
```

### Cross-Agent Learnings
Allow team-wide learnings that all agents inherit:

```json
{"sprint": 5, "agent_id": "*", "learning_type": "team", "content": {"text": "Always run integration tests before merge"}}
```

### Learning Prioritization
Weight learnings by type or sprint recency:

```python
# "drop" learnings (mistakes) have higher priority than "keep"
# Recent learnings appear first in prompt
```

### Approval Workflow
Require human approval for certain learnings before applying:

```json
{"sprint": 3, "agent_id": "jamie_junior_fullstack", "learning_type": "drop", "content": {...}, "applied": false, "requires_approval": true}
```

## Files Modified

- `src/agents/base_agent.py`: Added `_load_meta_learnings()` method and layer 8 composition
- `src/orchestrator/sprint_manager.py`: Refactored `apply_meta_learning()` to use JSONL-only storage
- `team_config/07_meta/meta_learnings.jsonl`: Learning storage (one line per learning)

## Verification

```bash
# Run multi-sprint experiment
MOCK_LLM=true python -m src.orchestrator.main --sprints 5 --output /tmp/test --db-url mock://

# Check learnings were stored
cat team_config/07_meta/meta_learnings.jsonl

# Verify learnings are loaded into prompts
python -c "
from src.agents.base_agent import BaseAgent, AgentConfig
config = AgentConfig(role_id='priya_senior_devops', name='Test', model='x', temperature=0.7, max_tokens=100)
agent = BaseAgent(config, 'mock://')
print('[META-LEARNINGS]' in agent.prompt)  # Should print True
"
```

---

**This system enables realistic team evolution where agents learn from mistakes and successes without polluting the base profile architecture.**
