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

The metacognitive loop is:

```text
MONITOR -> ASSESS -> CONTROL
```

These are generic metacognitive phases, not a compatibility claim for any external reference implementation.

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

