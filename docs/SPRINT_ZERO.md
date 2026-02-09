# Sprint 0: Infrastructure Setup

## Overview

Sprint 0 implements infrastructure setup before feature development begins. Real development teams don't start coding immediately—they need to align on coding standards, set up CI/CD pipelines, establish project infrastructure, and configure tooling.

**Sprint 0 runs automatically as the first sprint** when enabled (default). The team generates and completes infrastructure stories for linters, formatters, CI/CD, containerization, and deployment manifests.

## Key Features

- **Multi-language support**: Python, Go, Rust, TypeScript, C/C++
- **Hybrid trigger**: System generates stories OR stakeholder provides explicit stories in backlog.yaml
- **Brownfield-friendly**: Analyzes existing repos and only creates stories for missing infrastructure
- **CI validation gate**: Sprint 0 not "done" until CI pipeline validates successfully
- **Real working configs**: Agents generate actual YAML/JSON/TOML configs using file tools

## Configuration

### Enable/Disable Sprint 0

```yaml
# config.yaml
sprint_zero:
  enabled: true  # Set to false to skip Sprint 0
```

When disabled, sprints start at 1. When enabled (default), sprint loop runs 0 → N.

### Define Product Metadata

```yaml
# backlog.yaml
product:
  name: "TaskFlow Pro"
  description: "SaaS project management platform"

  # Multi-language support
  languages: [python, go, typescript]

  # Tech stack
  tech_stack:
    - docker
    - kubernetes
    - github-actions  # or gitlab-ci
    - prometheus

  # Repository info
  repository:
    type: greenfield  # or brownfield
    url: ""  # If brownfield, URL to existing repo
```

## Generated Infrastructure Stories

### Python

- **INFRA-PY-LINT**: Setup black, ruff, mypy in pyproject.toml
- **INFRA-PY-TEST**: Setup pytest with coverage tracking

### Go

- **INFRA-GO-LINT**: Setup golangci-lint with .golangci.yml and go.mod

### Rust

- **INFRA-RUST-LINT**: Setup rustfmt and clippy with rustfmt.toml and Cargo.toml

### TypeScript

- **INFRA-TS-LINT**: Setup eslint, prettier, tsconfig.json

### C++

- **INFRA-CPP-LINT**: Setup clang-format, cppcheck, CMakeLists.txt

### Containerization

- **INFRA-DOCKER**: Dockerfile, docker-compose.yml, .dockerignore

### Kubernetes

- **INFRA-K8S**: Deployment, Service, ConfigMap manifests in k8s/

### CI/CD

- **INFRA-CI-GHA**: GitHub Actions workflow (.github/workflows/ci.yml)
- **INFRA-CI-GITLAB**: GitLab CI configuration (.gitlab-ci.yml)

## Usage Modes

### Greenfield (Default)

System generates all infrastructure stories based on `languages` and `tech_stack`:

```yaml
product:
  languages: [python, go]
  tech_stack: [github-actions, docker]
  repository:
    type: greenfield
    url: ""
```

**Generated stories**: Python linting, Python testing, Go linting, GitHub Actions CI, Docker setup (5 stories)

### Brownfield (Existing Repo)

System clones repo, analyzes existing infrastructure, and generates stories ONLY for missing pieces:

```yaml
product:
  languages: [python]
  tech_stack: [github-actions, docker]
  repository:
    type: brownfield
    url: "https://github.com/your-org/existing-project.git"
```

**Analysis example**:
```
✓ GitHub Actions workflow exists
✗ pyproject.toml missing black/ruff config
✗ Dockerfile missing
```

**Generated stories**: Python linting, Docker setup (2 stories, CI skipped)

### Explicit Stories (Stakeholder Override)

Provide custom Sprint 0 stories in backlog.yaml:

```yaml
product:
  languages: [python]
  tech_stack: [github-actions]
  repository:
    type: greenfield
    url: ""

stories:
  - id: "INFRA-001"
    title: "Setup GitHub Actions CI pipeline"
    description: "Custom CI workflow with specific requirements"
    acceptance_criteria:
      - "Workflow runs on PR and main"
      - "Runs tests for Python 3.11 and 3.12"
      - "Deploys to staging on main merge"
    story_points: 5
    priority: 1
    sprint: 0  # Explicitly Sprint 0
    assigned_specializations: [devops]
```

When explicit Sprint 0 stories exist, system uses those instead of generating.

## Sprint 0 Workflow

```
Sprint 0 Execution:
│
├─ Planning Phase
│   ├─ Detect project type (greenfield vs brownfield)
│   ├─ If greenfield: Generate all infrastructure stories
│   ├─ If brownfield: Analyze repo → Generate gap stories
│   └─ If explicit stories in backlog: Use those
│
├─ Development Phase (normal pairing)
│   ├─ DevOps specialists lead infrastructure tasks
│   ├─ Agents use write_file tool to create configs
│   ├─ Stories: "Setup GitHub Actions CI", "Configure Go linter", etc.
│   └─ Agents commit configs with git tools
│
├─ QA Review
│   ├─ QA validates configs are syntactically correct
│   └─ Approve/reject
│
├─ CI Validation Gate (NEW)
│   ├─ Actually run CI pipeline validation (gh workflow list, yaml parse)
│   ├─ If CI passes → Sprint 0 complete
│   └─ If CI fails → Log warning, mark incomplete
│
└─ Retrospective
    └─ Team discusses infrastructure decisions
```

## CI Validation

Sprint 0 includes a validation gate that checks if CI pipelines are correctly configured:

**GitHub Actions**:
```bash
gh workflow list  # Validates workflow syntax
```

**GitLab CI**:
```python
yaml.safe_load('.gitlab-ci.yml')  # Validates YAML syntax
```

If validation fails, Sprint 0 status is marked as "incomplete" but experiment continues.

## Agent Assignment

Infrastructure stories are assigned by specialization:

```python
# DevOps specialists lead CI/CD, Docker, K8s stories
assigned_specializations: [devops]

# Backend + DevOps collaborate on language tooling
assigned_specializations: [backend, devops]

# Frontend + DevOps for TypeScript/JS tooling
assigned_specializations: [frontend, devops]
```

Pairing follows normal rules: driver + navigator, checkpoints at 25/50/75/100%.

## Example Sprint 0 Run

```bash
export MOCK_LLM=true
python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/sprint-zero-test \
  --db-url mock:// \
  --backlog backlog.yaml
```

**Output**:
```
=============================================================
SPRINT 0 (Infrastructure)  [14:23:45]
=============================================================
  Planning (Sprint 0)...
    Generating infrastructure stories for: python, typescript
    Generated 4 infrastructure stories
    Added 4 stories to Sprint 0 backlog
  Development...
    [Pairing sessions for infrastructure stories]
  QA review...
    [QA validates configs]
  CI Validation...
    ✓ GitHub Actions workflow validated
  Retrospective...
  Artifacts...
  ✓ Sprint 0 complete: Infrastructure validated

=============================================================
SPRINT 1  [14:25:12]
=============================================================
  Planning...
    [Feature stories selected]
  ...
```

## Generated File Examples

### Python - pyproject.toml

```toml
[tool.black]
line-length = 88
target-version = ['py39', 'py310', 'py311']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
addopts = "-ra -q --cov=src --cov-report=html"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src"]
```

### GitHub Actions - .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest black ruff mypy

      - name: Lint with ruff
        run: ruff check .

      - name: Format check with black
        run: black --check .

      - name: Test with pytest
        run: pytest --cov=src --cov-report=xml
```

### Docker - Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## Research Questions

Sprint 0 enables new research questions:

1. **Infrastructure Quality**: Do AI teams choose appropriate tooling configurations?
2. **Consensus Building**: How do agents negotiate coding style standards?
3. **Specialization Value**: Are DevOps agents more effective than generalists for infrastructure?
4. **Learning Transfer**: Do juniors learn DevOps practices from Sprint 0 pairing?
5. **Brownfield Adaptation**: Can agents understand and improve existing infrastructure?

## Disabling Sprint 0

To skip Sprint 0 and start with feature development:

```yaml
# config.yaml
sprint_zero:
  enabled: false
```

Or:

```bash
# Temporarily disable via environment
SPRINT_ZERO_ENABLED=false python -m src.orchestrator.main ...
```

## Troubleshooting

### "No Sprint 0 stories generated"

**Cause**: Empty `languages` or `tech_stack` in backlog.yaml

**Fix**: Add at least one language:
```yaml
product:
  languages: [python]
  tech_stack: [github-actions]
```

### "CI validation failed"

**Cause**: Generated CI config has syntax errors or gh CLI not available

**Fix**: Sprint 0 will complete anyway. Check `/tmp/agent-workspace/sprint-0/` for generated configs and manually validate.

### "Brownfield analysis finds nothing"

**Cause**: Repository URL incorrect or unreachable

**Fix**: Verify `repository.url` is accessible:
```bash
git clone <url> /tmp/test-clone
```

## Implementation Details

**Files**:
- `src/orchestrator/sprint_zero.py` - Story generation, brownfield analysis
- `src/orchestrator/sprint_manager.py` - Sprint 0 workflow, CI validation
- `src/orchestrator/backlog.py` - ProductMetadata extraction
- `src/orchestrator/config.py` - sprint_zero_enabled flag
- `src/orchestrator/main.py` - Sprint loop starts at 0

**Tests**:
- `tests/unit/test_sprint_zero.py` - 11 unit tests
- `tests/integration/test_sprint_zero_integration.py` - 3 integration tests

**Total**: 38/38 tests passing
