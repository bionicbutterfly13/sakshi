# Principles

This document uses RFC 2119-style language: MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are intentional.

## Identity

- The public package name MUST be `sakshi`.
- Public identifiers MUST use Sakshi-native names.
- Related-work references MUST live in provenance sections or inline citations, not package paths, class names, function names, or primary docs headings.
- The project MUST NOT claim drop-in compatibility with any external reference implementation unless compatibility tests exist.

## Boundary Discipline

- Package core MUST NOT import host runtime modules.
- Package core MUST NOT import FastAPI, Graphiti, Neo4j, smolagents, or host service getters.
- Runtime dependencies MUST enter through protocols, DTOs, or explicit constructor arguments.
- Host-specific glue MUST live in a host adapter outside this package.

## Lifecycle

- Package code MUST NOT define module-global singleton getters.
- Hosts own construction, caching, dependency wiring, and process lifecycle.
- Core classes SHOULD be deterministic when supplied with deterministic clocks and stores.

## Data Shapes

- Boundary data MUST be represented as typed DTOs or protocols.
- Ad hoc dictionaries MAY be used only at explicitly opaque host-extension seams.
- New DTOs SHOULD be Pydantic v2 models unless a dataclass is clearly simpler and remains package-internal.

## Testing

- Package tests MUST run without the Dionysus repository on `PYTHONPATH`.
- Host adapter tests belong in the host repository.
- Any skipped external integration test MUST report as skipped, not silently passed.

## Documentation

- Behavior-changing changes SHOULD update docs in the same commit.
- New package areas SHOULD update `docs/quality.md`.
- Public docs SHOULD describe what Sakshi does before describing influences.

