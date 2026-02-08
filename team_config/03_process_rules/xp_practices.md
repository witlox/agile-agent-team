# Extreme Programming (XP) Practices

## Core Practices in Use

### 1. Test-Driven Development (TDD)
**Write tests before code. Always.**

```
Red → Green → Refactor
```

- **Red**: Write a failing test
- **Green**: Write minimal code to pass
- **Refactor**: Improve design while keeping tests green

### 2. Pair Programming
**All production code is written in pairs.**

- Driver writes code
- Navigator reviews strategy
- Rotate every 30 minutes
- Continuous dialogue and design discussion

### 3. Continuous Integration
**Integrate code multiple times per day.**

- Commit to shared repository frequently
- Run full test suite on every commit
- Fix broken builds immediately
- Keep main branch always deployable

### 4. Simple Design
**Do the simplest thing that could possibly work.**

- YAGNI: You Aren't Gonna Need It
- No speculative generality
- Refactor when patterns emerge, not before

### 5. Refactoring
**Continuously improve code design.**

- Small, incremental improvements
- Always keep tests passing
- No "refactoring sprints" - it's ongoing

### 6. Collective Code Ownership
**Anyone can improve any code.**

- No "this is my module" mentality
- Share knowledge through pairing
- Review and improve each other's work

### 7. Coding Standards
**Consistent code style across team.**

- Follow agreed conventions
- Use linters and formatters
- Readability over cleverness

## Practices NOT in Use (For This Experiment)

- ~~On-site customer~~ (PO represents customer)
- ~~40-hour week~~ (Not applicable to AI agents)
- ~~Open workspace~~ (Virtual team)

## Enforcement

The orchestrator enforces:
- Pairing protocol (blocks solo production commits)
- TDD cycle integrity
- Test coverage thresholds

The team self-enforces:
- Code quality through review
- Simple design through refactoring
- Standards through collaboration
