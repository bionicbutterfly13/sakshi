```markdown
# sakshi Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `sakshi` Python codebase. You'll learn how to implement new features, fix bugs, write tests, and maintain documentation in a consistent and collaborative manner. The repository favors clear commit messages, modular code, and a documentation-driven approach.

## Coding Conventions

- **File Naming:**  
  Use camelCase for Python files.  
  _Example:_  
  ```
  sakshi/recovery/hinting.py
  sakshi/dataLoader.py
  ```

- **Import Style:**  
  Use relative imports within the package.  
  _Example:_  
  ```python
  from .utils import parseConfig
  from ..core import BaseHandler
  ```

- **Export Style:**  
  Use named exports (define `__all__` in modules when needed).  
  _Example:_  
  ```python
  __all__ = ["RecoveryHint", "HintGenerator"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with these prefixes:
    - `feat`: New features
    - `fix`: Bug fixes
    - `chore`: Maintenance or tooling
  _Example:_  
  ```
  feat: add hinting logic for recovery
  fix: correct typo in dataLoader
  chore: update dependencies
  ```

## Workflows

### Feature Implementation with Docs and Tests
**Trigger:** When adding a new feature or significant capability  
**Command:** `/new-feature`

1. Update or create implementation code in `sakshi/`  
   _Example:_  
   ```
   sakshi/recovery/hinting.py
   ```
2. Update or create corresponding `__init__.py` files if needed.
3. Update or create documentation in `docs/api/` and `docs/architecture.md`.
4. Update `CHANGELOG.md` with a summary of the new feature.
5. Update `mkdocs.yml` if new documentation files are added.
6. Add or update tests in `tests/unit/`  
   _Example:_  
   ```
   tests/unit/hinting.test.py
   ```
7. Update `pyproject.toml` or `uv.lock` if dependencies change.

### Bugfix with Docs and Tests
**Trigger:** When fixing a bug in an existing feature  
**Command:** `/bugfix`

1. Modify implementation code in `sakshi/`  
   _Example:_  
   ```
   sakshi/recovery/hinting.py
   ```
2. Update documentation in `docs/api/` and `docs/architecture.md` if necessary.
3. Update `CHANGELOG.md` with a summary of the fix.
4. Add or update tests in `tests/unit/`  
   _Example:_  
   ```
   tests/unit/hinting.test.py
   ```

## Testing Patterns

- **Test Framework:** Not explicitly specified; use standard Python testing (e.g., `unittest` or `pytest`).
- **Test File Naming:**  
  Test files use the pattern `*.test.*` and are located in `tests/unit/`.  
  _Example:_  
  ```
  tests/unit/hinting.test.py
  ```
- **Test Example:**  
  ```python
  import unittest
  from sakshi.recovery.hinting import RecoveryHint

  class TestRecoveryHint(unittest.TestCase):
      def test_hint_generation(self):
          hint = RecoveryHint("example")
          self.assertEqual(hint.generate(), "Expected Output")
  ```

## Commands

| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /new-feature | Start a new feature with docs and tests      |
| /bugfix      | Start a bugfix with docs and tests           |
```
