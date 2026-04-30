# Contributing

Sakshi is in early experimental development. The public API is subject to breaking change without notice in 0.x releases.

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

## Branch convention

Feature branches: `feature/<short-description>`. Pull requests target `main`.

## Public API discipline

Sakshi exposes protocols, DTOs, and pure-core logic. The public package never imports from a specific runtime, persistence layer, web framework, or LLM SDK. Host applications wire concrete implementations behind the documented protocols.

If a proposed change would add a runtime dependency to the package core, open a discussion before submitting code.
