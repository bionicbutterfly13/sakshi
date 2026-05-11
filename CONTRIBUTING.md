# Contributing

Sakshi is in pre-1.0 development. The public API is usable for host-adapter work, but 0.x minor releases may still include breaking changes.

## Running tests

```bash
pip install -e .[dev]
pytest
```

## Code style

Ruff is the formatter and linter. CI enforces a clean run:

```bash
ruff check sakshi tests
ruff format --check sakshi tests
```

## Quality gate

`make ci` is the single source of truth — it runs compile, format check,
lint, mypy type-check, hygiene, and a covered test run. The coverage floor
is set with `COVERAGE_MIN` (default `88`). Push only after `make ci` is
green locally.

```bash
make ci                    # run the full gate
make coverage              # just the covered test run
make COVERAGE_MIN=90 ci    # raise the floor for a stricter local run
```

## Branch convention

Feature branches: `feature/<short-description>`. Pull requests target `main`.

## Public API discipline

Sakshi exposes protocols, DTOs, and pure-core logic. The public package never imports from a specific runtime, persistence layer, web framework, or LLM SDK. Host applications wire concrete implementations behind the documented protocols.

If a proposed change would add a runtime dependency to the package core, open a discussion before submitting code.
