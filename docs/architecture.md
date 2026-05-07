# Architecture

Sakshi is a metacognitive runtime library. It exposes protocol seams and pure core logic; host applications provide concrete runtime services.

## Layers

Package dependencies should flow in this direction:

```text
models
  -> protocols / errors / config
  -> cycle / registries / interpret / goals / plans / meta / intake / world
```

Rules:

- `models/` contains DTOs only.
- `protocols.py` defines host seams only.
- Runtime modules accept protocol implementations by constructor argument.
- No runtime module may import a concrete host service.
- Host adapters live outside the package.

## Public Seams

Hosts supply:

- `EventBus` for lifecycle and goal events.
- `Clock` for deterministic time.
- `GoalStateStore` for world-state reads and goal-outcome writes.
- `BasinHook` for optional attractor-basin lifecycle integration.
- `WriteGuard` for host safety policy.

Package defaults may be no-op or test-friendly, but production integrations belong in the host adapter.

## Cycle Shape

The object-level cycle is:

```text
PERCEIVE -> INTERPRET -> EVAL -> INTEND -> PLAN -> ACT
```

The metacognitive loop mirrors the object-level cycle:

```text
MONITOR -> INTERPRET -> EVALUATE -> INTEND -> PLAN -> CONTROL
```

These are generic metacognitive phases, not a compatibility claim for any external reference implementation.

## Anomaly lanes

Every detected anomaly carries an `AnomalySourceType` tag at detection:

- `WORLD` — mismatch between expected and observed environment state. Triggers world-model corrections.
- `COGNITIVE` — mismatch inside the agent's own reasoning trace (impasse, expectation violation on a phase output, plan deviation). Triggers meta-cycle adjustments.
- `COMPOUND` — straddles both lanes. Decomposed at detection, not at explanation.

Calibration metrics and explanation pipelines are reported per lane. Cross-lane aggregates conflate object-level and meta-level signals and mislead host operators.

## Goal lifecycle

`Goal` carries two orthogonal axes:

- `GoalStatus` — terminal state (active, achieved, abandoned, blocked, delegated).
- `GoalMode` — current lifecycle phase (formulating, selected, dispatched, monitoring, repairing, deferred, completed) plus an event history (`Goal.transitions`).

Hosts subscribe to `goal.op` events on the `EventBus` to receive `GoalOperationEvent` records describing the canonical lifecycle verbs (formulate, select, expand, commit, dispatch, monitor, evaluate, repair, defer, delegate, resume).

## Discrepancy resolution

`DiscrepancyResolution` records the four-step chain `symptom → explanation → goal → plan` end-to-end at either the object or meta level. The same shape applies on both levels by design: a fact-vs-expectation mismatch in the world produces a goal that fixes the world; a phase-output-vs-expectation mismatch in cognition produces a goal that fixes the cognition.

## Trace pruning

The meta-cycle does not reason over the full unbounded `CycleTrace`. Hosts pass a `TracePruner` (see `sakshi.cycle`) that reduces the trace to a relevant slice. Three defaults ship with the package:

- `LastNPruner` — keep the final N phase results.
- `SinceAnomalyPruner` — keep every phase from the most recent anomaly forward.
- `WhereExpectationFiredPruner` — keep only phases whose output flagged at least one expectation.

Hosts can write their own implementations against the protocol; the package never selects a pruner on the caller's behalf.

## Plan decomposition and constraints

`TaskDecomposer` (in `sakshi.plans`) is the seam for HTN-style or any other structured planning. The package itself never imports a planner.

`GoalConstraint` (in `sakshi.plans`) reifies the bounds on a goal's feasibility — initial state, safety constraints, goal conditions — plus an `integrity_critical` flag that downstream modification guards read to refuse dropping the constraint.

## Tiered transparency

`TransparencyLevel` selects which DTO a host surfaces to humans:

- `StatusTransparency` — current state and active goals.
- `ReasoningTransparency` — the most recent decision's reasoning chain.
- `ProjectionTransparency` — forecasts and risk estimates.

Consumers usually want exactly one tier; the DTOs are not unioned.

## Failure Model

Sakshi raises typed package exceptions from `sakshi.errors`.

- `GoalValidationError` — goal invalid against schema or current world state.
- `PlanSoundnessError` — plan cannot safely execute.
- `AnomalyEscalationError` — anomaly persistence requires escalation.
- `PhaseTransitionError` — invalid cycle lifecycle operation.
- `WorldStateUnavailableError` — host state store cannot return required state.

Host adapters may translate lower-level exceptions into these errors. Package core should not leak persistence, web-framework, or host-service exception types through public APIs.

## Observability

Core modules use named Python loggers and high-signal structured message text. Event emission goes through `EventBus`; direct printing is not allowed in package code.

## Construction

Sakshi package code does not ship singleton getters. Hosts construct runtime objects and pass configured protocol implementations. This keeps lifecycle, caching, and dependency ownership outside the library.

