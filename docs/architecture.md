# Architecture

Sakshi is a metacognitive runtime library. It exposes protocol seams and pure core logic; host applications provide concrete runtime services.

## Witness Pattern

The Witness pattern is Sakshi's main architectural boundary: Sakshi observes a
host agent's cognition without becoming the host's cognition. The host owns
planning, memory, tools, world modeling, motivation generation, and side
effects. Sakshi owns typed observation seams, expectation checks, audit records,
and small decision helpers that let the host decide what to do next.

This makes the runtime useful in production because it adds inspectability and
governance without forcing a host to adopt Sakshi as its agent framework. A
host can declare module expectations, tag anomalies, record goal operations,
calibrate confidence, report trust and uncertainty, gate motivation, and verify
achievement or self-modification claims through one deterministic package-local
surface. When a feature would require Sakshi to simulate the host's beliefs or
choose the host's domain strategy, it belongs in the host adapter instead.

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

## Module contracts

Every module that participates in a cycle can register an `ExpectationProfile` declaring five contract fields:

- `runtime_bound_seconds` — latency SLA.
- `output_schema` — JSON-schema-like dict, type name, or class path.
- `confidence_range` — inclusive `[low, high]` bounds on self-reported confidence.
- `side_effects_contract` — modules / blackboard keys / services this module is allowed to mutate.
- `failure_modes` — admissible failure shapes (each with severity).

This is the primary typed-monitoring surface. Sakshi watches the running module against its declaration; mismatches produce `ExpectationViolation` records routed through the standard event flow. Three convenience methods (`confidence_in_band`, `is_declared_failure`, `has_side_effect`) cover the most common checks.

## Stuck-loop detection

`CanalizationMetrics` is a frozen four-number struct that flags "agent stuck in a no-progress loop." The fields — `depth`, `dwell_time`, `perturbation_resistance`, `temperature_sensitivity` — combine into a coarse `CanalizationRisk` band (`HEALTHY` / `DEEPENING` / `PATHOLOGICAL`). The convenience factory `metrics_from_static_cycles()` derives the struct from the primitives existing detectors already emit. Hosts read the band to decide whether to widen search precision, swap a module, or escalate.

## Intervention validation

`InterventionExecutor` is the package's validation primitive for meta-cycle
control actions. `MetaController` routes generated `ControlAction` intent
through an executor before publishing to the host event bus. The host still owns
runtime side effects; Sakshi publishes only permitted control intent plus an
audit record of every permit or deny decision. The executor:

1. Checks a per-`(action_type, target)` cooldown to prevent thrashing.
2. Calls the host's `InterventionPermissionPolicy.is_permitted(action, history)`.
3. Records every decision in a bounded `InterventionRecord` audit history.
4. Accepts an `InterventionOutcome` callback so downstream effectiveness can be reported.

The default `AlwaysPermitPolicy` is test-friendly; production hosts inject their
own policy. Hosts that have not yet completed their policy can use
`DenyByDefaultPolicy` as a safe scaffold — it denies every intervention with an
explicit audit reason instead of silently permitting them. The same shape exists
on the write seam: `AlwaysPermitWriteGuard` is the permissive default,
`DenyByDefaultWriteGuard` is the deny-first alternative. `MetaCycleResult.actions`
contains only permitted/published actions, while
`MetaCycleResult.intervention_records` exposes the full decision trail. The
audit history is the seam human reviewers and post-hoc analysis tools read.

## Confidence calibration

`CalibrationTracker` is a sliding-window store for `(predicted_confidence, actually_correct)` pairs. One call to `report()` returns:

- `self_trust_score` — single scalar in `[0.0, 1.0]` summarizing whether the agent's confidence claims line up with reality.
- `calibration_warnings` — per-decile records identifying which confidence band is miscalibrated and by how much.

A host that sees a warning at the 0.9 decile can widen the `confidence_range` on the offending module's `ExpectationProfile` rather than blanket-suppress.

## Goal lineage

`GoalLineageAuditor` walks the `metadata["source_goal_id"]` chain produced by `GoalTransformer` and reports a typed `LineageReport` with depth, widening-step count, transform chain, and a `LineageVerdict` (`ALIGNED` / `WARN` / `DRIFTED`). The auditor never intervenes; it returns a typed signal a host can route to a pre-INTEND gate, an operator dashboard, or both.

## Outcome memory episode retrieval

`GoalOutcomeMemory` is a typed log of past goal closures. Three accessors support post-mortem retrieval:

- `recent(n)` — newest `n` records, newest first.
- `find_similar(predicate_name=..., outcome_status=..., limit=...)` — recent records sharing a predicate name and (optionally) outcome.
- `hit_rate(predicate_name=...)` — fraction of recorded records that achieved their goal.

The store is a record log, not a learning system. Hosts that want strategy-level adaptation read these and decide.

## Meta-cycle scheduling

`MetaSchedulingPolicy` decides whether to run the meta-cycle this iteration. Three defaults ship:

- `EveryCyclePolicy` — backward-compatible default; run on every cycle.
- `OnAnomalyPolicy` — run only when an anomaly fired since the previous run.
- `ThrottledByLoadPolicy(max_run_risk=..., always_run_on_anomaly=...)` — skip when `CanalizationMetrics` reports load above the threshold; an anomaly during high load can still force a run.

Hosts plug their own implementations through the protocol when finer-grained scheduling is needed.

## Deliberation gate

`DeliberationGate` is a pure threshold function that recommends `routine` vs `deliberative` reasoning given three small numbers: confidence, recent failure rate, remaining budget. Conservative default: stay routine unless confidence is below 0.6 *or* failure rate above 0.4 *and* budget remains above the floor. The gate is decision-only; it never executes either path.

## Goal-assignment rebellion

`RebelHook` is the pre-INTEND seam where the meta-layer evaluates an assigned goal against the agent's declared `CognitiveExpectation` set. The hook returns a typed `RebelDecision` with verdict `ACCEPT`, `REWRITE` (carrying a substitute goal), or `REJECT` (with a reason string). The default `AcceptingRebelHook` accepts every goal; production hosts inject a hook that consults their safety state.

## Anticipatory risk

`AnticipatoryRiskScorer` runs the three-step risk pipeline on a candidate plan:

1. The host's `RiskModel` enumerates per-step `PlanRisk` records.
2. `aggregate_risk_score` reduces them to a single scalar in `[0, 1]`, discounting by expected benefit.
3. `classify_band` maps the scalar to a `RiskBand` (`LOW`, `MEDIUM`, `HIGH`).

Returns a frozen `PlanRiskAssessment`. Slots into the EVAL phase before commit.

## Intervention pattern taxonomy

`InterventionType` labels what *pattern* of intervention is happening (`WIDEN_SEARCH`, `DROP_CONFIDENCE`, `FLUSH_MEMORY`, etc.) — orthogonal to `ControlActionType` which names the *mechanism* (`ADJUST_PRECISION`, `SWAP_MODULE`). One mechanism can serve many patterns; the pattern label keeps audit records intelligible. Pass `pattern=...` to `InterventionExecutor.validate`; the recorded `InterventionRecord` carries it through.

## Failure-axis classification

`classify_failure_mode` tags a `FailureMode` along the four-axis TRAP taxonomy (Transparency, Reasoning, Adaptation, Perception). Resolution order: explicit override argument, `trap:<axis>` marker in the description, deterministic keyword match against name + description. `TRAPRouter` then maps each axis to a recommended `ControlActionType` (Reasoning → `SWAP_MODULE`, Perception → `STRENGTHEN_MODULE`, Adaptation → `ADJUST_PRECISION`, Transparency → `SUPPRESS_MODULE`); host-supplied routing overrides defaults.

## Operational recovery hints

`StrategyHinter` maps concrete runtime failures such as timeouts, empty results,
parse errors, and bridge failures to bounded `RecoveryAction` hints. This layer
does not execute retries or tool calls. The host owns each `StrategyHinter`
instance, including attempt state and custom strategy registration, so package
code has no process-wide recovery singleton.

The default `RECOVERY_STRATEGIES` mapping is immutable. Hosts can copy those
defaults into an instance, register local strategies, inspect the next action
without consuming it, and reset attempt state for a completed task. This
operational taxonomy is separate from TRAP: TRAP classifies declared cognitive
failure modes, while recovery recommends a next step for a runtime failure
already observed by the host.

## Competing-hypothesis distribution

`AnomalyExplainer.explain_distribution(event, top_k=3)` returns up to ``top_k`` ranked `AnomalyExplanation` records instead of collapsing to a single best guess. Hosts read the distribution and decide whether the top-1 confidence exceeds the runner-up by enough margin to justify a high-impact intervention; otherwise they defer or gather more evidence.

## Two-axis trust + uncertainty typing

`TrustBifurcation` separates two questions a host operator usually conflates: how *competent* was the capability that produced this output (reliability under recent calibration) and how *intact* was the pipeline that delivered it (was the signal tampered with, censored, unverified). The two axes are reported independently; the `aggregate` property combines them via geometric mean so a weakness on either side penalizes the score.

`UncertaintyType` tags whether a confidence value reflects a `PROBABILITY` (single modeled hypothesis), `AMBIGUITY` (multiple equiprobable hypotheses), or `IGNORANCE` (no model). Hosts route differently in each case.

`UncertaintyBoundary` adds the response-oriented classification: stochastic uncertainty, ambiguity across hypotheses, ignorance/no model, epistemic uncertainty where more evidence may help, or ontological/fundamental uncertainty where the model frame itself may be wrong.

`TrustRepairRecommendation` records typed repair suggestions (`GATHER_EVIDENCE`, `WIDEN_HYPOTHESES`, `RECALIBRATE_MODULE`, `VERIFY_INTEGRITY`, `ESCALATE_TO_OPERATOR`, `REFRAME_MODEL`) with reason, target, severity, optional uncertainty boundary, and evidence keys. Sakshi records the suggestion; hosts decide whether and how to act.

`TrustReport` is the composite host-facing DTO that bundles a `TrustBifurcation`, an `UncertaintyType`, an `UncertaintyBoundary`, the labels of competing hypotheses (when applicable), calibration status, trajectory band, free-form recommendation text, and typed repair recommendations. The surface humans see.

## Cost-matrix error shaping

`ConfusionWeighter` is a typed cost-matrix decision helper. Given a probability vector and a `{predicted: {true: cost}}` matrix, it picks the class minimizing expected cost rather than the naive arg-max. Returns a `ConfusionDecision` recording both the chosen class and the naive baseline so audit trails show what the asymmetric cost structure actually changed. `ConfusionWeighter.from_uniform` builds a starter matrix from a class list plus FP/FN cost scalars.

## Motivation surface

Sakshi does not generate intrinsic motivations on its own — the host does. What Sakshi provides is the typed surface hosts use to:

- Tag every goal with the source `MotivationType` (achievement / affiliation / power / novelty / competence / surprise / extrinsic / unclassified).
- Bound the host's motivation creativity through a `CreativityEnvelope` (allowed predicates, forbidden attributes, max novelty score, forbidden motivation types). `evaluate_envelope(...)` returns a typed `EnvelopeVerdict`.
- Filter motivated goals against a `GoalRelevanceFilter` over a host-defined value-tag taxonomy.
- Stream every motivation activation through `MotivationAuditor` — a bounded ring-buffer that produces `ComputationalMotivationMetrics` (diversity, stability, risk, communication cost) on demand.

The Witness stance: Sakshi observes the host's motivation record, validates against host-declared envelopes, and reports — never generates.

## Defensive guards

Two typed protocols guard against classic failure modes; both ship with sensible default implementations and accept host-supplied replacements when richer logic is needed.

`RewardIntegrityGuard` validates a goal-achievement claim against a host-supplied set of exogenous evidence keys. The default `EvidenceRequiringRewardIntegrityGuard` counts *distinct* evidence keys and requires at least ``min_evidence`` of them before permitting the claim, so duplicate keys cannot inflate the count. Hosts can also pass ``required_evidence_keys`` to demand specific named keys (e.g., ``"tool:completed"`` and ``"state:changed"``) before any claim is permitted. Defends against the pattern where an agent silently records "goal achieved" without the world having moved.

`ModificationIntegrityGuard` validates a proposed `GoalConstraint` rewrite. The default `IntegrityCriticalModificationGuard` refuses to demote a constraint flagged ``integrity_critical=True`` to non-critical and refuses to drop any of its safety constraints. This closes the Phase A → Phase F handshake on the ``integrity_critical`` flag.

Both guards return a typed `GuardVerdict`; `make_audit_record` wraps any verdict into a frozen `GuardAuditRecord` hosts stream through their event bus.

`KnowledgeRewardBalance` is a host-declared preference enum (`KNOWLEDGE` / `REWARD` / `HYBRID`) with two predicate helpers (`biases_toward_exploration`, `biases_against_exploration`) hosts use when deciding whether to suppress a curiosity-motivated goal under budget pressure.

## Failure Model

Sakshi raises typed package exceptions from `sakshi.errors`.

- `GoalValidationError` — goal invalid against schema or current world state.
- `PlanSoundnessError` — plan cannot safely execute.
- `AnomalyEscalationError` — anomaly persistence requires escalation.
- `PhaseTransitionError` — invalid cycle lifecycle operation.
- `WorldStateUnavailableError` — host state store cannot return required state.

Host adapters may translate lower-level exceptions into these errors. Package core should not leak persistence, web-framework, or host-service exception types through public APIs.

## Failure visibility

Two seams default to fail-open behavior (keep the cycle moving when callback or
persistence layers misbehave) but ship a strict opt-in for hosts that want
loud failures during integration:

- `PhaseRegistry(fail_fast_callbacks=True)` — re-raises any cycle-complete
  callback failure as `PhaseTransitionError` instead of swallowing it. Use
  this when a callback owns persistence the rest of the system relies on.
- `GoalMonitor(fail_closed_on_store_error=True)` — surfaces store-write
  failures as `store_error` on the returned `GoalMonitorResult` and treats
  the goal as not-yet-monitored, rather than silently reporting success.

Both options are opt-in so the quickstart defaults stay friendly to tests
and inert hosts.

## Observability

Core modules use named Python loggers and high-signal structured message text. Event emission goes through `EventBus`; direct printing is not allowed in package code.

## Construction

Sakshi package code does not ship singleton getters. Hosts construct runtime objects and pass configured protocol implementations. This keeps lifecycle, caching, and dependency ownership outside the library.

## Reference integrations

Two examples live under `examples/`:

- `toy_blocks_agent/` — the smallest concrete answer to "how do I wire Sakshi
  into an existing agent?" A 3-phase plan/act/observe loop on a stdlib-only
  blocks world. Exercises `PhaseRegistry`, `EventBus`, `GoalStateStore`, and
  `WriteGuard` end-to-end.
- `llm_research_agent/` — the bigger sibling: the host's cognition is an
  actual language model (Anthropic Claude in live mode, a deterministic mock
  in test mode). Adds dynamic `GoalGraph` decomposition, typed anomaly
  observation on low-confidence answers, and a `WriteGuard`-gated publish
  step. Demonstrates how Sakshi's seams hold when cognition is non-toy.
