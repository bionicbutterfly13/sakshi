# Changelog

All notable changes to this project will be documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/) once 1.0 ships; until then 0.x
releases may break public API in any minor version.

## [Unreleased]

## [0.6.0a0] - 2026-05-07

### Added
- `meta.MetaSchedulingPolicy` protocol — host-pluggable rule for
  whether to run the meta-cycle on the current iteration. Three
  defaults ship: `EveryCyclePolicy`, `OnAnomalyPolicy`,
  `ThrottledByLoadPolicy(max_run_risk=..., always_run_on_anomaly=...)`.
  The throttled policy reads `CanalizationMetrics` directly and skips
  expensive meta-runs when load is pathological, with a configurable
  anomaly override.
- `meta.DeliberationGate` — pure threshold function that decides
  between routine and deliberative reasoning paths given current
  confidence, recent failure rate, and remaining budget. Returns a
  typed `DeliberationDecision`. Conservative default: routine path
  unless confidence is below 0.6 *or* failure rate above 0.4 *and*
  budget is above the floor.
- `goals.RebelHook` protocol — pre-INTEND gate where the meta-layer
  evaluates an assigned goal against expectations and returns
  `RebelDecision.accept`, `RebelDecision.rewrite`, or
  `RebelDecision.reject`. Default `AcceptingRebelHook` is fully
  backward-compatible; production hosts inject their own.
- `plans.AnticipatoryRiskScorer` — three-step risk pipeline (identify
  via `RiskModel`, aggregate, classify into `RiskBand`). Returns a
  frozen `PlanRiskAssessment`. Pure functions: `aggregate_risk_score`
  and `classify_band` are exposed for hosts that want only one step.
- `meta.InterventionType` enum — pattern-level taxonomy of eight
  named interventions (`PAUSE_AND_REEVALUATE`, `DROP_CONFIDENCE`,
  `WIDEN_SEARCH`, `RELAX_GOAL`, `FLUSH_MEMORY`, `TRIGGER_EXPLORATION`,
  `SUSPEND_RECOVERY`, `ESCALATE_TO_OPERATOR`). `InterventionRecord`
  now carries an optional `pattern` field; `InterventionExecutor.validate`
  accepts a `pattern=` keyword.
- `interpret.TRAPDimension` enum (Transparency, Reasoning, Adaptation,
  Perception, Unclassified) plus `classify_failure_mode` and
  `TRAPRouter`. Tags `FailureMode` records along the four-axis
  taxonomy and recommends a default `ControlActionType` per axis,
  overridable per host.
- `goals.AnomalyExplainer.explain_distribution` — returns up to
  ``top_k`` ranked competing hypotheses instead of collapsing to one.
  Lets the meta-cycle hedge across competing diagnoses when the
  top-1 confidence does not exceed the runner-up by a comfortable
  margin.

### Notes
- `OptimalityMeasure` (originally proposed in the roadmap) was
  audited against the existing `GoalSelector` + `ModSelectionCriteria`
  seam in `goals/selector.py` and judged redundant. The existing
  `criteria` constructor argument already supports pluggable scoring;
  hosts that want Bayesian / Thompson / etc. policies subclass
  `ModSelectionCriteria` directly.
- `EmergenceBound` (originally proposed) deferred. The Type I-IV
  classification is multi-agent-flavored and Sakshi is single-agent
  by default; hosts that build multi-agent adapters can introduce the
  classifier in their adapter layer.

## [0.5.0a0] - 2026-05-07

### Added
- `meta.CanalizationMetrics` — frozen dataclass with four fields
  (`depth`, `dwell_time`, `perturbation_resistance`,
  `temperature_sensitivity`) plus a three-band `CanalizationRisk`
  classifier (`HEALTHY` / `DEEPENING` / `PATHOLOGICAL`). Convenience
  factory `metrics_from_static_cycles()` derives metrics from the
  primitives existing detectors already emit.
- `models.ExpectationProfile` — five-property contract every module
  registers (`runtime_bound_seconds`, `output_schema`,
  `confidence_range`, `side_effects_contract`, `failure_modes`). The
  primary typed-monitoring surface: each module declares what it
  should do; Sakshi watches and reports violations against the
  declaration. `models.FailureMode` carries the per-mode severity.
- `meta.InterventionExecutor` — validates every meta-cycle control
  action (`SUPPRESS_MODULE`, `ADJUST_PRECISION`, `SWAP_MODULE`,
  `STRENGTHEN_MODULE`, `REPLACE_MODULE`) against a typed
  `InterventionPermissionPolicy` plus a configurable cooldown.
  Records every decision in a bounded audit history and accepts an
  `InterventionOutcome` callback so downstream effectiveness can be
  recorded. Default `AlwaysPermitPolicy` is test-friendly; production
  hosts plug their own policy.
- `interpret.CalibrationTracker` — sliding-window tracker for
  `(predicted_confidence, actually_correct)` pairs. Reports a
  `self_trust_score` scalar and a list of `CalibrationWarning`
  records identifying which confidence band is miscalibrated.
  Consolidates what the original roadmap split across two phases
  ("inverse trust" + "calibration auditor") into one tracker with
  one DTO surface.
- `interpret.GoalLineageAuditor` — walks the
  `metadata["source_goal_id"]` chain produced by `GoalTransformer`
  and reports a typed `LineageReport` with depth, widening-step
  count, transform chain, and a `LineageVerdict`
  (`ALIGNED` / `WARN` / `DRIFTED`). Pre-INTEND drift signal; never
  intervenes on its own.
- `goals.GoalOutcomeMemory.recent()`, `find_similar()`,
  `hit_rate()`, and `__len__` — episode retrieval extensions on the
  existing outcome store. No new module; the store remains a typed
  log of past closures, not a learning system.

### Changed
- Rewrote `meta/canalization.py` docstrings in plain-user
  vocabulary ("agent stuck in a no-progress loop") instead of
  research-architecture jargon. The math is unchanged.

## [0.4.0a0] - 2026-05-07

### Added
- `AnomalySourceType` enum (`WORLD | COGNITIVE | COMPOUND`) and a `source`
  field on `AnomalyEvent` and `AnomalyEscalation`. Anomalies are now tagged
  at detection so calibration and explanation can be reported per lane.
- `GoalMode` lifecycle enum (formulating / selected / dispatched /
  monitoring / repairing / deferred / completed) and `GoalEvent`
  history on every `Goal`, with `Goal.record_transition()` helper.
  `GoalMode` is orthogonal to the existing `GoalStatus`.
- `GoalOperation` taxonomy enum and `GoalOperationEvent` DTO covering the
  canonical lifecycle verbs (formulate, select, expand, commit, dispatch,
  monitor, evaluate, repair, defer, delegate, resume).
- `DiscrepancyResolution` DTO and `ResolutionLevel` enum capturing the
  symptom → explanation → goal → plan chain end-to-end at object or
  meta level.
- `TransparencyLevel` enum and three tier DTOs (`StatusTransparency`,
  `ReasoningTransparency`, `ProjectionTransparency`) for tiered host
  disclosure of agent state and reasoning.
- `GoalConstraint` frozen DTO in `sakshi.plans` carrying
  `(initial_state, safety_constraints, goal_conditions,
  integrity_critical)`. The `integrity_critical` flag is the contract
  surface a future modification guard reads to refuse dropping a
  constraint.
- `TracePruner` protocol in `sakshi.cycle` plus three default
  implementations: `LastNPruner`, `SinceAnomalyPruner`, and
  `WhereExpectationFiredPruner`. Bounds the meta-cycle's input on
  long-running agents.
- `TaskDecomposer` protocol and `Action` DTO in `sakshi.plans`. Lets
  hosts plug HTN-style or other structured planners behind a stable
  package seam.
- `ControlActionType.REPLACE_MODULE` for the case where a meta-cycle
  decision is to install a fundamentally different module rather than
  swap to a known alternative.

### Removed
- Two extraneous control-action enum entries imported from an external
  draft plan, together with their emitter module under `meta/`. They
  were never part of Sakshi's process. The underlying
  static-policy-entrenchment signal will return as
  `CanalizationMetrics` in a later release with proper typing. The
  `Goal-Driven Autonomy` prose section that depended on those entries
  was also removed from `docs/architecture.md`.

## [0.3.0] - 2026-05-06

### Added
- `GoalGraph.iter_goals()` — public iterator over every goal in the
  graph regardless of status. Stable insertion order.
- `GoalGraph.get_goals_by_status(statuses)` — public filter for goals
  matching any of the supplied :class:`GoalStatus` values. Empty
  filter returns an empty list.
- `CognitiveBlackboard.snapshot` — deepcopy failures now log a warning
  with the offending key + value type instead of silently aliasing
  live state. Snapshots remain best-effort but no longer fail invisibly.
- `AnomalyExplainer.explain` — broad-except handler promoted from
  `debug` to `warning`; the degraded `AnomalyExplanation` now surfaces
  the underlying error class in its `hypothesis` text so callers can
  see when an explanation is a fallback.

### Changed
- README Status section: explicit warning that the `NoOpEventBus`,
  `NoOpBasinHook`, and `AlwaysPermitWriteGuard` defaults are inert by
  design; production hosts must inject real implementations.

## [0.2.0] - 2026-05-05

### Added
- CI `package` job: runs `python -m build` + `twine check` on every PR so
  the release path cannot drift from CI.
- `release.yml` GitHub Actions workflow: tag pushes (`v*`) build and
  publish to PyPI via Trusted Publishing (OIDC, no API token);
  `workflow_dispatch` with `target=testpypi` supports dry-run publishes to
  TestPyPI.

### Changed
- Distribution name confirmed as `pysakshi` on PyPI; `sakshi` import name
  unchanged. This release establishes the first stable PyPI pin, enabling
  host projects to drop git-commit references in favour of a versioned
  requirement (`pysakshi>=0.2.0`).

## [0.1.0] - 2026-05-04

### Added
- First public alpha release.
- Top-level re-exports from `sakshi`: `PhaseRegistry`, protocols
  (`EventBus`, `Clock`, `GoalStateStore`, `BasinHook`, `WriteGuard`),
  default no-op implementations (`NoOpEventBus`, `NoOpBasinHook`,
  `AlwaysPermitWriteGuard`), and the `SakshiError` hierarchy.
- Initial repository skeleton.
- Public protocols: `EventBus`, `Clock`, `GoalStateStore`, `BasinHook`, `WriteGuard`.
- Error hierarchy: `SakshiError` and named subclasses.
- `SakshiConfig` skeleton.
- Pydantic DTOs for goals, cycle traces, blackboard snapshots, expectations, anomalies, execution summaries, and world state.
- Core runtime packages for cycle state, registries, world simulation, interpretation, goals, plans, metacognition, and instruction intake.
- Agent-first repository contract: `AGENTS.md`, architecture/principles/quality docs, `Makefile`, and hygiene checks.
