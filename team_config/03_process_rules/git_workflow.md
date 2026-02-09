# Git Workflow — Stable Main + Gitflow

## Core Principle

**Main is always stable, always deployable, always green.**

This is the one non-negotiable rule. Every commit on `main` must pass all tests, meet quality gates, and be production-ready.

## Workflow Overview

```
main (stable, always green)
  ↓
feature/us-001-user-registration (your work)
  ↓
Pull Request → Code Review → Merge to main
```

## Branch Strategy

### Main Branch
- **Always deployable**: Every commit on main can go to production
- **Always green**: All tests pass, CI/CD passes, quality gates met
- **Protected**: No direct commits—only via PR with approval
- **Single source of truth**: Deployments only from main

### Feature Branches
- **Naming convention**: `feature/<story-id>-<short-description>`
  - Example: `feature/us-001-user-registration`
  - Example: `feature/bug-123-fix-login-timeout`
- **Created from**: Latest `main`
- **Lifespan**: Short-lived (1 sprint max)
- **Ownership**: Created by pairing session, owned by pair

### Hotfix Branches (Incidents)
- **Naming convention**: `hotfix/<incident-id>-<description>`
- **Created from**: `main`
- **Merged back to**: `main` immediately after fix
- **Priority**: Blocks all other work until resolved

## Development Flow

### 1. Start New Story/Task

```bash
# Pull latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/us-001-user-registration

# Commit work in small increments
git add src/auth/registration.py tests/test_registration.py
git commit -m "Add: user registration with email validation"

# Push to remote
git push -u origin feature/us-001-user-registration
```

### 2. Keep Feature Branch Updated

```bash
# Regularly rebase on main to avoid large merge conflicts
git checkout main
git pull origin main
git checkout feature/us-001-user-registration
git rebase main

# Resolve any conflicts (see Merge Conflict Resolution below)
```

### 3. Create Pull Request

**Before creating PR:**
- ✅ All tests pass locally
- ✅ Code follows style guide (black, ruff, mypy)
- ✅ No debug code, print statements, or TODOs
- ✅ Feature complete per acceptance criteria
- ✅ Self-reviewed the diff

**PR description template:**
```markdown
## Story
[US-001] User registration

## Changes
- Implemented user registration endpoint
- Added email validation
- Added bcrypt password hashing
- Added duplicate email check

## Testing
- Unit tests: test_registration.py (5 tests, all passing)
- Manual testing: Postman collection attached
- Edge cases covered: empty email, invalid format, duplicate email

## Acceptance Criteria
- [x] Email format validated
- [x] Password hashed with bcrypt
- [x] Duplicate email rejected with clear error
- [x] Welcome email sent on success
```

### 4. Code Review

**Reviewers:**
- Minimum 1 approval required (usually the pairing partner or lead dev)
- Lead dev reviews if complex architecture changes
- Testers review if significant test coverage changes

**Review criteria:**
- Correctness: Does it work?
- Tests: Are there tests? Do they cover edge cases?
- Clarity: Is the code readable?
- Performance: Any obvious bottlenecks?
- Security: Any vulnerabilities?

### 5. Merge to Main

```bash
# After approval, merge via GitHub/GitLab UI
# OR via command line:
git checkout main
git pull origin main
git merge --no-ff feature/us-001-user-registration
git push origin main

# Delete feature branch (cleanup)
git branch -d feature/us-001-user-registration
git push origin --delete feature/us-001-user-registration
```

## Merge Conflict Resolution

### When Conflicts Occur

Merge conflicts are **normal and expected**—they happen when:
- Multiple pairs work on related code
- Feature branch hasn't been rebased recently
- Simultaneous changes to shared files

**Mindset**: Conflicts are not failures—they're coordination points.

### Resolution Protocol

#### 1. Don't Panic
- Conflicts are solvable
- You're not alone—ask for help
- The original authors of conflicting code can help

#### 2. Identify the Conflict

```bash
# During rebase, git will show conflicting files
git status

# Shows:
# Unmerged paths:
#   both modified:   src/auth/user.py
```

#### 3. Understand Both Sides

**Open the conflicting file:**
```python
<<<<<<< HEAD (your changes)
def register_user(email, password):
    if not validate_email(email):
        raise ValueError("Invalid email")
    # Your implementation
=======
def register_user(email, password, username):
    # Their implementation with username parameter
>>>>>>> main
```

**Ask questions:**
- What was the other pair trying to achieve?
- Why did they change this code?
- Can both changes coexist?
- Should we refactor to avoid the conflict?

#### 4. Resolve Together (Preferred)

**Best practice**: Pair with the author of the conflicting code

1. Find the other pair (via git blame or PR history)
2. Schedule a quick pairing session (15-30 min)
3. Resolve conflict together, understanding both approaches
4. Decide on unified approach (may be better than either original)

**Lead dev available**: For complex conflicts, escalate to lead dev

#### 5. Resolve Solo (If Authors Unavailable)

If you must resolve alone:
1. Read the other PR/commit to understand intent
2. Preserve their functionality if possible
3. Test both code paths after resolution
4. Ask for review from conflicting author before merging
5. Add tests to cover the merged behavior

#### 6. Verify Resolution

```bash
# After resolving conflicts in editor
git add src/auth/user.py
git rebase --continue

# Run full test suite
pytest

# Verify no regressions
```

### Complex Conflict Escalation

**When to escalate to lead dev:**
- Architectural conflicts (different design approaches)
- Affects > 5 files
- You don't understand the other code
- Performance or security implications
- Stuck > 1 hour

**Lead dev's role:**
- Facilitates discussion between both pairs
- Explains architectural intent
- Proposes refactor if needed
- Makes final decision if no consensus

## "You Break It, You Fix It" Culture

### The Rule

**If you break the build, you own the fix.**

"Breaking the build" means:
- Tests fail on `main` after your merge
- CI/CD pipeline fails
- Production deployment fails
- Quality gates fail (coverage, lint, type checks)

### But Everyone Helps

**Critical**: This is not punishment—it's ownership with support.

- **Immediate notification**: CI alerts the pair who merged
- **Lead dev pairs**: Drop everything to pair with you on the fix
- **Team support**: Anyone can help debug
- **Blameless**: Focus on "how did this pass locally but fail in CI?"

### Fix Process

1. **Acknowledge**: "I broke the build, I'm on it"
2. **Diagnose**: Pair with lead dev or senior to understand failure
3. **Fix options**:
   - **Quick fix** (< 30 min): Fix forward, push to main
   - **Complex fix** (> 30 min): Revert the merge, fix in new PR
4. **Verify**: CI passes, all tests green
5. **Post-mortem** (optional): "What can we learn? How do we prevent this?"

### Lead Dev's Response

> "You broke the build? Good—that's how we learn where the gaps are. Let's fix it together and add a test so it never breaks this way again."

**Actions**:
- Pairs immediately to fix (navigator role—teaches debugging)
- Adds missing tests to prevent recurrence
- Identifies systemic issues (e.g., "we need integration tests")
- **Never blames**—"We fix systems, not people"

### Post-Mortem (Blameless)

After build is fixed, optional team discussion:
- **What happened?** (facts, no blame)
- **Why did it pass locally but fail in CI?**
- **What can we learn?**
- **How do we prevent this?** (better tests, pre-commit hooks, etc.)
- **Action items** (assigned, tracked)

## Commit Message Standards

### Format

```
<type>: <summary> (<story-id>)

<optional body>

<optional footer>
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring
- `test:` - Add or update tests
- `docs:` - Documentation only
- `chore:` - Build, dependencies, tooling

### Examples

```
feat: implement user registration endpoint (US-001)

- Add email validation
- Hash passwords with bcrypt
- Check for duplicate emails
- Send welcome email

Resolves #123
```

```
fix: prevent race condition in concurrent registrations (BUG-045)

Added database-level unique constraint on email column to prevent
duplicate registrations when requests arrive simultaneously.
```

```
refactor: extract email validation to shared utility (TECH-012)

Email validation logic was duplicated across registration and
password reset flows. Extracted to validators/email.py for reuse.
```

## CI/CD Integration

### Pre-Merge Checks (Automated)

- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Code coverage ≥ 85%
- ✅ Linter passes (ruff)
- ✅ Type checker passes (mypy)
- ✅ Code formatter passes (black)
- ✅ No security vulnerabilities (bandit, safety)

### Post-Merge (Main Branch)

- ✅ All pre-merge checks
- ✅ Deploy to staging automatically
- ✅ Run E2E tests on staging
- ✅ Performance benchmarks within limits
- ✅ Tag release if all pass

## Git Best Practices

### DO

- ✅ Commit often (small, logical chunks)
- ✅ Write clear commit messages
- ✅ Rebase feature branches on main frequently
- ✅ Run tests before pushing
- ✅ Review your own diff before creating PR
- ✅ Keep feature branches short-lived (< 1 sprint)
- ✅ Delete merged branches

### DON'T

- ❌ Commit directly to main (always use PR)
- ❌ Force push to shared branches
- ❌ Commit secrets, credentials, or .env files
- ❌ Commit large binary files
- ❌ Commit debug code, print statements, or commented code
- ❌ Merge with failing tests
- ❌ Use `git push --force` on main (ever!)

## Emergency Procedures

### Revert a Bad Merge

```bash
# If bad code made it to main, revert immediately
git revert <commit-hash>
git push origin main

# Then fix properly in new PR
```

### Hotfix for Production Incident

```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/incident-789-fix-auth-timeout

# Make fix
git add src/auth/timeout.py tests/test_timeout.py
git commit -m "fix: increase auth timeout to 30s (INC-789)"

# Push and create PR (expedited review)
git push -u origin hotfix/incident-789-fix-auth-timeout

# After approval, merge immediately
# Deploy to production ASAP
```

## Tools Integration

### Agents Working with Git

When agents (pair programmers) work with git, they:

1. **Always create feature branches** per story
2. **Commit incrementally** (after each checkpoint)
3. **Write clear commit messages** (following format)
4. **Run tests before committing** (via run_tests tool)
5. **Use git tools**:
   - `git_status` - Check working tree
   - `git_diff` - Review changes
   - `git_add` - Stage files
   - `git_commit` - Commit with message

### Workspace Manager Integration

The `WorkspaceManager` automatically:
- Creates git repo with `main` branch
- Creates feature branch for each story: `feature/<story-id>`
- Configures git user: "Agile Agent Team <agents@example.com>"
- Initializes with README commit
- Ready for agent tool use

## Summary

**Core principle**: Main is stable—always green, always deployable.

**Workflow**: Feature branches → PR → Review → Merge → Main

**Conflicts**: Normal, expected, resolved together

**Build breaks**: You own the fix, but everyone helps

**Quality**: Non-negotiable—tests, lint, coverage, reviews

**Culture**: Blameless, supportive, learning-focused
