# Python Coding Standards

## Enforced by Tools

All Python code MUST conform to these tool-enforced standards:

### 1. PEP 8 (Style Guide)
- Official Python style guide
- Enforced by: **ruff** (replaces flake8)
- Key rules:
  - 4 spaces for indentation (never tabs)
  - `snake_case` for functions/variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants

### 2. Black (Formatter)
- **Line length**: 88 characters
- **String quotes**: Double quotes `"` (auto-normalized)
- **Trailing commas**: Added in multi-line structures
- Run: `black .` (auto-formats entire codebase)
- **NO CONFIGURATION** - Black is intentionally opinionated

### 3. Ruff (Linter)
- Modern, fast linter (replaces flake8, isort, pyupgrade)
- Default rules: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort)
- Recommended additions: `N` (pep8-naming), `W` (pycodestyle warnings)
- Run: `ruff check .`
- Config in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
```

### 4. mypy (Type Checker)
- **All functions MUST have type hints**
- Strict mode recommended: `disallow_untyped_defs = true`
- Run: `mypy .`
- Config in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
disallow_untyped_defs = true
```

### 5. pytest (Testing)
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- **Coverage requirement**: ≥85% line coverage
- Run: `pytest --cov=src --cov-report=term-missing`

## Non-Negotiable Patterns

### Import Order (Enforced by ruff/isort)
```python
# 1. Standard library
import os
import sys

# 2. Third-party
import requests
from sqlalchemy import create_engine

# 3. Local
from .models import User
from ..utils import logger
```

### Type Hints (Required)
```python
from typing import Optional, List, Dict

def get_user(user_id: int) -> Optional[User]:
    """Retrieve user by ID."""
    pass

def process_items(items: List[str]) -> Dict[str, int]:
    """Process items and return counts."""
    pass
```

### Error Handling (Standard Pattern)
```python
# Always use specific exceptions
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    return None
```

### Docstrings (Google Style)
```python
def calculate_total(items: List[Item], tax_rate: float) -> float:
    """Calculate total price including tax.

    Args:
        items: List of items to calculate total for.
        tax_rate: Tax rate as decimal (e.g., 0.15 for 15%).

    Returns:
        Total price including tax.

    Raises:
        ValueError: If tax_rate is negative.
    """
    pass
```

## Toolchain Commands

```bash
# Format code (ALWAYS run before commit)
black .

# Lint code
ruff check .

# Type check
mypy .

# Run tests with coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# All checks (CI pipeline)
black --check . && ruff check . && mypy . && pytest
```

## Deviations Allowed Only For

1. **Line length**: Can exceed 88 chars for:
   - Long URLs in comments
   - Import statements that can't be broken

2. **Type hints**: Can be omitted for:
   - Simple scripts (<50 lines)
   - Obvious types in small private functions

3. **Test coverage**: Can be <85% for:
   - Defensive error handling branches
   - Platform-specific code

**All deviations MUST be justified in code review comments.**
