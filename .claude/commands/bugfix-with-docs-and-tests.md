---
name: bugfix-with-docs-and-tests
description: Workflow command scaffold for bugfix-with-docs-and-tests in sakshi.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /bugfix-with-docs-and-tests

Use this workflow when working on **bugfix-with-docs-and-tests** in `sakshi`.

## Goal

Fixes a bug and updates related documentation, changelog, and tests.

## Common Files

- `sakshi/**/*.py`
- `docs/api/*.md`
- `docs/architecture.md`
- `CHANGELOG.md`
- `tests/unit/*.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Modify implementation code in sakshi/ (e.g., sakshi/recovery/hinting.py)
- Update documentation in docs/api/ and docs/architecture.md if necessary
- Update CHANGELOG.md
- Update or add tests in tests/unit/

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.