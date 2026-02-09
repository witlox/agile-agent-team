# E2E (End-to-End) Tests

## Overview

E2E tests run complete multi-sprint workflows to verify the entire system integration. These tests are **manual** (not run automatically) because they:

- Take 2-5 minutes to complete
- Write to real file system locations
- Start services (metrics server on port 8080)
- Create workspace artifacts

## Running E2E Tests

### Run all E2E tests:
```bash
pytest tests/integration/test_e2e_sprint_workflow.py -v -s -m e2e
```

### Run specific E2E test:
```bash
pytest tests/integration/test_e2e_sprint_workflow.py::test_e2e_three_sprint_workflow -v -s
```

### Run regular tests (excluding E2E):
```bash
pytest tests/ -m "not e2e"
```

## E2E Test Suite

### `test_e2e_three_sprint_workflow`
**Duration:** ~3-5 minutes
**Purpose:** Comprehensive 3-sprint workflow verification

**Verifies:**
- ✅ Sprint directory structure (3 sprint folders)
- ✅ Kanban state snapshots (ready/in_progress/review/done)
- ✅ Pairing logs (session records with driver/navigator)
- ✅ Retrospective outputs (keep/drop/puzzle in Markdown)
- ✅ Meta-learning entries (JSONL storage)
- ✅ Final report aggregation (velocity, features, sessions)
- ✅ Workspace artifacts (if code generation enabled)

**Outputs:**
- Kanban: `{output}/sprint-0N/kanban.json`
- Pairing: `{output}/sprint-0N/pairing_log.json`
- Retro: `{output}/sprint-0N/retro.md`
- Report: `{output}/final_report.json`
- Meta: `team_config/07_meta/meta_learnings.jsonl`
- Workspace: `/tmp/agent-workspace/sprint-0N/us-NNN/`

### `test_e2e_sprint_workflow_kanban_state_transitions`
**Duration:** ~1-2 minutes
**Purpose:** Verify kanban cards move through states correctly

**Checks:**
- Cards start in 'ready'
- Cards move to 'in_progress' during development
- Cards move to 'review' after pairing
- Cards move to 'done' after QA approval
- No duplicate card IDs across columns

### `test_e2e_sprint_workflow_pairing_diversity`
**Duration:** ~3-5 minutes
**Purpose:** Verify pair rotation ensures diverse pairing

**Checks:**
- Multiple unique pairs form across 3 sprints
- Navigators rotate (not always the same)
- Different agents get paired together

## Test Configuration

E2E tests use:
- **Config:** `config.yaml` (standard config)
- **Database:** `mock://` (in-memory)
- **Backlog:** Dynamically created test backlog
- **Agents:** Full 16-agent team from config
- **Mode:** Mock mode (no real LLM calls)

## File System Impact

E2E tests create files in:

1. **Output directory** (test-specific temp dir):
   - `sprint-01/kanban.json`
   - `sprint-01/pairing_log.json`
   - `sprint-01/retro.md`
   - `sprint-02/...`
   - `sprint-03/...`
   - `final_report.json`

2. **Team config** (shared):
   - `team_config/07_meta/meta_learnings.jsonl` (appends learnings)

3. **Workspace** (shared):
   - `/tmp/agent-workspace/sprint-0N/us-NNN/` (code artifacts)

**Cleanup:** Output dir is cleaned up automatically (pytest tmp_path). Shared locations may accumulate test data.

## Troubleshooting

### Port 8080 already in use
The metrics server tries to start on port 8080. If another process is using it:
```bash
lsof -i :8080
kill <PID>
```

### Existing meta_learnings.jsonl
E2E tests append to the existing file. To start fresh:
```bash
rm team_config/07_meta/meta_learnings.jsonl
```

### Workspace artifacts accumulate
Clean old workspace artifacts:
```bash
rm -rf /tmp/agent-workspace/
```

## Example Output

```
$ pytest tests/integration/test_e2e_sprint_workflow.py::test_e2e_three_sprint_workflow -v -s -m e2e

test_e2e_three_sprint_workflow PASSED

======================================================================
E2E TEST SUMMARY
======================================================================
✓ 3 sprints completed
✓ Kanban snapshots verified (3 files)
✓ Pairing logs verified (12 total sessions)
✓ Retrospectives verified (3 retro.md files)
✓ Final report verified
✓ Average velocity: 4.3 pts/sprint
✓ Total features: 3
======================================================================
```

## Integration with CI/CD

E2E tests are **not** run in CI/CD pipelines by default. To run in CI:

```yaml
# .github/workflows/e2e.yml
- name: Run E2E tests
  run: pytest tests/integration/test_e2e_sprint_workflow.py -v -m e2e
  timeout-minutes: 10
```

## Performance

| Test | Duration | Sprints | Assertions |
|------|----------|---------|------------|
| `test_e2e_three_sprint_workflow` | 3-5 min | 3 | 50+ |
| `test_e2e_sprint_workflow_kanban_state_transitions` | 1-2 min | 1 | 10+ |
| `test_e2e_sprint_workflow_pairing_diversity` | 3-5 min | 3 | 5+ |

Total E2E suite: **~7-12 minutes**

## Why Mock Mode?

E2E tests use mock mode (`MOCK_LLM=true` or `database_url=mock://`) because:
- **Fast:** No real LLM API calls
- **Deterministic:** Canned responses, repeatable results
- **No cost:** No API usage
- **Reliable:** No network dependencies

Mock mode still exercises:
- All orchestration logic
- Kanban state transitions
- Pairing session flow
- File I/O and serialization
- Sprint lifecycle management

## Future Enhancements

Potential E2E test additions:
- [ ] Test with real vLLM endpoint (requires vLLM server)
- [ ] Test with Anthropic API (requires API key)
- [ ] Test brownfield mode (clone existing repo)
- [ ] Test remote git integration (mock gh/glab CLI)
- [ ] Test disturbance injection (verify impact on velocity)
- [ ] Test profile swapping (verify swap/revert/decay)
- [ ] Test specialist consultant system (max 3 per sprint)
