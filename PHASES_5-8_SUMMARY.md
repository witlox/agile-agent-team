# Phases 5-8: Integrated Code Generation Workflow

**Status**: ✅ Completed
**Tests**: 24/24 passing

## Overview

Implemented a complete code generation workflow that enables agents to produce actual working code instead of just simulating development. The system now supports:

- **Real workspace management** per sprint/story
- **BDD/Gherkin feature generation** from user stories
- **Agentic code implementation** using tool-calling runtimes
- **Test execution with iteration loops**
- **Git commits** for completed work

## Components Implemented

### 1. Workspace Management (`src/codegen/workspace.py`)

```python
WorkspaceManager
  ├── create_sprint_workspace(sprint_num, story_id)
  ├── create_feature_branch(workspace, story_id)
  ├── _init_fresh_repo(workspace)
  └── _clone_repo(workspace)  # For existing projects
```

**Features**:
- Per-sprint/story workspace isolation
- Git initialization with proper config
- Support for cloning existing repos
- Automatic cleanup of old workspaces

### 2. BDD Generator (`src/codegen/bdd_generator.py`)

```python
BDDGenerator
  ├── generate_feature_file(story, workspace)
  ├── generate_step_definitions_template(feature_file)
  └── _build_feature_content(story)  # Gherkin formatting
```

**Features**:
- Converts user stories to Gherkin feature files
- Supports explicit scenarios (Given/When/Then)
- Auto-generates scenarios from acceptance criteria
- Creates pytest-bdd step definition templates

### 3. Test Execution Tools (`src/tools/agent_tools/test_runner.py`)

```python
RunTestsTool
  ├── execute(path, verbose, markers)
  └── _parse_test_summary(output)  # Extracts pass/fail counts

RunBDDTestsTool
  └── execute(feature_file)
```

**Features**:
- Pytest integration with timeout handling
- Test summary parsing (passed/failed/errors)
- BDD feature test execution
- Configurable markers and verbosity

### 4. Code Generation Pairing Engine (`src/agents/pairing_codegen.py`)

```python
CodeGenPairingEngine
  ├── run_pairing_session(pair, task, sprint_num)
  ├── _implement_with_runtime(driver, navigator, task, workspace, feature_file)
  ├── _run_tests_with_iteration(agent, workspace)
  └── _commit_changes(agent, workspace, task)
```

**Workflow**:
1. **Setup**: Create workspace for story
2. **BDD**: Generate Gherkin feature file
3. **Implement**: Driver uses `execute_coding_task()` with tools
4. **Test**: Run tests, iterate on failures (max 3 times)
5. **Commit**: Git commit if tests pass
6. **Update**: Move card to review in Kanban

### 5. Sprint Manager Integration (`src/orchestrator/sprint_manager.py`)

**Auto-detection**:
```python
if self._agents_have_runtimes():
    # Use CodeGenPairingEngine for real code
    self.pairing_engine = CodeGenPairingEngine(...)
else:
    # Fall back to dialogue-based PairingEngine
    self.pairing_engine = PairingEngine(...)
```

**Configuration** (`src/orchestrator/config.py`):
- Added `tools_workspace_root` field
- Added `repo_config` field for cloning existing projects
- Loads from `runtimes.tools.workspace_root` in config.yaml

### 6. Backlog Format Extension (`backlog.yaml`)

**New BDD scenarios field**:
```yaml
stories:
  - id: US-001
    title: "User registration"
    scenarios:
      - name: "Successful registration"
        given:
          - "the system is ready"
          - "no user exists with email user@example.com"
        when:
          - "I register with email user@example.com and password SecurePass123"
        then:
          - "a new user account is created"
          - "the password is hashed with bcrypt"
```

## Configuration

### config.yaml
```yaml
runtimes:
  tools:
    workspace_root: "/tmp/agent-workspace"
    allowed_commands: ["git", "pytest", "python", ...]

models:
  agents:
    alex_senior_networking:
      runtime: "local_vllm"  # or "anthropic"
      tools: ["filesystem", "git", "bash"]
```

## Testing

### New Tests
- `test_sprint_codegen.py`: Sprint manager integration
  - Verifies CodeGenPairingEngine used when runtimes present
  - Verifies PairingEngine fallback when no runtimes
  - Validates workspace manager configuration

### Test Results
```
24 tests passing:
  - 10 unit tests (kanban, runtime, tools)
  - 8 integration tests (pairing, codegen, sprint)
  - 6 qualification tests (agent creation, prompts)
```

## Usage Example

```bash
# Run experiment with code generation
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output results/codegen-test \
  --db-url mock://

# Generated artifacts:
# /tmp/agent-workspace/sprint-01/us-001/
#   ├── features/us-001.feature
#   ├── src/implementation.py
#   ├── tests/test_implementation.py
#   └── .git/
```

## Deployment Modes

### 1. Fully Offline (Local vLLM)
- All agents use `runtime: "local_vllm"`
- XML-based tool calling
- No internet required

### 2. Fully Online (Anthropic)
- All agents use `runtime: "anthropic"`
- Native Claude API tool calling
- Requires ANTHROPIC_API_KEY

### 3. Hybrid
- Mix local and Anthropic runtimes per agent
- Balance cost/quality/latency

## Key Design Decisions

1. **Backward Compatibility**: System detects runtime presence and falls back to dialogue-based pairing
2. **Test Iteration**: Max 3 test-fix cycles to prevent infinite loops
3. **Workspace Isolation**: Each story gets its own directory to avoid conflicts
4. **BDD Optional**: Stories work with or without explicit scenarios
5. **Mock Mode**: All components work in mock mode for testing without real LLM calls

## Next Steps

✅ Phase 5: Pairing integration
✅ Phase 6: BDD/DDD support
✅ Phase 7: Workspace management
✅ Phase 8: Test execution

**Future Enhancements**:
- Coverage metrics from actual test runs
- Pull request creation via `gh` CLI
- Multi-file refactoring support
- Incremental repo updates (vs fresh clone)
