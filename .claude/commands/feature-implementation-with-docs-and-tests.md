---
name: feature-implementation-with-docs-and-tests
description: Workflow command scaffold for feature-implementation-with-docs-and-tests in sakshi.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-implementation-with-docs-and-tests

Use this workflow when working on **feature-implementation-with-docs-and-tests** in `sakshi`.

## Goal

Implements a new feature, updating documentation, changelog, code, and tests.

## Common Files

- `sakshi/**/*.py`
- `docs/api/*.md`
- `docs/architecture.md`
- `CHANGELOG.md`
- `mkdocs.yml`
- `tests/unit/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update or create implementation code in sakshi/ (e.g., sakshi/recovery/hinting.py)
- Update or create corresponding __init__.py files if needed
- Update or create documentation in docs/api/ and docs/architecture.md
- Update CHANGELOG.md
- Update mkdocs.yml if new docs are added

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.