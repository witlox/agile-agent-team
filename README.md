# Agile Agent Team Experiment

A multi-agent AI system that operates as a mature, high-performing software development team that **produces actual working code**.

**_Critical remark:_** this whole thing is generated using AI, it stems from conversations with Claude to setup the premise and test the hypotheses.
Any code that is in this repo is AI generated as well, the experiment is thus 2-fold :)

## Overview

This project implements an 11-agent that operates like a real software development team and **generates real, tested code**:

- **1 Dev Lead** + **1 QA Lead** + **1 Product Owner**
- **6 Developers** (2 senior, 2 mid-level, 2 junior)
- **2 Testers** (integration + E2E)

Agents follow XP practices (pair programming, TDD, CI), use a Kanban board with WIP limits, and generate BDD-driven code through tool use (filesystem, git, bash, pytest). They can target existing codebases (brownfield) or start fresh (greenfield), and optionally push to GitHub/GitLab with automated PR workflows.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/witlox/agile-agent-team
cd agile-agent-team
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install

# Run 3 sprints in mock mode (no LLM/GPU/DB required, agents still generate real code)
MOCK_LLM=true python -m src.orchestrator.main \
  --sprints 3 \
  --output /tmp/test-run \
  --db-url mock://

# Continue the experiment for 2 more sprints (resumes from sprint 4)
MOCK_LLM=true python -m src.orchestrator.main \
  --continue 2 \
  --output /tmp/test-run \
  --db-url mock://

# View generated code
ls -la /tmp/agent-workspace/sprint-01/*/

# Run tests
pytest
```

For deployment with live LLMs (vLLM offline, Anthropic online, or hybrid), see **[docs/USAGE.md](docs/USAGE.md)**.

## How It Works

Each sprint (60 minutes wall-clock, simulating 2 weeks) follows this lifecycle:

1. **Sprint 0** (first run only) — Infrastructure setup: CI/CD, linters, formatters, Docker
2. **Planning** — PO selects stories from `backlog.yaml`, team breaks them into tasks
3. **Development** — Pairs implement features using BDD (Gherkin → code → test → commit)
4. **QA Review** — QA lead approves/rejects; optional PR creation on GitHub/GitLab
5. **Retrospective** — Keep/Drop/Puzzle analysis, meta-learnings stored per agent
6. **Disturbances** — Random failures injected (flaky tests, scope creep, incidents)

Work is defined in `backlog.yaml` as user stories with acceptance criteria and optional BDD scenarios. See **[docs/USAGE.md](docs/USAGE.md)** for the full configuration reference.

## Documentation

| Document | Description |
|----------|-------------|
| **[docs/USAGE.md](docs/USAGE.md)** | Usage guide: deployment modes, configuration, remote git, code generation |
| **[docs/ADVANCED_USAGE.md](docs/ADVANCED_USAGE.md)** | Advanced usage: disturbances, profile swapping, metrics, multi-team orchestration |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System architecture: components, agent composition, runtime system, data flow |
| **[docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)** | Implementation status, test breakdown, current capabilities |
| **[docs/RESEARCH_QUESTIONS.md](docs/RESEARCH_QUESTIONS.md)** | Research hypotheses, measurement approaches, expected patterns |
| **[docs/SPRINT_ZERO.md](docs/SPRINT_ZERO.md)** | Sprint 0 multi-language infrastructure setup |
| **[docs/AGENT_RUNTIMES.md](docs/AGENT_RUNTIMES.md)** | Runtime system design (vLLM, Anthropic, hybrid) |
| **[docs/META_LEARNING.md](docs/META_LEARNING.md)** | Meta-learning system: JSONL storage, dynamic prompt evolution |
| **[docs/TEAM_CULTURE.md](docs/TEAM_CULTURE.md)** | Team culture modeling: pairing, git workflow, hiring protocol |
| **[docs/DESIGN_RATIONALE.md](docs/DESIGN_RATIONALE.md)** | Design decisions and trade-offs |
| **[CLAUDE.md](CLAUDE.md)** | Development guide for contributors and AI assistants |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Contribution guidelines |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and feature tracking |

## Research Questions

This experiment explores whether AI agents can form effective collaborative teams. Key hypotheses:

1. **Dialogue-driven pairing** produces better code than solo agents
2. **Junior agents learn measurably** from pairing with seniors
3. **Velocity follows a maturity curve** (growth → stabilization)
4. **Disturbances are handled realistically** under process constraints
5. **Profile-swapping** increases velocity but reduces learning

See **[docs/RESEARCH_QUESTIONS.md](docs/RESEARCH_QUESTIONS.md)** for detailed hypotheses, measurement approaches, and expected patterns.

## Project Structure

```
src/
├── orchestrator/       # Sprint lifecycle, planning, standups, reviews
├── agents/             # Agent system, pairing engines, runtimes
├── codegen/            # Workspace management, BDD generation
├── tools/              # Kanban, shared context, agent tools
└── metrics/            # Prometheus metrics

team_config/            # 8-layer compositional agent profiles
├── 00_base/            # Universal behavior + coding standards
├── 01_role_archetypes/ # Developer / Tester / Leader
├── 02_seniority/       # Junior / Mid / Senior patterns
├── 03_specializations/ # Domain expertise
├── 04_domain_knowledge/# Deep technical knowledge
├── 05_individuals/     # Personalities
├── 06_process_rules/   # XP, Kanban, pairing, git workflow
├── 07_meta/            # Meta-learnings (JSONL)
└── 08_specialists/     # External consultant profiles

tests/                  # Unit / integration / qualification
examples/               # 6 example config+backlog pairs
config.yaml             # Experiment + runtime + tool configuration
backlog.yaml            # Product backlog with BDD scenarios
```

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full component deep dive.

## License

MIT License — see [LICENSE](LICENSE)

## Citation

If you use this in research, please cite:

```bibtex
@software{agile_agent_team,
  title={Agile Agent Team: Multi-Agent Simulation of Software Development},
  author={Pim Witlox},
  year={2026},
  url={https://github.com/witlox/agile-agent-team}
}
```

## Acknowledgments

- Inspired by real-world agile teams and XP practices
- Built on vLLM, Qwen, DeepSeek, and other open-source models
- Thanks to the AI agent research community
