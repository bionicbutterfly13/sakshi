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

- Package tests MUST run without any private host repository on `PYTHONPATH`.
- Host adapter tests belong in the host repository.
- Any skipped external integration test MUST report as skipped, not silently passed.

## Documentation

- Behavior-changing changes SHOULD update docs in the same commit.
- New package areas SHOULD update `docs/quality.md`.
- Public docs SHOULD describe what Sakshi does before describing influences.

## Anomaly lane integrity

- Every detected anomaly MUST carry an `AnomalySourceType` tag at detection
  (`WORLD`, `COGNITIVE`, or `COMPOUND`).
- World-level anomalies trigger world-model corrections; cognitive
  anomalies trigger meta-cycle adjustments. Compound anomalies MUST
  be decomposed at detection, not at explanation.
- Calibration metrics SHOULD be reported per lane. Cross-lane
  aggregates conflate object-level and meta-level signals and
  mislead host operators.

## Two-axis self-trust

- Self-trust MUST be reported on two axes (`competence_confidence`
  and `integrity_confidence`); a single integrity claim MUST NOT be
  inferred from competence history.
- A single integrity breach decays trust faster than competence
  drift; the separation gives operators a typed handle on which
  axis is failing.

## Goal-creativity envelope

- Creative goal generation belongs to the host, not to Sakshi.
- When a host runs an intrinsic-motivation system, creative outputs
  MUST be validated against an explicit `CreativityEnvelope`
  declared by the host.
- Goals beyond the envelope MUST be rejected with reason and the
  rejection logged in `MotivationAuditor`. Suppressing rejections
  silently defeats the audit purpose.

## Goal interrogability

- Every goal in flight SHOULD be traceable back to its source: a
  motivation type, a host instruction, or a discrepancy resolution.
- Goals reaching pre-INTEND with no traceable source SHOULD raise a
  `GoalLineageAuditor` warning so operators can decide.

## Defensive guard discipline

- A goal-achievement claim SHOULD pass through a
  `RewardIntegrityGuard` before it is recorded; the guard validates
  the claim against host-supplied exogenous evidence.
- A `GoalConstraint` flagged `integrity_critical=True` MUST NOT be
  silently demoted or have its safety constraints dropped by the
  meta-layer; a `ModificationIntegrityGuard` enforces this.
