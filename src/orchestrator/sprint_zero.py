"""Sprint 0 infrastructure story generation and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .backlog import ProductMetadata
from .convention_analyzer import ConventionAnalyzer


@dataclass
class InfrastructureStory:
    """Infrastructure story for Sprint 0."""

    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    story_points: int
    priority: int
    assigned_specializations: List[str]
    config_files: List[str]
    validation_command: Optional[str] = None
    template_content: Optional[Dict[str, str]] = None


class BrownfieldAnalyzer:
    """Analyzes existing repository and identifies infrastructure gaps."""

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def analyze(self) -> Dict[str, bool]:
        """Check which infrastructure exists."""
        return {
            "ci_pipeline": self._has_ci_pipeline(),
            "docker": self._has_docker(),
            "python_linting": self._has_python_linting(),
            "python_testing": self._has_python_testing(),
            "go_linting": self._has_go_linting(),
            "rust_linting": self._has_rust_linting(),
            "typescript_linting": self._has_typescript_linting(),
            "cpp_linting": self._has_cpp_linting(),
            "kubernetes": self._has_kubernetes(),
        }

    def _has_ci_pipeline(self) -> bool:
        """Check for CI config files."""
        return (self.workspace / ".github" / "workflows").exists() or (
            self.workspace / ".gitlab-ci.yml"
        ).exists()

    def _has_docker(self) -> bool:
        """Check for Docker configuration."""
        return (self.workspace / "Dockerfile").exists()

    def _has_python_linting(self) -> bool:
        """Check for Python linting config."""
        pyproject = self.workspace / "pyproject.toml"
        if not pyproject.exists():
            return False
        content = pyproject.read_text()
        return "[tool.black]" in content or "[tool.ruff]" in content

    def _has_python_testing(self) -> bool:
        """Check for Python test configuration."""
        pyproject = self.workspace / "pyproject.toml"
        if not pyproject.exists():
            return False
        content = pyproject.read_text()
        return "[tool.pytest" in content or "[tool.coverage" in content

    def _has_go_linting(self) -> bool:
        """Check for Go linting config."""
        return (self.workspace / ".golangci.yml").exists()

    def _has_rust_linting(self) -> bool:
        """Check for Rust linting config."""
        return (self.workspace / "rustfmt.toml").exists()

    def _has_typescript_linting(self) -> bool:
        """Check for TypeScript linting config."""
        return (self.workspace / "tsconfig.json").exists() and (
            self.workspace / ".eslintrc.json"
        ).exists()

    def _has_cpp_linting(self) -> bool:
        """Check for C++ linting config."""
        return (self.workspace / ".clang-format").exists()

    def _has_kubernetes(self) -> bool:
        """Check for Kubernetes manifests."""
        return (
            (self.workspace / "k8s").exists()
            or (self.workspace / "kubernetes").exists()
            or (self.workspace / "helm").exists()
        )

    def generate_gap_stories(
        self, analysis: Dict[str, bool], available_stories: List[InfrastructureStory]
    ) -> List[InfrastructureStory]:
        """Generate stories only for missing infrastructure."""
        gaps = [key for key, exists in analysis.items() if not exists]

        # Map gaps to story ID patterns
        gap_to_pattern = {
            "ci_pipeline": ["ci-gha", "ci-gitlab", "ci"],
            "docker": ["docker"],
            "python_linting": ["py-lint", "python-lint"],
            "python_testing": ["py-test", "python-test"],
            "go_linting": ["go-lint"],
            "rust_linting": ["rust-lint"],
            "typescript_linting": ["ts-lint", "typescript-lint"],
            "cpp_linting": ["cpp-lint", "c++-lint"],
            "kubernetes": ["k8s", "kubernetes"],
        }

        # Filter stories by matching infrastructure gaps
        gap_stories = []
        for story in available_stories:
            story_id_lower = story.id.lower()
            for gap in gaps:
                patterns = gap_to_pattern.get(gap, [gap.replace("_", "-")])
                if any(pattern in story_id_lower for pattern in patterns):
                    gap_stories.append(story)
                    break

        return gap_stories


class SprintZeroGenerator:
    """Generates infrastructure stories for Sprint 0."""

    # Story templates for different infrastructure components
    PYTHON_STORIES = [
        InfrastructureStory(
            id="INFRA-PY-LINT",
            title="Setup Python linting (black, ruff, mypy)",
            description="Configure Python code quality tools for consistent formatting and type checking",
            acceptance_criteria=[
                "pyproject.toml exists with black, ruff, mypy configurations",
                "black formats code to 88 char line length",
                "ruff catches common issues and import ordering",
                "mypy type checks successfully",
            ],
            story_points=3,
            priority=2,
            assigned_specializations=["backend", "devops"],
            config_files=["pyproject.toml"],
            validation_command="black --check . && ruff check . && mypy .",
            template_content={
                "pyproject.toml": """[tool.black]
line-length = 88
target-version = ['py39', 'py310', 'py311']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
ignore = []

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
"""
            },
        ),
        InfrastructureStory(
            id="INFRA-PY-TEST",
            title="Setup Python testing (pytest, coverage)",
            description="Configure pytest and coverage reporting for Python code",
            acceptance_criteria=[
                "pyproject.toml includes pytest configuration",
                "Coverage tracking enabled with 85% minimum",
                "Test discovery configured for tests/ directory",
                "HTML coverage reports generated",
            ],
            story_points=3,
            priority=3,
            assigned_specializations=["backend", "qa"],
            config_files=["pyproject.toml"],
            validation_command="pytest --collect-only",
            template_content={
                "pyproject.toml": """[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=src --cov-report=term-missing --cov-report=html"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
precision = 2
fail_under = 85
"""
            },
        ),
    ]

    GO_STORIES = [
        InfrastructureStory(
            id="INFRA-GO-LINT",
            title="Setup Go linting (golangci-lint)",
            description="Configure golangci-lint for Go code quality checks",
            acceptance_criteria=[
                ".golangci.yml exists with linter configuration",
                "gofmt, govet, staticcheck enabled",
                "go.mod file created with module path",
                "Linting passes on existing code",
            ],
            story_points=3,
            priority=4,
            assigned_specializations=["backend", "devops"],
            config_files=[".golangci.yml", "go.mod"],
            validation_command="golangci-lint run",
            template_content={
                ".golangci.yml": """linters:
  enable:
    - gofmt
    - govet
    - staticcheck
    - errcheck
    - gosimple
    - ineffassign
    - unused

linters-settings:
  gofmt:
    simplify: true

run:
  timeout: 5m
  tests: true
""",
                "go.mod": """module github.com/example/project

go 1.21

require ()
""",
            },
        ),
    ]

    RUST_STORIES = [
        InfrastructureStory(
            id="INFRA-RUST-LINT",
            title="Setup Rust linting (rustfmt, clippy)",
            description="Configure Rust formatting and linting tools",
            acceptance_criteria=[
                "rustfmt.toml exists with formatting rules",
                "Cargo.toml configured for project",
                "clippy linting enabled",
                "Code formatted consistently",
            ],
            story_points=3,
            priority=5,
            assigned_specializations=["backend", "devops"],
            config_files=["rustfmt.toml", "Cargo.toml"],
            validation_command="cargo fmt -- --check && cargo clippy",
            template_content={
                "rustfmt.toml": """edition = "2021"
max_width = 100
tab_spaces = 4
""",
                "Cargo.toml": """[package]
name = "project"
version = "0.1.0"
edition = "2021"

[dependencies]

[dev-dependencies]
""",
            },
        ),
    ]

    TYPESCRIPT_STORIES = [
        InfrastructureStory(
            id="INFRA-TS-LINT",
            title="Setup TypeScript linting (eslint, prettier)",
            description="Configure TypeScript tooling for type checking and code quality",
            acceptance_criteria=[
                "tsconfig.json exists with strict mode enabled",
                ".eslintrc.json configured with TypeScript parser",
                ".prettierrc for consistent formatting",
                "All config files parse successfully",
            ],
            story_points=3,
            priority=6,
            assigned_specializations=["frontend", "devops"],
            config_files=["tsconfig.json", ".eslintrc.json", ".prettierrc"],
            validation_command="tsc --noEmit && eslint . && prettier --check .",
            template_content={
                "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
""",
                ".eslintrc.json": """{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "semi": ["error", "always"],
    "quotes": ["error", "single"]
  }
}
""",
                ".prettierrc": """{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "printWidth": 100
}
""",
            },
        ),
    ]

    CPP_STORIES = [
        InfrastructureStory(
            id="INFRA-CPP-LINT",
            title="Setup C++ linting (clang-format, cppcheck)",
            description="Configure C++ code formatting and static analysis",
            acceptance_criteria=[
                ".clang-format exists with formatting rules",
                "CMakeLists.txt configured for project",
                "cppcheck static analysis configured",
                "Build system generates compile_commands.json",
            ],
            story_points=3,
            priority=7,
            assigned_specializations=["backend", "devops"],
            config_files=[".clang-format", "CMakeLists.txt"],
            validation_command="clang-format --dry-run --Werror **/*.cpp **/*.h",
            template_content={
                ".clang-format": """BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
""",
                "CMakeLists.txt": """cmake_minimum_required(VERSION 3.15)
project(project VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Add your source files here
""",
            },
        ),
    ]

    DOCKER_STORIES = [
        InfrastructureStory(
            id="INFRA-DOCKER",
            title="Setup Docker containerization",
            description="Create Dockerfile and docker-compose for local development",
            acceptance_criteria=[
                "Dockerfile builds successfully",
                "docker-compose.yml for local dev environment",
                ".dockerignore excludes unnecessary files",
                "Container runs application correctly",
            ],
            story_points=5,
            priority=8,
            assigned_specializations=["devops"],
            config_files=["Dockerfile", "docker-compose.yml", ".dockerignore"],
            validation_command="docker build -t app:test .",
            template_content={
                "Dockerfile": """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
""",
                "docker-compose.yml": """version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=development
""",
                ".dockerignore": """__pycache__
*.pyc
.git
.venv
tests
*.md
""",
            },
        ),
    ]

    KUBERNETES_STORIES = [
        InfrastructureStory(
            id="INFRA-K8S",
            title="Setup Kubernetes deployment manifests",
            description="Create Kubernetes deployment, service, and configuration manifests",
            acceptance_criteria=[
                "k8s/deployment.yaml for application deployment",
                "k8s/service.yaml for service exposure",
                "k8s/configmap.yaml for configuration",
                "Manifests validate with kubeval or kubectl dry-run",
            ],
            story_points=5,
            priority=9,
            assigned_specializations=["devops", "networking"],
            config_files=[
                "k8s/deployment.yaml",
                "k8s/service.yaml",
                "k8s/configmap.yaml",
            ],
            validation_command="kubectl apply --dry-run=client -f k8s/",
            template_content={
                "k8s/deployment.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
      - name: app
        image: app:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
""",
                "k8s/service.yaml": """apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  selector:
    app: app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
""",
                "k8s/configmap.yaml": """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  ENV: "production"
""",
            },
        ),
    ]

    CI_STORIES = [
        InfrastructureStory(
            id="INFRA-CI-GHA",
            title="Setup GitHub Actions CI pipeline",
            description="Create GitHub Actions workflow for automated testing, linting, and deployment",
            acceptance_criteria=[
                "Workflow runs on push to main and PRs",
                "Runs tests for all languages in project",
                "Linting passes before tests",
                "Coverage reports generated and uploaded",
            ],
            story_points=5,
            priority=1,
            assigned_specializations=["devops"],
            config_files=[".github/workflows/ci.yml"],
            validation_command="gh workflow list",
            template_content={
                ".github/workflows/ci.yml": """name: CI

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
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov black ruff mypy

      - name: Lint with ruff
        run: ruff check .

      - name: Format check with black
        run: black --check .

      - name: Type check with mypy
        run: mypy .

      - name: Test with pytest
        run: pytest --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
"""
            },
        ),
        InfrastructureStory(
            id="INFRA-CI-GITLAB",
            title="Setup GitLab CI pipeline",
            description="Create GitLab CI configuration for automated testing and deployment",
            acceptance_criteria=[
                ".gitlab-ci.yml runs on MR and main branch",
                "Test stage runs all project tests",
                "Lint stage enforces code quality",
                "Pipeline passes on clean code",
            ],
            story_points=5,
            priority=1,
            assigned_specializations=["devops"],
            config_files=[".gitlab-ci.yml"],
            validation_command="gitlab-ci-lint .gitlab-ci.yml",
            template_content={
                ".gitlab-ci.yml": """stages:
  - lint
  - test
  - build

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

lint:
  stage: lint
  image: python:3.11
  script:
    - pip install black ruff mypy
    - black --check .
    - ruff check .
    - mypy .

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=src --cov-report=xml --cov-report=term
  coverage: '/TOTAL.*\\s+(\\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
"""
            },
        ),
    ]

    def __init__(
        self,
        product_metadata: ProductMetadata,
        team_config: Dict,
        workspace: Optional[Path] = None,
    ):
        self.product = product_metadata
        self.team = team_config
        self.workspace = workspace

    def generate_stories(
        self, brownfield_mode: bool = False
    ) -> List[InfrastructureStory]:
        """Generate all infrastructure stories based on tech stack and languages.

        Args:
            brownfield_mode: If True, analyze existing workspace and only generate stories for gaps

        Returns:
            List of infrastructure stories (all stories for greenfield, gap stories for brownfield)
        """
        # Generate all potential stories
        all_stories = self._generate_all_stories()

        # If brownfield, filter to only gap stories
        if brownfield_mode and self.workspace:
            analyzer = BrownfieldAnalyzer(self.workspace)
            analysis = analyzer.analyze()

            # Also run convention analyzer to augment existing conventions
            convention_analyzer = ConventionAnalyzer(self.workspace)
            for lang in self.product.languages:
                lang_lower = lang.lower()
                conventions = convention_analyzer.analyze(lang_lower)
                augmented = convention_analyzer.generate_augmented_config(
                    lang_lower, conventions
                )

                # Log detected conventions (would be used by agents during implementation)
                if conventions:
                    print(f"  Detected {lang_lower} conventions: {conventions}")
                    print(f"  Augmented config: {augmented}")

            return analyzer.generate_gap_stories(analysis, all_stories)

        return all_stories

    def _generate_all_stories(self) -> List[InfrastructureStory]:
        """Generate all possible infrastructure stories."""
        stories = []

        # CI/CD pipeline (always needed)
        if (
            "github-actions" in self.product.tech_stack
            or "github" in str(self.product.repository_url).lower()
        ):
            stories.extend(self._generate_ci_stories_with_all_languages("github"))
        elif (
            "gitlab-ci" in self.product.tech_stack
            or "gitlab" in str(self.product.repository_url).lower()
        ):
            stories.extend(self._generate_ci_stories_with_all_languages("gitlab"))
        else:
            # Default to GitHub Actions if not specified
            stories.extend(self._generate_ci_stories_with_all_languages("github"))

        # Per-language tooling
        for lang in self.product.languages:
            lang_lower = lang.lower()
            if lang_lower == "python":
                stories.extend(self.PYTHON_STORIES)
            elif lang_lower == "go":
                stories.extend(self.GO_STORIES)
            elif lang_lower == "rust":
                stories.extend(self.RUST_STORIES)
            elif lang_lower in ["typescript", "ts", "javascript", "js"]:
                stories.extend(self.TYPESCRIPT_STORIES)
            elif lang_lower in ["c++", "cpp", "c"]:
                stories.extend(self.CPP_STORIES)

        # Build validation stories for compiled languages
        if any(
            lang.lower() in ["go", "rust", "c++", "cpp", "c"]
            for lang in self.product.languages
        ):
            stories.extend(self._generate_build_validation_stories())

        # Containerization
        if "docker" in self.product.tech_stack:
            stories.extend(self.DOCKER_STORIES)

        # Kubernetes/Helm
        if "kubernetes" in self.product.tech_stack or "helm" in self.product.tech_stack:
            stories.extend(self.KUBERNETES_STORIES)

        return stories

    def _generate_ci_stories_with_all_languages(
        self, provider: str
    ) -> List[InfrastructureStory]:
        """Generate CI story templates that include all project languages.

        Args:
            provider: 'github' or 'gitlab'

        Returns:
            CI story with template customized for project languages
        """
        if provider == "github":
            return [self._customize_github_actions_template()]
        else:
            return [self._customize_gitlab_ci_template()]

    def _customize_github_actions_template(self) -> InfrastructureStory:
        """Generate GitHub Actions CI template with all project languages."""
        languages = [lang.lower() for lang in self.product.languages]

        # Build CI steps for each language
        ci_steps = []

        if "python" in languages:
            ci_steps.append(
                """      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov black ruff mypy

      - name: Format check (Python)
        run: black --check .

      - name: Lint (Python)
        run: ruff check .

      - name: Type check (Python)
        run: mypy .

      - name: Test (Python)
        run: pytest --cov=src --cov-report=xml --cov-report=term"""
            )

        if "go" in languages:
            ci_steps.append(
                """      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - name: Format check (Go)
        run: gofmt -d .

      - name: Lint (Go)
        run: golangci-lint run

      - name: Test (Go)
        run: go test -race -cover ./..."""
            )

        if "rust" in languages:
            ci_steps.append(
                """      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          components: rustfmt, clippy

      - name: Format check (Rust)
        run: cargo fmt -- --check

      - name: Lint (Rust)
        run: cargo clippy -- -D warnings

      - name: Test (Rust)
        run: cargo test"""
            )

        if any(lang in languages for lang in ["typescript", "ts", "javascript", "js"]):
            ci_steps.append(
                """      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Node dependencies
        run: npm ci

      - name: Format check (TypeScript)
        run: npx prettier --check .

      - name: Lint (TypeScript)
        run: npx eslint . --ext .ts,.tsx

      - name: Type check (TypeScript)
        run: npx tsc --noEmit

      - name: Test (TypeScript)
        run: npm test"""
            )

        if any(lang in languages for lang in ["c++", "cpp", "c"]):
            ci_steps.append(
                """      - name: Install C++ tools
        run: sudo apt-get update && sudo apt-get install -y cmake clang-format clang-tidy

      - name: Format check (C++)
        run: find . -name '*.cpp' -o -name '*.h' | xargs clang-format --dry-run --Werror

      - name: Build (C++)
        run: |
          mkdir build
          cd build
          cmake ..
          make

      - name: Test (C++)
        run: cd build && ctest"""
            )

        workflow_content = f"""name: CI

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

{chr(10).join(ci_steps)}

      - name: Upload coverage
        if: success()
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
"""

        return InfrastructureStory(
            id="INFRA-CI-GHA",
            title="Setup GitHub Actions CI pipeline",
            description=f"Create GitHub Actions workflow for {', '.join(self.product.languages)} project",
            acceptance_criteria=[
                "Workflow runs on push to main and PRs",
                f"Runs format/lint/test for all languages: {', '.join(self.product.languages)}",
                "All quality checks pass",
                "Coverage reports generated",
            ],
            story_points=5,
            priority=1,
            assigned_specializations=["devops"],
            config_files=[".github/workflows/ci.yml"],
            validation_command="gh workflow list",
            template_content={".github/workflows/ci.yml": workflow_content},
        )

    def _customize_gitlab_ci_template(self) -> InfrastructureStory:
        """Generate GitLab CI template with all project languages."""
        # Similar structure to GitHub Actions but for GitLab CI YAML
        # For brevity, return existing template (can be expanded similarly)
        return self.CI_STORIES[1]

    def _generate_build_validation_stories(self) -> List[InfrastructureStory]:
        """Generate build validation stories for compiled languages."""
        stories = []

        if "go" in [lang.lower() for lang in self.product.languages]:
            stories.append(
                InfrastructureStory(
                    id="INFRA-GO-BUILD",
                    title="Setup Go build validation",
                    description="Ensure Go code builds successfully with all dependencies",
                    acceptance_criteria=[
                        "go.mod includes all dependencies",
                        "go build ./... succeeds",
                        "go mod tidy keeps dependencies clean",
                        "Build produces working binary",
                    ],
                    story_points=2,
                    priority=7,
                    assigned_specializations=["golang_specialist", "backend"],
                    config_files=["Makefile"],
                    validation_command="go build ./...",
                    template_content={
                        "Makefile": """build:
\tgo build -v ./...

test:
\tgo test -v -race -cover ./...

lint:
\tgolangci-lint run

fmt:
\tgofmt -w .
\tgoimports -w .

.PHONY: build test lint fmt
"""
                    },
                )
            )

        if "rust" in [lang.lower() for lang in self.product.languages]:
            stories.append(
                InfrastructureStory(
                    id="INFRA-RUST-BUILD",
                    title="Setup Rust build validation",
                    description="Ensure Rust code builds successfully in debug and release modes",
                    acceptance_criteria=[
                        "cargo build succeeds",
                        "cargo build --release succeeds",
                        "cargo check runs quickly for validation",
                        "All dependencies compile",
                    ],
                    story_points=2,
                    priority=8,
                    assigned_specializations=["rust_specialist", "systems_programming"],
                    config_files=["Makefile"],
                    validation_command="cargo build",
                    template_content={
                        "Makefile": """build:
\tcargo build

release:
\tcargo build --release

test:
\tcargo test

lint:
\tcargo clippy -- -D warnings

fmt:
\tcargo fmt

check:
\tcargo check

.PHONY: build release test lint fmt check
"""
                    },
                )
            )

        if any(lang.lower() in ["c++", "cpp", "c"] for lang in self.product.languages):
            stories.append(
                InfrastructureStory(
                    id="INFRA-CPP-BUILD",
                    title="Setup C++ build validation",
                    description="Ensure C++ code builds successfully with CMake",
                    acceptance_criteria=[
                        "CMakeLists.txt configures project",
                        "Debug build succeeds",
                        "Release build succeeds with optimizations",
                        "Tests compile and link",
                    ],
                    story_points=3,
                    priority=9,
                    assigned_specializations=["cpp_specialist", "systems_programming"],
                    config_files=["CMakeLists.txt", "Makefile"],
                    validation_command="cmake -B build && cmake --build build",
                    template_content={
                        "CMakeLists.txt": """cmake_minimum_required(VERSION 3.20)
project(MyProject CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(myapp src/main.cpp)

enable_testing()
""",
                        "Makefile": """build:
\tmkdir -p build && cd build && cmake .. && make

release:
\tmkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && make

test:
\tcd build && ctest

clean:
\trm -rf build

.PHONY: build release test clean
""",
                    },
                )
            )

        return stories

    def convert_to_backlog_format(self, story: InfrastructureStory) -> Dict:
        """Convert InfrastructureStory to backlog.yaml story format."""
        return {
            "id": story.id,
            "title": story.title,
            "description": story.description,
            "acceptance_criteria": story.acceptance_criteria,
            "story_points": story.story_points,
            "priority": story.priority,
            "sprint": 0,  # Explicitly Sprint 0
            "assigned_specializations": story.assigned_specializations,
            "_infrastructure": {
                "config_files": story.config_files,
                "validation_command": story.validation_command,
                "template_content": story.template_content,
            },
        }
