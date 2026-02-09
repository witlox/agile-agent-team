# Multi-Language Support Implementation

## Status: Phase 1 Complete ✅

Multi-language support has been implemented with tool-enforced coding standards and multi-language test execution.

## What's Been Implemented

### 1. Tool-Enforced Coding Standards ✅

Created concise, standards-based convention files in `team_config/00_base/coding_standards/`:

#### Python (`python.md`)
- **Formatter**: Black (88 chars, NO config)
- **Linter**: Ruff (replaces flake8, isort, pyupgrade)
- **Type Checker**: mypy (strict mode)
- **Testing**: pytest (≥85% coverage)
- **Commands**: `black . && ruff check . && mypy . && pytest --cov`

#### Go (`go.md`)
- **Formatter**: gofmt + goimports (tabs, NO config)
- **Linter**: golangci-lint (govet, staticcheck, errcheck)
- **Testing**: go test (≥80% coverage, race detector)
- **Commands**: `gofmt -w . && golangci-lint run && go test -race -cover ./...`

#### Rust (`rust.md`)
- **Formatter**: rustfmt (100 chars)
- **Linter**: clippy (treat warnings as errors)
- **Testing**: cargo test (≥85% coverage)
- **Commands**: `cargo fmt && cargo clippy -- -D warnings && cargo test`

#### TypeScript (`typescript.md`)
- **Formatter**: Prettier (configurable)
- **Linter**: ESLint with @typescript-eslint
- **Type Checker**: tsc (strict mode required)
- **Testing**: Jest (≥85% coverage)
- **Commands**: `prettier --write . && eslint . --ext .ts,.tsx && tsc --noEmit && jest`

#### C++ (`cpp.md`)
- **Formatter**: clang-format (LLVM/Google style)
- **Linter**: clang-tidy (modernize, readability, performance)
- **Standard**: C++ Core Guidelines (C++17+)
- **Testing**: GoogleTest (≥80% coverage)
- **Commands**: `clang-format -i **/*.cpp && clang-tidy *.cpp && ctest`

### 2. Base Agent Integration ✅

Updated `team_config/00_base/base_agent.md`:
- Added comprehensive "Coding Standards" section
- Lists tool requirements for all 5 languages
- Defines deviation policy (necessity/simplicity/performance)
- Emphasizes tool enforcement over manual style
- **ALL agents now know these standards by default**

### 3. Multi-Language Test Runner ✅

Created `src/tools/agent_tools/test_runner_multi.py`:

**Features:**
- **Auto-detection**: Detects language from workspace files
- **Language support**: Python, Go, Rust, TypeScript, C++
- **Coverage collection**: Language-specific coverage metrics
- **Unified interface**: Same `run_tests` tool for all languages

**Detection Logic:**
- Python: pyproject.toml, setup.py, *.py files
- Go: go.mod, *.go files
- Rust: Cargo.toml, *.rs files
- TypeScript: package.json, tsconfig.json, *.ts files
- C++: CMakeLists.txt, *.cpp files

**Commands Executed:**
```bash
# Python
pytest --cov=src --cov-report=json --cov-branch tests/

# Go
go test -v -cover -race ./...

# Rust
cargo test

# TypeScript
npm test -- --coverage

# C++
ctest --output-on-failure
```

### 4. Tool Factory Update ✅

Updated `src/tools/agent_tools/factory.py`:
- Replaced `RunTestsTool` with `MultiLanguageTestRunner`
- Agents using `run_tests` tool now get multi-language support automatically

## Architecture

```
Coding Standards Flow:
│
├─ Agent Initialization
│   └─ Loads base_agent.md → includes coding standards
│
├─ Code Writing
│   ├─ Agent knows: Black for Python, gofmt for Go, etc.
│   └─ Agent follows tool conventions, not arbitrary style
│
└─ Testing
    ├─ Agent calls run_tests tool
    ├─ MultiLanguageTestRunner detects language
    ├─ Runs appropriate test command (pytest/go test/cargo test/jest/ctest)
    └─ Returns results with coverage metrics
```

## What Still Needs Implementation

### Phase 2: Build & Format Tools

#### 1. Multi-Language Formatter Tool

```python
# src/tools/agent_tools/formatter.py
class MultiLanguageFormatter(Tool):
    """Auto-detect and run language formatter."""

    async def execute(self):
        # Detect language
        # Run: black/gofmt/rustfmt/prettier/clang-format
        pass
```

#### 2. Multi-Language Linter Tool

```python
# src/tools/agent_tools/linter.py
class MultiLanguageLinter(Tool):
    """Auto-detect and run language linter."""

    async def execute(self):
        # Detect language
        # Run: ruff/golangci-lint/clippy/eslint/clang-tidy
        pass
```

#### 3. Multi-Language Build Tool

```python
# src/tools/agent_tools/builder.py
class MultiLanguageBuilder(Tool):
    """Auto-detect and run language build."""

    async def execute(self):
        # Python: pip install -r requirements.txt
        # Go: go build
        # Rust: cargo build
        # TypeScript: npm install && npm run build
        # C++: cmake -B build && cmake --build build
        pass
```

### Phase 3: Brownfield Convention Detection

#### Convention Analyzer

```python
# src/orchestrator/convention_analyzer.py
class ConventionAnalyzer:
    """Analyzes existing code to infer conventions."""

    def analyze_python(self, workspace: Path) -> Dict:
        """Detect:
        - Line length (from existing code)
        - Quote style (single vs double)
        - Import style
        - Existing linter configs
        """
        pass

    def augment_with_standards(self, detected: Dict, language: str) -> Dict:
        """Merge detected conventions with tool standards."""
        pass
```

Update Sprint 0 to use this for brownfield projects.

### Phase 4: Language Specializations

Add language-focused specializations:

```yaml
# team_config/03_specializations/golang_specialist.md
# Golang Specialist

You are expert in Go:
- Idiomatic Go patterns (error handling, interfaces)
- Goroutines and channels for concurrency
- Standard library usage
- Go testing patterns (table-driven tests)
...
```

Similar for:
- `rust_specialist.md`
- `typescript_specialist.md`
- `cpp_specialist.md`

### Phase 5: Agent Configuration

Update `config.yaml` to add language specialists:

```yaml
models:
  agents:
    alex_senior_golang:
      name: "Alex Chen (Senior Go Developer)"
      seniority: senior
      specializations: [backend, golang_specialist]
      runtime: "local_vllm"
      tools: ["filesystem", "git", "bash", "test_runner"]

    priya_senior_rust:
      name: "Priya Sharma (Senior Rust Developer)"
      seniority: senior
      specializations: [backend, rust_specialist]
      runtime: "local_vllm"
      tools: ["filesystem", "git", "bash", "test_runner"]

    # ... etc
```

### Phase 6: Sprint 0 Updates

Update Sprint 0 templates to include build commands:

```python
# In sprint_zero.py, add validation commands
PYTHON_STORIES = [
    {
        "id": "INFRA-PY-BUILD",
        "title": "Setup Python dependencies",
        "validation_command": "pip install -r requirements.txt && python -c 'import src'",
        ...
    }
]

GO_STORIES = [
    {
        "id": "INFRA-GO-BUILD",
        "title": "Setup Go module",
        "validation_command": "go mod download && go build ./...",
        ...
    }
]
```

## Testing Status

### Tests to Add

1. **Multi-language test runner**:
   ```python
   # tests/unit/test_multi_language_runner.py
   - test_detect_python_workspace
   - test_detect_go_workspace
   - test_run_python_tests
   - test_run_go_tests
   - test_run_rust_tests
   - test_run_typescript_tests
   - test_run_cpp_tests
   - test_coverage_collection
   ```

2. **Convention loading**:
   ```python
   # tests/unit/test_coding_standards.py
   - test_standards_loaded_in_base_agent
   - test_python_standards_reference_tools
   - test_go_standards_reference_tools
   # etc
   ```

3. **Integration tests**:
   ```python
   # tests/integration/test_multi_language_codegen.py
   - test_agent_writes_go_code_and_tests
   - test_agent_writes_rust_code_and_tests
   # etc
   ```

## Usage Example

### Greenfield Multi-Language Project

```yaml
# backlog.yaml
product:
  name: "Microservices Platform"
  languages: [python, go, rust]
  tech_stack: [docker, kubernetes, github-actions]
  repository:
    type: greenfield
```

**Sprint 0 generates**:
- Python linting/testing configs
- Go linting/build configs
- Rust linting/build configs
- Docker multi-stage builds
- CI pipeline that tests all languages

**Sprint 1+ development**:
- Agents auto-detect language in each workspace
- Follow tool-enforced conventions
- Run appropriate tests
- All languages work seamlessly

### Brownfield Migration

```yaml
# backlog.yaml
product:
  languages: [python]  # Existing Python project
  tech_stack: [github-actions]
  repository:
    type: brownfield
    url: "https://github.com/org/existing-python-project.git"
```

**Sprint 0**:
1. Clone repository
2. Detect existing conventions:
   - Line length: 120 (from existing code)
   - No type hints currently
3. Generate stories to:
   - Add mypy configuration
   - Add ruff configuration
   - Keep line length at 120 (deviate from Black's 88)
   - Gradually add type hints

## Configuration

### Allowed Commands (config.yaml)

Agents need these commands available:

```yaml
runtimes:
  tools:
    allowed_commands:
      # Python
      - "python"
      - "python3"
      - "pip"
      - "pytest"
      - "black"
      - "ruff"
      - "mypy"

      # Go
      - "go"
      - "gofmt"
      - "goimports"
      - "golangci-lint"

      # Rust
      - "cargo"
      - "rustfmt"
      - "rustc"

      # TypeScript
      - "npm"
      - "npx"
      - "node"
      - "tsc"

      # C++
      - "cmake"
      - "make"
      - "g++"
      - "clang"
      - "clang-format"
      - "clang-tidy"
      - "ctest"

      # General
      - "git"
      - "ls"
      - "cat"
      - "grep"
      - "find"
```

## Benefits

### For Agents

1. **Clear standards**: Tools define "correct", not arbitrary style guides
2. **Automatic enforcement**: Formatters make code compliant
3. **Consistent behavior**: Same standards across all projects
4. **Multi-language fluency**: Work in any supported language

### For Research

1. **Standardized quality**: All projects follow industry best practices
2. **Fair comparison**: Same quality bar across experiments
3. **Brownfield realism**: Can work with existing codebases
4. **Language effects**: Study how language choice affects outcomes

### For Users

1. **Production-ready code**: Follows industry standards
2. **Tool integration**: Works with standard dev tools
3. **Maintainability**: Code follows conventions developers expect
4. **Flexibility**: Supports greenfield and brownfield projects

## Next Steps

To complete multi-language support:

1. **Implement Phase 2**: Format/lint/build tools
2. **Add Phase 3**: Brownfield convention detection
3. **Create Phase 4**: Language specialist profiles
4. **Update Phase 5**: Agent configurations
5. **Enhance Phase 6**: Sprint 0 build validation
6. **Test thoroughly**: Multi-language integration tests
7. **Document**: Update USAGE.md with multi-language examples

**Estimated effort**: 4-6 hours for Phases 2-6

## Summary

**Phase 1 (Complete)**: Tool-enforced standards + multi-language test runner
**Impact**: Agents now know industry standards for 5 languages and can test code in all of them

**Next**: Add format/lint/build tools and language specialists for full multi-language development capability.
