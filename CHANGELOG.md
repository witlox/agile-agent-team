# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added - External Stakeholder Feedback via Webhooks (2026-02-10)

**Stakeholder review now supports external notification and feedback collection**:
- **StakeholderNotifier** (`src/orchestrator/stakeholder_notify.py`): New module for webhook delivery and feedback collection
  - `StakeholderReviewPayload` (frozen dataclass): Rich sprint summary with velocity trend, coverage, cycle time, disturbances, completed stories, PO assessment
  - `StakeholderFeedback` dataclass: Decision, priority changes, new stories from stakeholders
  - `send_webhook()`: POST JSON to Slack/Teams/Matrix/generic URL with 3-attempt retry (5s/15s/30s backoff)
  - `wait_for_feedback()`: Two modes — file polling or HTTP callback server (aiohttp)
  - Three timeout actions: `auto_approve` (default), `po_proxy` (PO generates feedback), `block` (wait indefinitely)
  - Mock mode: skip HTTP, auto-approve immediately
- **Config**: New `stakeholder_review:` YAML section with cadence, timeout, webhook, and feedback settings
  - Default review cadence changed from 5 to 3 sprints
  - Backward compatible: old `sprints_per_stakeholder_review` field still works
- **SprintManager**: `stakeholder_review()` rewritten from 20-line stub to full implementation
  - Builds payload from sprint results, sends webhook, waits for feedback
  - Applies backlog changes (deprioritize stories, add new stories)
  - Persists feedback in SharedContextDB, publishes `stakeholder_feedback` event on message bus
  - Falls back to PO-only review when webhook not configured (backwards compat)
- **SharedContextDB**: `stakeholder_feedback` table + `store_stakeholder_feedback()` / `get_stakeholder_feedback()` methods
- **Backlog**: `add_story()` method for stakeholder-injected stories
- **18 new tests**: 14 unit tests (`test_stakeholder_notify.py`) + 4 integration tests (`test_stakeholder_review.py`)
- **Test count**: 350 → 368 collected (360 passing, 5 skipped, 3 pre-existing e2e failures)

**Files changed**:
- `src/orchestrator/stakeholder_notify.py` — **NEW**: StakeholderNotifier, payloads, feedback
- `tests/unit/test_stakeholder_notify.py` — **NEW**: 14 unit tests
- `tests/integration/test_stakeholder_review.py` — **NEW**: 4 integration tests
- `src/orchestrator/config.py` — 9 stakeholder review fields + YAML parsing, default cadence 5→3
- `config.yaml` — `stakeholder_review:` section, cadence default 3
- `src/orchestrator/sprint_manager.py` — Rewritten `stakeholder_review()`, StakeholderNotifier creation
- `src/orchestrator/main.py` — Use `stakeholder_review_cadence`, skip Sprint 0 reviews
- `src/tools/shared_context.py` — `_stakeholder_feedback` store, `stakeholder_feedback` table, store/get methods
- `src/orchestrator/backlog.py` — `add_story()` method

### Added - Async Message Bus for Peer-to-Peer Agent Communication (2026-02-10)

**In-process message bus enabling direct agent-to-agent communication**:
- **MessageBus** (`src/agents/messaging.py`): Pure asyncio message bus with Strategy-pattern backends
  - Direct 1-to-1 messaging between agents
  - Named channels for group communication (pair channels, standup channels)
  - Broadcast to all registered agents
  - Pub/Sub topics with async handler callbacks
  - Request/Reply with timeout (uses `asyncio.Future`)
  - Message history with channel filtering and stats
- **Two backends**: `InProcessBackend` (default, zero dependencies) and `RedisBackend` (multi-process, uses redis.asyncio)
- **Frozen `Message` dataclass**: Immutable for safe concurrent access by multiple coroutines
- **`MessageType` enum**: DIRECT, CHANNEL, BROADCAST, REQUEST, REPLY, EVENT
- **`agent_id` property on BaseAgent**: Convenience alias for `config.role_id`; fixes pre-existing references in `sprint_manager.py`
- **BaseAgent messaging methods**: `send_message()`, `receive_message()`, `request_from()`, `subscribe_topic()` — all return None gracefully when no bus attached
- **Config**: `messaging:` YAML section with `backend`, `redis_url`, `history_size`, `log_messages`
- **SprintManager**: Creates bus at init, registers all agents, optionally writes `messages.json` to sprint artifacts
- **Ceremony integration**:
  - `pairing_codegen.py`: Creates pair channels, publishes `pair_progress` events (session_started/ended)
  - `daily_standup.py`: Creates standup channels, publishes `standup_decisions` topic after dev lead facilitation
- **SharedContextDB**: Added `_messages` store, `messages` table, `store_message()` and `get_messages()` methods
- **26 new tests**: 21 unit tests (`test_messaging.py`) + 5 integration tests (`test_messaging_integration.py`)
- **Test count**: 324 → 350 collected (344 passing, 3 skipped, 3 pre-existing e2e failures)

**Files changed**:
- `src/agents/messaging.py` — **NEW**: MessageBus, Message, Channel, backends, factory
- `tests/unit/test_messaging.py` — **NEW**: 21 unit tests
- `tests/integration/test_messaging_integration.py` — **NEW**: 5 integration tests
- `src/agents/base_agent.py` — `agent_id` property, `_message_bus`/`_inbox` fields, messaging convenience methods
- `src/orchestrator/config.py` — 4 messaging fields + YAML parsing
- `config.yaml` — `messaging:` section
- `src/orchestrator/sprint_manager.py` — Create bus, register agents, message artifact logging
- `src/agents/pairing_codegen.py` — Pair channels, progress events
- `src/orchestrator/daily_standup.py` — Accept bus, standup channels, decision broadcasts
- `src/tools/shared_context.py` — `_messages` store, `store_message()`, `get_messages()`, `messages` table

### Added - Complete Allowed Commands & Example Configurations (2026-02-10)

**Expanded `allowed_commands` from 15 to 48 commands**:
- Version control: Added `gh` (GitHub CLI), `glab` (GitLab CLI) for remote git integration
- Go: `go`, `gofmt`, `goimports`, `golangci-lint`
- Rust: `cargo` (build, test, format, lint)
- TypeScript: `npx`, `tsc` (added to existing `npm`, `node`)
- C++: `cmake`, `ctest`, `make`, `clang-format`, `clang-tidy`
- Python: Added `flake8` (was in bash.py defaults but missing from config.yaml)
- Shell utilities: `touch`, `cp`, `mv`, `rm`, `head`, `tail`, `wc`, `diff`, `sort`, `uniq`, `sed`, `awk`, `tree`, `env`, `which`, `tar`, `curl`, `wget`
- Updated hardcoded defaults in `src/tools/agent_tools/bash.py` to match

**5 example configuration pairs** (`examples/<name>/config.yaml` + `backlog.yaml`):
- `01-startup-mvp/` — 5-person Anthropic team, Python SaaS, no disturbances, 45-min sprints
- `02-enterprise-brownfield/` — Full 11-person vLLM team, Go+Python brownfield, GitHub PRs, full disturbances
- `03-oss-rust-library/` — 7-person hybrid team (seniors on Anthropic, juniors on vLLM), Rust, GitLab MRs
- `04-chaos-experiment/` — Full team, max disturbances, free profile swapping, turnover, 20 sprints
- `05-quick-demo/` — 3 agents, mock mode, 15-min sprints, trivial 3-story backlog

**Files changed**:
- `config.yaml` — Expanded `allowed_commands` (15 → 48)
- `src/tools/agent_tools/bash.py` — Updated hardcoded default allowlist to match
- `examples/01-startup-mvp/` — config.yaml + backlog.yaml (NoteKeep API)
- `examples/02-enterprise-brownfield/` — config.yaml + backlog.yaml (OrderFlow service)
- `examples/03-oss-rust-library/` — config.yaml + backlog.yaml (fastcache crate)
- `examples/04-chaos-experiment/` — config.yaml + backlog.yaml (StressApp platform)
- `examples/05-quick-demo/` — config.yaml + backlog.yaml (HelloAPI)

### Changed - Configurable Sprint Timing & Agent Time Awareness (2026-02-10)

**Wall-clock sprint duration now configurable (default: 60 min)**:
- `sprint_duration_minutes` in config.yaml now optional (defaults to 60 if omitted)
- New CLI flag `--duration <minutes>` overrides config value
- `ExperimentConfig` fields all have sensible defaults (no required positional args)

**Reduced simulated days from 10 to 5 (configurable)**:
- New config field `num_simulated_days` (default: 5) under `experiment` section
- At 60 min wall-clock, each simulated day now gets ~12 min instead of ~6 min
- Gives agents enough time for full implement → test → fix → commit cycles

**Agent time awareness — wall-clock deadlines passed to agents**:
- `sprint_end` and `day_end` deadlines computed in `run_development()` and threaded to agents
- `_build_implementation_prompt()` appends a `## Time Context` section with remaining minutes
- Agents see remaining time and get guidance: "If time is short, focus on completing a working MVP"
- Bridges the gap between scope-boxed AI agents and time-boxed agile sprints

**Files changed**:
- `src/orchestrator/config.py` — `sprint_duration_minutes` default 60, `num_simulated_days` field + parsing
- `src/orchestrator/main.py` — `--duration` CLI arg, passed to config override
- `src/orchestrator/sprint_manager.py` — configurable day count, `sprint_end` computation, deadline threading
- `src/agents/pairing_codegen.py` — `deadline`/`sprint_end` params, `## Time Context` prompt injection
- `config.yaml` — `num_simulated_days: 5`, `--duration` comment
- `tests/unit/test_config.py` — 4 new tests (2 for duration, 2 for simulated days)
- `tests/integration/test_sprint_zero_refinement.py` — updated day count assertions
- Documentation: CLAUDE.md, DESIGN_RATIONALE.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, sprint_planning.md

### Added - Pre-commit Hooks (2026-02-10)

**Automated Code Quality Gates**:
- **pre-commit framework**: `black`, `ruff`, and `mypy` run automatically on every commit
- **`pyproject.toml`**: Centralized tool configuration (line-length 88, ruff E/F/W rules, mypy non-strict)
- **`.pre-commit-config.yaml`**: Hook definitions using official repos (black, ruff-pre-commit) and local mypy
- **mypy**: Runs informational-only (non-blocking) due to 93 pre-existing type errors; remove `|| true` once resolved
- **ruff**: E501 (line length) ignored since black handles formatting
- **Dependencies**: Added `pre-commit==3.6.0` to `requirements.txt`

### Added - Research-Critical Test Coverage (2026-02-09)

**Profile Swapping Tests** (13 tests - Research Question 4):
- `test_swap_to_sets_swap_state` - Verify swap state creation
- `test_swap_to_modifies_prompt` - Swap notice added to prompt
- `test_swap_to_preserves_original_config` - Original config saved
- `test_is_swapped_property` - Property returns correct state
- `test_revert_swap_restores_config` - Config restoration
- `test_revert_swap_clears_state` - State cleanup
- `test_revert_swap_restores_prompt` - Prompt restoration
- `test_decay_swap_reduces_proficiency` - Proficiency decay over sprints
- `test_decay_swap_reverts_after_decay_period` - Auto-revert after threshold
- `test_multiple_swaps_only_preserve_first_original` - Prevent nested swap corruption
- `test_revert_when_not_swapped_is_safe` - Safe no-op when not swapped
- `test_decay_when_not_swapped_is_safe` - Safe no-op when not swapped
- `test_swap_proficiency_bounds` - Proficiency bounded at [0, 1]

**Meta-Learning Tests** (11 tests - Research Question 7):
- `test_write_meta_learning_to_jsonl` - JSONL append works
- `test_read_meta_learnings_filters_by_agent` - Agent-specific filtering
- `test_meta_learnings_loaded_in_prompt` - Learnings appear in prompt
- `test_multiple_learnings_accumulated` - Multiple learnings for same agent
- `test_empty_jsonl_returns_empty_string` - Handles missing file gracefully
- `test_malformed_jsonl_handled` - Skip bad lines, keep valid ones
- `test_meta_learning_sprint_tracking` - Sprint numbers preserved
- `test_meta_learning_types` - Keep/Drop/Puzzle types
- `test_prompt_reloads_after_new_learning` - Dynamic prompt reload
- `test_meta_learnings_format_in_prompt` - Correct formatting with context
- `test_meta_learnings_only_for_matching_agent` - No cross-agent pollution

**Impact**: These 24 tests validate the two core mechanisms for measuring team learning and adaptation:
- **Profile swapping** (RQ4: "Does profile-swapping break team dynamics?")
- **Meta-learning** (RQ7: "How does team maturity affect productivity?")

**Test Count**: 144 → 168 passing tests (+ 24 new tests)

### Fixed - Meta-Learning Resilience (2026-02-09)

**Bug Fix**: `BaseAgent._load_meta_learnings()` now handles malformed JSONL gracefully
- **Before**: Single malformed line caused all learnings to be discarded
- **After**: Malformed lines skipped per-line, valid learnings preserved
- **Change**: Moved `try/except json.JSONDecodeError` inside the loop (line-level error handling)
- **Impact**: Meta-learnings now robust against corruption (e.g., manual edits, truncated writes)

### Added - Specialist Consultant System (2026-02-09)

**External Expertise On-Boarding - Managed Knowledge Gaps**:
- **Specialist Consultant System**: Ability to bring in external experts when team lacks domain expertise
  - Maximum 3 consultations per sprint (enforced)
  - Velocity penalty of 2.0 story points per consultation (configurable cost)
  - Only activated when team genuinely lacks expertise for a blocker
- **Automatic Detection**: System detects expertise gaps based on blocker descriptions and team skills
  - Keywords trigger domain-specific specialists (ML, security, performance, cloud, etc.)
  - Checks team's specializations to avoid redundant consultations
- **Specialist Domains Available**:
  - `ml`: Machine Learning / AI (training, deployment, debugging)
  - `security`: Authentication, authorization, OWASP Top 10
  - `performance`: Optimization, profiling, benchmarking
  - `cloud`: AWS, GCP, Azure, Kubernetes
  - `architecture`: System design, scalability, patterns
- **Knowledge Transfer Flow**:
  1. Dev Lead identifies expertise gap blocker
  2. System creates temporary specialist agent with domain profile
  3. Specialist paired with junior/mid developer (learning opportunity)
  4. 1-day consultation: unblock issue, transfer knowledge, teach patterns
  5. Learnings recorded, velocity penalty applied
- **New Files**:
  - `src/orchestrator/specialist_consultant.py` - Core system implementation
  - `team_config/08_specialists/ml_specialist.md` - ML expert profile
  - `team_config/08_specialists/security_specialist.md` - Security expert profile
  - `tests/unit/test_specialist_consultant.py` - 6 comprehensive tests
- **Metrics**: `specialist_consultations_total`, `specialist_velocity_penalty` counters
- **Integration**: Wired into `SprintManager`, ready for automatic detection in daily standups
- **Research Impact**: Enables studying how teams handle knowledge gaps with controlled external help

### Added - Disturbance Detection & Observability (2026-02-09)

**Disturbance Detection System - Now Fully Operational**:
- **Flaky Test Detection**: Track test results across iterations, detect inconsistent pass/fail patterns
  - Wired in `src/agents/pairing_codegen.py` during test execution phase
  - Compares results from multiple test runs to identify non-deterministic failures
- **Test Failure Detection**: Automatic detection when max iterations reached without passing
  - Triggers after agents exhaust retry attempts
  - Records full iteration history for debugging
- **Merge Conflict Detection**: Catch and report merge conflicts during git operations
  - Wired in `src/codegen/workspace.py` during git pull operations
  - Detects "CONFLICT" markers in stderr, tags affected cards
- **Infrastructure**: Added `disturbance_engine` parameter to `CodeGenPairingEngine` and `WorkspaceManager`
- **Result**: Hybrid disturbance system fully operational (injection + natural detection)

**Custom Metrics - Recording Junior/Senior Dynamics**:
- `junior_questions_total` - Tracks questions asked by junior developers during story refinement
  - Recorded in `src/orchestrator/story_refinement.py`
  - Labels: `junior_id`, `category`, `resulted_in_change`
- `reverse_mentorship_events` - Tracks when juniors drive with senior navigators
  - Recorded in `src/agents/pairing_codegen.py`
  - Labels: `junior_id`, `senior_id`, `topic`
- **Impact**: Enables measurement of research question "Do juniors improve team outcomes?"

**Test Coverage Expansion - 342% Increase**:
- Expanded from 38 to 171 tests (133 new tests)
- Added 73 tests in TIER 2-4 (ceremonies, multi-language, metrics, remote git)
- Added 6 tests for specialist consultant system
- Added 24 tests for profile swapping and meta-learning (research-critical)
- All 30 TIER 1 tests (disturbances, pair rotation, conventions) already passing
- **Current Status**: 168 tests passing, 3 skipped (expected - tools not installed)

### Changed

**Multi-Language Tool Tests - Real Execution**:
- Enhanced `tests/unit/test_multi_language_formatter.py`:
  - Now executes actual Black, gofmt, rustfmt, prettier, clang-format
  - Added `@pytest.mark.skipif` decorators for missing tools
  - Verifies formatting changes are applied
- Enhanced `tests/unit/test_multi_language_linter.py`:
  - Now executes actual ruff, golangci-lint, clippy, eslint, clang-tidy
  - Tests verify tool execution succeeds
- **Result**: Placeholder assertions replaced with real tool integration tests

**Remote Git Tests - Mock-Based Integration**:
- Enhanced `tests/integration/test_remote_git.py`:
  - Added mocked `_run_command()` to simulate `gh pr create` output
  - Verifies PR URL parsing and number extraction
  - Validates CLI command construction (flags, arguments)
- **Result**: Structural placeholders replaced with behavior-driven tests

**Test Infrastructure**:
- Fixed all ceremony tests to use correct parameter names (`tasks_in_progress` not `in_progress_tasks`)
- Fixed return type assertions (dataclass types instead of dict)
- Fixed `RefinedStory` import in technical planning tests
- Updated workspace tests for git branch compatibility (main/master detection)

### Fixed
- Bug: `agent_id` attribute doesn't exist on `BaseAgent` - changed to `config.role_id` (17 occurrences across 3 files)
- Bug: Daily standup parameter mismatch - renamed to match API
- Bug: Coverage simulation formula - updated expected value from 85.0 to 89.0
- Bug: Git branch detection - added logic to detect main vs master
- Bug: Tool instantiation - changed `workspace=` to `workspace_root=` in tests

### Research Impact
- **Ecological Validity**: Natural disturbances now detected organically (not just injected)
- **Research Metrics**: Junior/senior dynamics now measurable via Prometheus
- **Tool Validation**: Multi-language support proven with real execution tests
- **Observability**: Full visibility into disturbance handling and team dynamics

---

## [1.3.0] - 2026-02-09

### Added - Agile Ceremonies: Complete Process Implementation

**2-Phase Sprint Planning**:
- Phase 1: Story Refinement (PO + Team) - Business context, clarification, estimation
- Phase 2: Technical Planning (Team only) - Task breakdown, architecture, dependencies, owner assignment
- `src/orchestrator/story_refinement.py` - StoryRefinementSession class
- `src/orchestrator/technical_planning.py` - TechnicalPlanningSession class
- `team_config/06_process_rules/sprint_planning.md` - Complete planning guide (~450 lines)

**Daily Standups**:
- Day-based simulation: 60 minutes wall-clock = 10 simulated days (2-week sprint)
- Daily standup every day except Day 1
- Focus: architectural alignment, cross-pair dependencies, Dev Lead facilitation
- `src/orchestrator/daily_standup.py` - DailyStandupSession class
- `team_config/06_process_rules/daily_standup.md` - Standup format guide (~380 lines)

**Pair Rotation Algorithm**:
- Round-robin with history tracking
- Task owner stays (provides continuity)
- Navigator rotates daily (everyone pairs with everyone)
- Includes testers + QA Lead (20% frequency)
- Max tasks = half team size
- `src/orchestrator/pair_rotation.py` - PairRotationManager class

**Sprint Review/Demo**:
- Team demonstrates completed stories to PO
- PO accepts/rejects against acceptance criteria
- Two-tier stakeholder feedback:
  - Fast loop (every sprint): PO represents stakeholders
  - Slow loop (every 5 sprints): Real stakeholders review asynchronously
- `src/orchestrator/sprint_review.py` - SprintReviewSession class
- `team_config/06_process_rules/sprint_review.md` - Review guide (~310 lines)
- `team_config/06_process_rules/retrospective.md` - Updated retrospective guide (~285 lines)

**Product Owner Role**:
- New role archetype: `team_config/01_role_archetypes/product_owner.md`
- Responsibilities: backlog management, story refinement, sprint review acceptance
- Individual personality: `team_config/05_individuals/sophia_rodriguez.md`

**Task Ownership and Dependencies**:
- Task owners provide continuity (stay on task until completion)
- Navigator rotates daily for knowledge transfer
- Simple dependency graph (task A blocks task B)
- Dev Lead coordinates handoffs in standups
- Sprint manager updated with task pull logic respecting dependencies

### Changed
- **Sprint Manager**: Major refactor for day-based simulation
  - `run_planning()` now calls Phase 1 + Phase 2
  - `run_development()` simulates 10 days with daily standups and pair rotation
  - `_run_day_pairing_sessions()` method for daily workflow
  - `_pull_task_for_owner()` respects dependencies
- **Time Simulation**: Explicit 20 min = 10 days mapping
- **Sprint Lifecycle**: Now includes Sprint 0 → Planning (2 phases) → Development (10 days) → QA → Review → Retro

### Documentation
- Updated `README.md` with Sprint 0 reference, PO mention, ceremony overview
- Updated `docs/USAGE.md` with ceremony sections (already comprehensive)
- Updated `docs/IMPLEMENTATION_STATUS.md` with full ceremony and Sprint 0 sections
- Created `CHANGELOG.md` for chronological feature tracking

---

## [1.2.0] - 2026-02-08

### Added - Sprint 0: Multi-Language Infrastructure Setup

**Sprint 0 Infrastructure Generation**:
- Automatic infrastructure story generation for Python, Go, Rust, TypeScript, C/C++
- Detects languages from `backlog.yaml` (`languages` field) and team specializations
- Generates stories for CI/CD, linters, formatters, testing, Docker, Kubernetes
- Greenfield: Complete infrastructure from scratch
- Brownfield: Analyze existing repo, generate stories only for gaps
- CI validation gate: Sprint 0 not complete until CI pipeline runs successfully
- `src/orchestrator/sprint_zero.py` - SprintZeroGenerator, BrownfieldAnalyzer

**Tool-Enforced Coding Standards**:
- Standards based on industry-standard tools (Black, Ruff, mypy, gofmt, rustfmt, clippy, prettier, eslint, clang-format)
- No verbose style guides - tools enforce conventions
- All agents know standards via `team_config/00_base/base_agent.md` "Coding Standards" section
- Per-language standard files:
  - `team_config/00_base/coding_standards/python.md` - Black (88 char), Ruff, mypy, pytest
  - `team_config/00_base/coding_standards/go.md` - gofmt, golangci-lint, go test
  - `team_config/00_base/coding_standards/rust.md` - rustfmt, clippy, cargo test
  - `team_config/00_base/coding_standards/typescript.md` - Prettier, ESLint, tsc strict, Jest
  - `team_config/00_base/coding_standards/cpp.md` - clang-format, clang-tidy, CTest

**Multi-Language Tools**:
- `src/tools/agent_tools/test_runner_multi.py` - MultiLanguageTestRunner (auto-detects language, runs appropriate test framework)
- `src/tools/agent_tools/formatter.py` - MultiLanguageFormatter (black/gofmt/rustfmt/prettier/clang-format)
- `src/tools/agent_tools/linter.py` - MultiLanguageLinter (ruff/golangci-lint/clippy/eslint/clang-tidy)
- `src/tools/agent_tools/builder.py` - MultiLanguageBuilder (pip/go mod/cargo/npm/cmake)
- All tools registered in `src/tools/agent_tools/factory.py`

**Convention Analyzer (Brownfield)**:
- `src/orchestrator/convention_analyzer.py` - ConventionAnalyzer class
- Detects existing coding conventions in brownfield repos
- Analyzes Python, Go, Rust, TypeScript, C++ configurations
- Generates augmented configs for missing tools
- Methods: `analyze_python()`, `analyze_go()`, `analyze_rust()`, `analyze_typescript()`, `analyze_cpp()`

**Language Specialist Agents**:
- 5 new senior language specialists added to team:
  - `liam_senior_python` - Enthusiastic, pragmatic (Python + backend)
  - `maya_senior_golang` - Direct, systems-thinker (Go + backend)
  - `kai_senior_rust` - Meticulous, safety-conscious (Rust + systems)
  - `aria_senior_typescript` - User-focused, passionate (TypeScript + frontend)
  - `dmitri_senior_cpp` - Performance-obsessed (C++ + systems)
- Specialization profiles:
  - `team_config/03_specializations/python_specialist.md` - Type hints, async, testing patterns
  - `team_config/03_specializations/golang_specialist.md` - Concurrency, interfaces, error handling
  - `team_config/03_specializations/rust_specialist.md` - Ownership, lifetimes, type system
  - `team_config/03_specializations/typescript_specialist.md` - Types, React/Node patterns
  - `team_config/03_specializations/cpp_specialist.md` - Modern C++17/20/23, templates
- Individual personalities:
  - `team_config/05_individuals/liam_obrien.md`
  - `team_config/05_individuals/maya_patel.md`
  - `team_config/05_individuals/kai_anderson.md`
  - `team_config/05_individuals/aria_cohen.md`
  - `team_config/05_individuals/dmitri_volkov.md`

### Changed
- **Main Loop**: Sprint loop now starts at 0 instead of 1 (`src/orchestrator/main.py`)
- **Backlog Schema**: Extended with `ProductMetadata` dataclass (`src/orchestrator/backlog.py`)
  - Fields: `languages`, `tech_stack`, `repository_type`, `repository_url`
- **Sprint Manager**: Added `_run_sprint_zero()`, `_run_planning_sprint_zero()`, `_validate_ci_pipeline()` methods
- **Base Agent**: Updated with comprehensive "Coding Standards" section referencing all language tools

### Documentation
- Updated `README.md` with Sprint 0 overview
- Updated `docs/USAGE.md` (already comprehensive)
- Added Sprint 0 section to `docs/IMPLEMENTATION_STATUS.md`

---

## [1.1.0] - 2026-02-07

### Added - Remote Git Integration & Brownfield Support

**Remote Git Integration**:
- Push code to GitHub/GitLab, create pull requests, QA approval, auto-merge
- `src/tools/agent_tools/remote_git.py` - RemoteGitProvider abstract base, GitHubProvider, GitLabProvider
- `src/tools/agent_tools/git.py` - Added GitRemoteTool, GitPushTool
- GitHub: Single service account + per-agent git attribution
- GitLab: Per-agent tokens for self-hosted instances
- PR/MR URLs stored in kanban card metadata
- QA approval via `gh pr review --approve` or `glab mr approve`
- Auto-merge when card moves to done

**Brownfield Development**:
- Clone existing repositories and build incrementally
- Workspace modes: `per_story` (greenfield) vs `per_sprint` (brownfield)
- Clone modes: `fresh` (delete/recreate) vs `incremental` (reuse/pull)
- Cross-sprint persistence: `copy_workspace_to_next_sprint()`
- Merge to main: `merge_to_main()` for completed features
- `src/codegen/workspace.py` - Enhanced WorkspaceManager

### Changed
- **Workspace Manager**: Refactored to support greenfield/brownfield modes
- **Sprint Manager**: Added `_approve_pr_if_exists()`, `_merge_pr_if_exists()` methods
- **Pairing Engine**: Added `_push_and_create_pr()` method
- **Database Schema**: Added `metadata JSONB` column to `kanban_cards` table

### Configuration
- Added `remote_git` section to `config.yaml`:
  - `enabled`, `provider`, `github`, `gitlab`, `author_email_domain`
- Extended `code_generation` section:
  - `workspace_mode`, `persist_across_sprints`, `merge_completed_stories`
  - `repo_config` with `url`, `branch`, `clone_mode`

### Documentation
- Added Remote Git Integration & Brownfield Support sections to `docs/IMPLEMENTATION_STATUS.md`
- Updated `docs/USAGE.md` with complete remote git and brownfield guides

---

## [1.0.0] - 2026-02-06

### Added - Initial Release: Tool-Using Agents & Code Generation

**Core System**:
- 11-agent software development team (1 Dev Lead, 1 QA Lead, 6 Developers, 2 Testers)
- 8-layer compositional agent profiles:
  1. Base (`00_base/base_agent.md`)
  2. Role Archetype (`01_role_archetypes/`)
  3. Seniority (`02_seniority/`)
  4. Specializations (`03_specializations/`)
  5. Domain Knowledge (`04_domain_knowledge/`)
  6. Individual Personality (`05_individuals/`)
  7. Demographics (from config.yaml)
  8. Meta-Learnings (`07_meta/meta_learnings.jsonl`)

**Runtime System**:
- Abstract runtime interface (`src/agents/runtime/base.py`)
- VLLMRuntime: Offline vLLM with XML-based tool calling
- AnthropicRuntime: Online Claude API with native tool use
- Three deployment modes: offline, online, hybrid
- Mock mode for testing (no LLM calls)

**Tool System**:
- Base tool interface (`src/tools/agent_tools/base.py`)
- Filesystem tools (5): read, write, edit, list, search
- Git tools (6): status, diff, add, commit, branch, log
- Bash tool: Sandboxed shell execution
- Test runner tools: RunTestsTool, RunBDDTestsTool (pytest integration)
- Tool registry and factory (`src/tools/agent_tools/factory.py`)

**Code Generation Workflow**:
- Workspace management: Per-sprint/story git workspaces
- BDD/Gherkin generation from user stories
- CodeGenPairingEngine: BDD → implement → test → commit workflow
- Test execution with iteration loop (max 3 attempts)
- Git commits with feature branches
- Kanban integration (move to review after commit)

**Sprint Lifecycle**:
- Planning: PO selects stories from backlog
- Disturbance injection (7 types): dependency breaks, production incidents, flaky tests, scope creep, junior misunderstandings, architectural debt, merge conflicts
- Development: Pairing sessions with real code generation
- QA review: QA lead approves/rejects
- Retrospective: Keep/Drop/Puzzle format
- Meta-learning: Learnings extracted and stored in JSONL

**Team Culture**:
- Lead Dev profile: Guru-level, navigator preference, team growth focus
- Git workflow: Stable main + gitflow, merge conflict resolution
- Hiring protocol: 3-round process with pairing under pressure
- Role-based pairing: Lead dev navigates, testers navigate, seniors mentor
- Turnover simulation (optional, >5 months)
- Tester pairing (20% frequency)

**Kanban Board**:
- WIP limits (4 in-progress, 2 review)
- Card states: ready, in_progress, review, done
- Snapshots and transition tracking
- Process coverage simulation

**Quality & Metrics**:
- Test coverage simulation (process-based, 70-95%)
- Prometheus metrics (velocity, coverage, pairing sessions)
- Profile swapping (swap/revert/decay mechanics)
- Blast radius controls for disturbances

**Testing**:
- 24 tests: 10 unit + 8 integration + 6 qualification
- All tests passing
- Mock mode works for all components

### Configuration
- `config.yaml`: Experiment settings, team constraints, disturbances, runtimes, agents
- `backlog.yaml`: Product backlog with user stories, acceptance criteria
- `team_config/`: 8-layer compositional profiles, process rules

### Documentation
- `README.md` - Project overview, quick start
- `CONTRIBUTING.md` - Contribution guide
- `CLAUDE.md` - Development guide for AI assistants
- `docs/ARCHITECTURE.md` - System architecture
- `docs/USAGE.md` - Configuration and usage guide
- `docs/IMPLEMENTATION_STATUS.md` - Implementation status
- `docs/AGENT_RUNTIMES.md` - Runtime system design
- `docs/META_LEARNING.md` - Meta-learning system
- `docs/RESEARCH_QUESTIONS.md` - Research hypotheses

---

## Research Impact

This project enables research into:
1. **AI Team Collaboration**: Can LLMs form effective collaborative teams?
2. **Seniority Dynamics**: Do agent seniority levels create realistic dynamics?
3. **Team Maturity**: How does team maturity affect productivity?
4. **Disturbance Handling**: Are disturbances handled realistically?
5. **Profile Swapping**: Does profile-swapping break team dynamics?
6. **Multi-Language Development**: Do AI teams choose appropriate tooling?
7. **Agile Process Effectiveness**: How well do ceremonies work with AI agents?
8. **Stakeholder Feedback Dynamics**: Fast vs slow feedback loops

---

## Version History Summary

- **v1.3.0** (2026-02-09): Agile ceremonies (2-phase planning, standups, sprint review, pair rotation)
- **v1.2.0** (2026-02-08): Sprint 0 multi-language infrastructure, language specialists
- **v1.1.0** (2026-02-07): Remote git integration, brownfield support
- **v1.0.0** (2026-02-06): Initial release with tool-using agents and code generation

---

## Links

- [GitHub Repository](https://github.com/witlox/agile-agent-team)
- [Documentation](docs/)
- [Research Questions](docs/RESEARCH_QUESTIONS.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Usage Guide](docs/USAGE.md)
