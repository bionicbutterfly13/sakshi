# Changelog

All notable changes to this project will be documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/) once 1.0 ships; until then 0.x
releases may break public API in any minor version.

## [Unreleased]

## [0.11.0] - 2026-05-11

### Removed
- `interpret.ExplanationEngine` and `interpret.ExplanationHypothesis`.
  These were a 0.4-era scaffold for an XPLAIN-style anomaly→goal pathway
  that was superseded by `goals.GoalGenerator` (paired with
  `interpret.AnomalyExplanation`) and never wired into the cycle. They
  carried mypy errors against the current `Goal` contract and were
  exported but uncalled. Hosts that need the same flow should use
  `GoalGenerator.generate_from_canalization_event` and the live
  anomaly-explanation pipeline.

### Fixed
- `meta.EvidenceRequiringRewardIntegrityGuard` constructor now accepts
  `required_evidence_keys` correctly, restoring import/compile health and
  letting hosts require named exogenous evidence keys before an achievement
  claim is permitted.
- `cycle.CognitiveBlackboard.clear()` is now atomic against concurrent
  writers. Previously it acquired and immediately released each per-key
  lock before clearing, leaving a window where a queued `set()` could
  interleave with the dict reset; it now holds every per-key lock for
  the duration of the clear.
- Type drift in `goals.GoalGraph.add_goal` (parent_id narrowing) and the
  removed `interpret.ExplanationEngine` (Goal predicate / priority
  contract) — `mypy sakshi/` is clean again.

### Changed
- `make ci` now runs `mypy sakshi` so type drift fails the gate.

## [0.10.0] - 2026-05-07

### Added
- `models.UncertaintyBoundary` — typed boundary classifier that
  distinguishes stochastic, ambiguous, ignorant, epistemic, and
  ontological uncertainty so hosts can route "get more evidence" vs
  "reframe the model" situations differently.
- `models.TrustRepairAction` and `models.TrustRepairRecommendation` —
  typed trust-repair recommendations that can be attached to
  `TrustReport` without executing repair inside Sakshi.
- README and architecture documentation now define the Witness pattern
  directly: Sakshi observes host cognition through typed seams while the
  host retains ownership of planning, memory, tools, world modeling,
  motivation generation, and side effects.

## [0.9.0] - 2026-05-07

### Added
- Phase G documentation sweep: anomaly-lane integrity principle,
  two-axis self-trust principle, goal-creativity envelope principle,
  goal interrogability principle, and defensive-guard discipline
  principle added to [docs/principles.md](docs/principles.md).
- [INSPIRATION.md](INSPIRATION.md): CLARION (Sun) and Goal Lifecycle
  Networks (Roberts, NRL) added; new section attributing Phase D / E
  / F shape and naming to specific chapters in *Foundations of
  Trusted Autonomy* (Abbass / Scholz / Reid eds., 2018, Springer
  Open).

### Changed
- Version cut from 0.9.0a0 to 0.9.0 once Phases A through G shipped
  with release metadata synchronized and the full local quality gate
  green.

## [0.9.0a0] - 2026-05-07

### Added
- `meta.RewardIntegrityGuard` protocol +
  `EvidenceRequiringRewardIntegrityGuard` default — validates a
  goal-achievement claim against a host-supplied set of exogenous
  evidence keys. Refuses to record achievement when fewer than
  ``min_evidence`` keys are present. Defends against the pattern
  where an agent silently records "goal achieved" without the world
  having moved.
- `meta.ModificationIntegrityGuard` protocol +
  `IntegrityCriticalModificationGuard` default — refuses to drop or
  relax a `GoalConstraint` flagged ``integrity_critical=True``.
  Specifically denies (a) demoting a critical constraint to
  non-critical and (b) dropping any safety constraint from a
  critical constraint's ``safety_constraints`` list. Closes the
  Phase A → Phase F handshake on the ``integrity_critical`` flag.
- `meta.GuardVerdict` and `meta.GuardDecision` — typed result shape
  shared by both guards. ``GuardVerdict.permitted`` is the boolean
  shortcut.
- `meta.GuardAuditRecord` + `meta.make_audit_record` — frozen audit
  record any guard verdict can be wrapped in for streaming through
  a host event bus.
- `meta.KnowledgeRewardBalance` enum (`KNOWLEDGE` / `REWARD` /
  `HYBRID`) plus `biases_toward_exploration` and
  `biases_against_exploration` predicates. Hosts use them when
  deciding whether to suppress a curiosity-motivated goal because
  the agent's budget is exhausted.

### Notes
- ``EpistemicState`` (multi-agent theory-of-mind seam, originally
  proposed in Phase F) deferred. Sakshi is single-agent by
  default; multi-agent belief tracking belongs in a host adapter.

## [0.8.0a0] - 2026-05-07

### Added
- `models.MotivationType` enum — coarse taxonomy of motivation
  sources (`ACHIEVEMENT`, `AFFILIATION`, `POWER`, `NOVELTY`,
  `COMPETENCE`, `SURPRISE`, `EXTRINSIC`, `UNCLASSIFIED`). Hosts tag
  every intrinsic goal with the type that produced it; Sakshi never
  generates motivation, only observes the host's record.
- `models.MotivationEvent` — immutable event DTO every motivation
  activation produces, including rejections.
- `models.CreativityEnvelope` + `evaluate_envelope` — host-declared
  bounds (allowed predicates, forbidden attributes, max novelty
  score, forbidden motivation types) plus a pure function that
  returns an `EnvelopeVerdict`. Goals outside the envelope are
  rejected with reason; the rejection still flows through the
  auditor.
- `models.GoalRelevanceFilter` — host-declared value-tag taxonomy
  with optional `require_value_tag` strict mode.
- `models.ComputationalMotivationMetrics` — frozen four-scalar
  summary (`diversity_score`, `stability_score`, `risk_assessment`,
  `communication_cost`) bounded to `[0, 1]`.
- `goals.MotivationAuditor` — bounded ring-buffer audit log over
  `MotivationEvent` records with `record`, `filter_by_type`,
  `acceptance_rate`, and `metrics()` accessors. The auditor never
  decides; it stores typed records and exposes a metrics view.

### Notes
- The full CLARION-style two-level motivation subsystem
  (TwoLevelMotivationSubsystem with implicit-drive Q-values) and
  the entropy-based CuriosityDrive scorer (originally proposed) are
  deferred. They model the host's mind, which is outside Sakshi's
  Witness-pattern scope. Hosts that want them implement them
  internally and emit `MotivationEvent` records into the auditor.
- `NarrativeMotivationJustifier` (templated explanations) and
  `MotivationDriftDetector` deferred; the metrics view already
  surfaces drift via `diversity_score` and `stability_score`.

## [0.7.0a0] - 2026-05-07

### Added
- `models.TrustBifurcation` — two-axis self-trust DTO splitting
  ``competence_confidence`` (capability reliability) from
  ``integrity_confidence`` (signal pipeline trust). The
  ``aggregate`` property combines them via geometric mean so a
  weakness on either axis penalizes the score.
- `models.UncertaintyType` enum — typed taxonomy distinguishing
  ``PROBABILITY``, ``AMBIGUITY``, and ``IGNORANCE``. Lets a host ask
  whether a confidence value reflects a modeled probability, a
  competing-models hedge, or a no-model placeholder.
- `models.TrustReport` — composite host-facing DTO bundling
  ``TrustBifurcation``, ``UncertaintyType``, competing-hypothesis
  labels, calibration status, trajectory band, and a free-form
  recommendation string. The surface hosts surface to humans.
- `interpret.ConfusionWeighter` (and helpers ``cost_weighted_argmin``,
  ``expected_cost``) — typed cost-matrix error shaper that picks the
  class minimizing expected cost given a host-supplied
  ``{predicted: {true: cost}}`` matrix. Returns a
  ``ConfusionDecision`` recording both the cost-weighted choice and
  the naive arg-max baseline. ``ConfusionWeighter.from_uniform``
  builds a starter matrix with asymmetric FP/FN costs.

### Notes
- ``MetaConfidence`` (Gaussian-over-confidence), ``TrustTrajectory``
  (parametric trust-evolution curve), ``MiscalibrationPattern``
  detector, and ``CoherenceWarning`` emergence-anomaly detector
  (originally proposed) deferred. The CalibrationTracker shipped in
  Phase B already produces per-decile warnings; multi-agent
  coherence belongs in a host adapter.

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
