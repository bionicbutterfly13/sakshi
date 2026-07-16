<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles: template placeholders -> six Sakshi governing principles
- Added sections: Additional Constraints; Development Workflow
- Removed sections: none
- Templates requiring updates:
  - updated: .specify/templates/plan-template.md
  - updated: .specify/templates/spec-template.md
  - updated: .specify/templates/tasks-template.md
  - updated: .agents/skills/speckit-specify/SKILL.md
  - updated: .agents/skills/speckit-tasks/SKILL.md
- Follow-up TODOs: none
-->
# Sakshi Constitution

## Core Principles

### I. Package Core Independence

The `sakshi/` package MUST remain independent of any host runtime. Package code
MUST NOT import `api.*`, FastAPI, Graphiti, Neo4j, smolagents, host service
getters, or another host-specific framework. Runtime capabilities MUST enter
through protocols, typed data objects, or explicit constructor arguments, and
host-specific glue MUST remain outside this package. This boundary keeps Sakshi
reusable, testable, and safe to embed in unrelated agent systems.

### II. Product-Native Identity and Formal Attribution

Public package names, import paths, classes, functions, and primary documentation
headings MUST use Sakshi-native language. External reference architectures and
private-project terminology MAY appear only in provenance material, citations,
or narrowly explanatory comments. Formal author, maintainer, citation,
copyright, and notice metadata MUST be preserved and MUST NOT be treated as
contamination. This rule protects a coherent public API without erasing credit.

### III. Explicit Host Ownership

Hosts MUST own construction, dependency wiring, caching, persistence, process
lifecycle, cognition, planning, tools, and side effects. Package code MUST NOT
add module-global singleton getters or silently obtain runtime services. When a
new capability needs a host service, the change MUST define or reuse a protocol
and require the host adapter to implement it. Defaults intended for tests or
quickstarts MUST be identified clearly; production scaffolds SHOULD fail closed.

### IV. Typed and Deterministic Contracts

Public boundaries MUST use typed DTOs or protocols. Pydantic v2 models SHOULD be
used for public data shapes unless a simpler package-internal dataclass is
clearly sufficient. Core behavior SHOULD be deterministic when supplied with
deterministic clocks, stores, and inputs. Errors MUST follow existing typed or
explicit failure patterns and MUST NOT be swallowed. Ad hoc dictionaries MAY be
used only at explicitly opaque extension seams.

### V. Verification Integrity

Behavioral and public-API changes MUST include focused regression coverage.
Where practical, a behavior change SHOULD demonstrate a failing test before the
implementation is changed. Existing assertions, scope, and coverage MUST NOT be
weakened to manufacture a pass. The full repository gate is `make ci`; `make
all` is its supported alias and MUST pass before handoff when development
dependencies are installed. Pre-existing failures MUST be reported separately
from failures introduced by the current change.

### VI. Narrow, Compatible Change

Each change MUST address one coherent concern and reuse existing abstractions,
dependencies, naming, structure, and error handling. Public behavior changes
MUST identify compatibility impact, update tests, and update public docs in the
same change. New package areas SHOULD update `docs/quality.md`. Dependencies MAY
be added only when the capability cannot be implemented correctly with the
existing stack. Adjacent issues MUST be recorded separately unless they block
the requested outcome.

## Additional Constraints

- Supported Python is 3.11 or newer. Core dependencies remain intentionally
  small: Pydantic and typing extensions.
- Secrets, credentials, tokens, and private host data MUST NOT be committed,
  logged, copied into specifications, or exposed in generated artifacts.
- Input handling MUST be checked for injection, path traversal, invalid state,
  authorization bypass, and unsafe writes when those risks are in scope.
- Graphify output is a project map, not ambient source context. Agents MUST NOT
  read or re-index `graphify-out/` during normal work.
- Completed files under ignored `.archive/` are historical records only. They
  MUST NOT be treated as active plans or migrated into new Spec Kit features.
- `AGENTS.md` remains the protected agent-instruction entry point. Spec Kit
  automation MUST NOT modify it unless Dr. Mani explicitly opens an
  agent-instruction update task.

## Development Workflow

- New staged features, bugs, releases, and other multi-step work MUST use a
  forward-only Spec Kit feature directory under `specs/`. Completed legacy
  tracks remain untouched as local history.
- The normal sequence is constitution check, specification, clarification when
  needed, plan, tasks, consistency analysis when useful, implementation, and
  verification. A plan MUST NOT proceed while its constitution check fails.
- Specifications MUST state measurable acceptance criteria, compatibility and
  boundary impact, assumptions, and explicit out-of-scope items. Plans MUST name
  real repository paths and the narrowest relevant verification commands.
- Contributions MUST follow `CONTRIBUTING.md`, including the `feature/<name>`
  branch convention for contributed feature work. Commits occur only when Dr.
  Mani explicitly requests them.
- For behavior changes, tasks MUST preserve RED/GREEN/REFACTOR discipline where
  practical. Documentation-only changes require readback and diff inspection;
  code changes require focused checks plus the full gate when practical.
- If the expected official workflow fails, work MUST stop with the exact
  blocker and changed state. Alternate scaffolds or bypasses require explicit
  approval.

## Governance

This constitution governs Spec Kit specifications, plans, tasks, and reviews in
Sakshi. `AGENTS.md` remains the higher-priority operational instruction file for
coding agents, and `CONTRIBUTING.md` remains the contribution protocol. A
constitution amendment requires an explicit scoped request, a documented sync
impact report, and propagation to affected templates or guidance. Versions use
semantic versioning: MAJOR for incompatible governance changes, MINOR for new or
materially expanded principles, and PATCH for clarifications. Every plan and
review MUST verify the applicable constitution gates; unexplained violations
block implementation.

**Version**: 1.0.0 | **Ratified**: 2026-07-16 | **Last Amended**: 2026-07-16
