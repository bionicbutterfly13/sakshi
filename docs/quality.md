# Quality Status

Status labels:

- `A` — implemented, import-clean, smoke-tested, package-boundary compliant.
- `B` — implemented but needs fuller tests or documentation.
- `C` — scaffolded or partially ported.
- `Pending` — not yet ported.

| Area | Status | Notes |
|---|---:|---|
| `models/` | A | DTOs ported with product-native names and no host imports. |
| `protocols.py` | A | Public seams defined for event bus, clock, goal state, basin hook, and write guard. |
| `errors.py` | A | Typed package error hierarchy defined. |
| `config.py` | C | Skeleton only; fields land as modules are ported. |
| `cycle/` | A | Blackboard and cycle history ported; smoke-tested. |
| `registries/` | A | Module and phase registries ported; smoke-tested. |
| `interpret/` | A | A-distance, ambiguity, anomaly persistence, and expectation evaluator ported; package-local tests cover key behavior. |
| `goals/` | A | Goal graph, selector, validator, transformer, generator, monitor, explainer, outcome closure, and outcome memory ported with package-native DTOs and injected seams. |
| `plans/` | A | Plan soundness and deviation tracker ported; learning-signal adjustment is host-wired through a public callback, not an EventBus singleton. |
| `meta/` | B | Package-native monitor/assess/control loop ported with injected graph, generator, EventBus, and WriteGuard seams. Host-only particle lifecycle and LinOSS/AIS dispatch remain adapter-side. |
| `intake/` | A | Instruction ingest ported with graph insertion, lineage metadata, validation, and deduplication; legacy goal-service sync remains adapter-side. |
| `world/` | A | World simulator ported; package-local tests cover action scaling and discrepancy detection. |
| Public docs | A | README, contribution notes, provenance, architecture, principles, quality docs, and quickstart exist. |
| Tests | A | Package-local tests cover DTOs, foundations, world/interpretation, goals, plans, meta, and intake without host imports. |

Update this file after each port cluster.
