# Sakshi 0.4 → 0.9 — Evolution of the Platform

A narrative account of how Sakshi grew from a small metacognitive
runtime into a typed-monitoring substrate. Each section describes
what Sakshi gained at that release, why the capability mattered,
and what it lets a host application do.

---

## What Sakshi is

Sakshi is a Python library that lets a host application embed a
*Witness* into its agent: a watcher that observes plan execution,
evaluates against expectations, and steers cognition without doing
the cognition itself. The package is small, deterministic, and
dependency-light. It exposes typed seams; the host supplies
concrete services.

Across seven releases, Sakshi grew the typed primitives a Witness
needs to do its job — module contracts, anomaly lanes, goal
lifecycles, trust calibration, motivation envelopes, and
defensive guards — without ever importing a host runtime or a
heavy machine-learning dependency.

---

## 0.4.0 — Typed seams

Sakshi gained the foundational data shapes every later release
depends on.

**Anomaly lanes.** Every detected anomaly now carries an
`AnomalySourceType` tag at detection: `WORLD`, `COGNITIVE`, or
`COMPOUND`. World-level anomalies route to world-model corrections;
cognitive-level anomalies route to meta-cycle adjustments. Tagging
the lane at the source prevents calibration metrics and
explanations from blending the two streams into a single muddied
signal.

**Goal lifecycle.** Goals gained a `GoalMode` axis (formulating,
selected, dispatched, monitoring, repairing, deferred, completed)
orthogonal to the existing `GoalStatus`. Each goal also carries a
`transitions` list of typed `GoalEvent` records and a
`record_transition` helper. Hosts can now ask both *is this goal
still in play* and *what is the goal currently doing* with a single
attribute lookup.

**Goal operations.** A `GoalOperation` enum names the eleven
canonical lifecycle verbs (formulate, select, expand, commit,
dispatch, monitor, evaluate, repair, defer, delegate, resume).
Hosts subscribe to `GoalOperationEvent` records on the event bus
and read goal-reasoning timelines as a queryable stream rather
than reconstructing them from scattered emissions.

**Discrepancy resolution.** A new `DiscrepancyResolution` DTO
captures the four-step chain `symptom → explanation → goal → plan`
end-to-end at either the object or meta level. The same shape works
on both levels by design.

**Tiered transparency.** A `TransparencyLevel` enum and three tier
DTOs (`StatusTransparency`, `ReasoningTransparency`,
`ProjectionTransparency`) let hosts surface agent reasoning to
humans at the right depth for each consumer.

**Goal constraints.** A frozen `GoalConstraint` DTO carries
`(initial_state, safety_constraints, goal_conditions,
integrity_critical)`. The `integrity_critical` flag is the
contract surface that downstream defensive guards use to refuse
dropping the constraint.

**Trace pruning.** A `TracePruner` protocol with three default
implementations (`LastNPruner`, `SinceAnomalyPruner`,
`WhereExpectationFiredPruner`) bounds the meta-cycle's input on
long-running agents.

**Plan decomposition.** A `TaskDecomposer` protocol and `Action`
DTO define the seam where hosts plug in HTN-style or other
structured planners. The package itself imports no planner.

**Module replacement.** A new `REPLACE_MODULE` control action
distinguishes the case where the meta-cycle installs a
fundamentally different implementation from the case where it
swaps to a known alternative (`SWAP_MODULE`).

The release closed with a small cleanup pass that removed two
control-action enum entries and an emitter module that did not
belong in the package's process. The underlying signal returned
in 0.5 as a properly typed model.

---

## 0.5.0 — Metacognitive substrate

Sakshi gained the typed-monitoring surface the Witness pattern
actually needs.

**Module contracts.** A new `ExpectationProfile` lets every module
that participates in a cycle declare five things: a runtime bound,
an output schema, a confidence range, a side-effects contract, and
admissible failure modes. Three convenience methods cover the
common checks: `confidence_in_band`, `is_declared_failure`, and
`has_side_effect`. Sakshi watches the running module against the
declaration; mismatches produce typed `ExpectationViolation`
records routed through the standard event flow.

**Stuck-loop detection.** A frozen `CanalizationMetrics` struct
(depth, dwell time, perturbation resistance, temperature
sensitivity) plus a three-band `CanalizationRisk` classifier
(`HEALTHY`, `DEEPENING`, `PATHOLOGICAL`) flags the situation where
an agent's planner cycles through near-identical actions without
the world state changing. Hosts route on the band: widen search
precision, swap a module, or escalate.

**Intervention validation.** Every metacognitive control action
now passes through an `InterventionExecutor` before it fires. The
executor checks a per-`(action_type, target)` cooldown, calls a
host-supplied permission policy, and records every decision in a
bounded audit history. An optional outcome callback lets the host
report whether the intervention worked. The default
`AlwaysPermitPolicy` is test-friendly; production hosts inject
their own policy.

**Confidence calibration.** A sliding-window `CalibrationTracker`
records `(predicted_confidence, actually_correct)` pairs and
reports two things: a single `self_trust_score` in `[0, 1]`
summarizing whether the agent's confidence claims line up with
reality, and a list of per-decile `CalibrationWarning` records
identifying which confidence bands are miscalibrated.

**Goal lineage.** A `GoalLineageAuditor` walks the
`source_goal_id` chain produced by `GoalTransformer` and reports a
typed `LineageReport` with depth, widening-step count, transform
chain, and a verdict: `ALIGNED`, `WARN`, or `DRIFTED`. The auditor
never intervenes; it returns a typed signal a host routes to a
pre-INTEND gate or an operator dashboard.

**Outcome retrieval.** The existing `GoalOutcomeMemory` typed log
gained three accessors: `recent(n)` for the newest records,
`find_similar(predicate_name=…)` for predicate-matched lookups,
and `hit_rate(predicate_name=…)` for the fraction-achieved scalar.

---

## 0.6.0 — Decision-quality upgrades

Sakshi gained the typed primitives a host needs to make better
decisions on top of the substrate.

**Meta-cycle scheduling.** A `MetaSchedulingPolicy` protocol with
three defaults — `EveryCyclePolicy`, `OnAnomalyPolicy`, and
`ThrottledByLoadPolicy` — decides whether the meta-cycle should
run on the current iteration. The throttled policy reads
`CanalizationMetrics` directly and skips runs when load is
pathological, with a configurable anomaly override that forces a
run during high-load anomalies.

**Deliberation gate.** A `DeliberationGate` is a pure threshold
function that recommends a routine or deliberative reasoning path
given current confidence, recent failure rate, and remaining
budget. Conservative defaults: stay routine unless confidence is
below 0.6 *or* failure rate is above 0.4 *and* budget remains
above the floor. The gate is decision-only; it never executes
either path.

**Goal-assignment rebellion.** A `RebelHook` protocol lets the
meta-layer evaluate an assigned goal against the agent's declared
expectations and return one of three verdicts: accept the goal
unchanged, rewrite to a substitute that resolves the same intent,
or refuse with a reason. The default `AcceptingRebelHook` is
backward-compatible; production hosts inject their own.

**Anticipatory risk.** An `AnticipatoryRiskScorer` runs the
three-step pipeline (identify per-step risks, aggregate, classify
into a `RiskBand`) on a candidate plan and returns a frozen
`PlanRiskAssessment`. The host's `RiskModel` supplies the
domain-specific risk identification; Sakshi supplies the typed
pipeline so every plan produces a comparable assessment.

**Intervention pattern taxonomy.** An `InterventionType` enum
labels what *pattern* of intervention is happening (pause and
re-evaluate, drop confidence, widen search, relax goal, flush
memory, trigger exploration, suspend recovery, escalate to
operator) — orthogonal to `ControlActionType` which names the
*mechanism*. One mechanism can serve many patterns; the pattern
label keeps audit records intelligible.

**Failure-axis classification.** A `TRAPDimension` enum tags each
`FailureMode` along the four-axis taxonomy (Transparency,
Reasoning, Adaptation, Perception). Resolution order is
deterministic: an explicit `trap:<axis>` marker in the description
wins over keyword matching against name and description. A
`TRAPRouter` maps each axis to a recommended `ControlActionType`
(Reasoning to swap, Perception to strengthen, Adaptation to
adjust precision, Transparency to suppress); host-supplied
routing overrides defaults.

**Competing-hypothesis distribution.** `AnomalyExplainer` gained
an `explain_distribution(top_k=N)` method that returns up to N
ranked competing hypotheses instead of collapsing to a single
best guess. Hosts hedge across diagnoses when the top-1
confidence does not exceed the runner-up by a comfortable margin.

---

## 0.7.0 — Trust calibration and uncertainty

Sakshi gained the typed primitives needed to be honest about its
own confidence on the right axes.

**Two-axis self-trust.** A `TrustBifurcation` DTO splits self-trust
into `competence_confidence` (capability reliability) and
`integrity_confidence` (signal pipeline trust). The `aggregate`
property combines them via geometric mean, so a weakness on either
axis penalizes the score. The separation gives operators a typed
handle on which axis is failing.

**Uncertainty taxonomy.** A `UncertaintyType` enum distinguishes
three modes: `PROBABILITY` (a single modeled hypothesis),
`AMBIGUITY` (multiple equiprobable hypotheses), and `IGNORANCE`
(no model). Hosts route differently in each case.

**Composite trust report.** A `TrustReport` DTO bundles a
`TrustBifurcation`, an `UncertaintyType`, the labels of competing
hypotheses, a calibration status string, a coarse trajectory
band, and a free-form recommendation. This is the surface humans
see.

**Cost-matrix error shaping.** A `ConfusionWeighter` reweights an
arg-max-style classification decision against a host-supplied
cost matrix and picks the class minimizing expected cost rather
than the most probable class. The returned `ConfusionDecision`
records both the cost-weighted choice and the naive arg-max
baseline so audit trails show what the asymmetric cost structure
actually changed. A `from_uniform` factory builds a starter
matrix from a class list plus FP/FN cost scalars.

---

## 0.8.0 — Motivation surface

Sakshi gained the typed surface for observing intrinsic motivation
without modelling it.

**Motivation taxonomy.** A `MotivationType` enum names eight
motivation sources: achievement, affiliation, power, novelty,
competence, surprise, extrinsic, and unclassified. Hosts tag
every intrinsic goal with the type that produced it. The package
never generates motivation; it observes the host's record.

**Motivation events.** A `MotivationEvent` DTO is the immutable
record produced for every activation, including rejections. A
`MotivationAuditor` stores them in a bounded ring buffer and
exposes accessors: `record`, `filter_by_type`, `acceptance_rate`,
and a typed `metrics()` view.

**Creativity envelope.** A host-declared `CreativityEnvelope`
bounds the motivation system's creativity: allowed predicates,
forbidden attributes, a maximum novelty score, and forbidden
motivation types. The pure function `evaluate_envelope` returns
a typed `EnvelopeVerdict`. Goals outside the envelope are
rejected with a reason, and the rejection flows through the
auditor — operators can later query the system about rejected
impulses.

**Relevance filter.** A `GoalRelevanceFilter` checks motivated
goals against a host-declared value-tag taxonomy. An optional
`require_value_tag` strict mode rejects goals carrying no tags
at all.

**Quality metrics.** A frozen `ComputationalMotivationMetrics`
bundle reports four bounded scalars over the auditor window:
diversity (how concentrated the motivation distribution is),
stability (whether acceptance rates are oscillating), risk (the
fraction of events from the power and surprise classes), and
communication cost (how much narrative the system is producing).
Hosts route on simple thresholds.

---

## 0.9.0 — Defensive guards

Sakshi gained the typed validation seams that defend against the
two classic failure modes a generally-capable autonomous system
must withstand.

**Reward integrity.** A `RewardIntegrityGuard` protocol validates
goal-achievement claims against a host-supplied set of exogenous
evidence keys (sensor readings, completed tool calls, observed
state-change events). The default
`EvidenceRequiringRewardIntegrityGuard` permits a claim only when
at least `min_evidence` keys are present, and refuses otherwise
with a typed reason. This prevents the pattern where an agent
silently records *goal achieved* without the world having moved.

**Modification integrity.** A `ModificationIntegrityGuard`
protocol validates a proposed `GoalConstraint` rewrite. The
default `IntegrityCriticalModificationGuard` refuses both demoting
a constraint flagged `integrity_critical=True` to non-critical and
dropping any of its safety constraints. This closes the contract
the `integrity_critical` flag introduced in 0.4.

**Shared verdict shape.** Both guards return a typed
`GuardVerdict` with a boolean `permitted` shortcut. A
`make_audit_record` helper wraps any verdict in a frozen
`GuardAuditRecord` for streaming through a host event bus.

**Knowledge-reward balance.** A `KnowledgeRewardBalance` enum
(`KNOWLEDGE`, `REWARD`, `HYBRID`) and two predicate helpers —
`biases_toward_exploration` and `biases_against_exploration` —
give hosts a typed handle for deciding whether to suppress a
curiosity-motivated goal under budget pressure.

The release also formalized five durable principles in the
project's principle document — anomaly-lane integrity, two-axis
self-trust, the goal-creativity envelope, goal interrogability,
and defensive-guard discipline — so the rules that produced the
typed surface outlast any single contributor.

---

## What 0.9 means

Sakshi at 0.9 is what the package was meant to be. The Witness has
a real typed surface. Every event coming out of Sakshi can be
checked against a declared contract. Every confidence claim can
be calibrated against ground-truth. Every intervention leaves a
typed audit trail. Every long-running goal can be checked
against its origin. Every motivated goal passes through a
host-declared envelope. Every achievement claim passes through a
guard that requires exogenous evidence.

The package imports no host runtime, no FastAPI, no graph
database, no machine-learning framework. The seams hosts use to
plug in their own services are typed protocols. The data shapes
that cross those seams are typed DTOs. The library is small,
deterministic, and ready for hosts to build against.
