# Feature Specification: 1.0 Readiness Review

**Feature Branch**: `feature/1-0-readiness-review`

**Created**: 2026-07-16

**Status**: Ready for Planning

**Input**: User description: "Review Sakshi's public API stability, host-adapter ergonomics, configuration skeleton, and remaining meta-layer work so the next implementation steps toward 1.0 can be chosen from current evidence."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish the Public Contract Baseline (Priority: P1)

As a Sakshi maintainer, I need every exported public contract assessed against
the documented pre-1.0 stability commitment so I can see which interfaces are
ready to preserve and which require a deliberate compatibility decision.

**Why this priority**: A 1.0 plan cannot be credible until the current public
surface is fully known and compatibility risks are explicit.

**Independent Test**: Compare the review inventory with the complete exported
public surface and confirm that every export has one compatibility disposition,
supporting evidence, and any required follow-up.

**Acceptance Scenarios**:

1. **Given** the current public export surface, **When** the readiness review is completed, **Then** every exported symbol is classified as preserve, revise before 1.0, deprecate, or remove before 1.0.
2. **Given** a symbol classified for revision, deprecation, or removal, **When** its finding is read, **Then** the compatibility impact and evidence for that decision are explicit.

---

### User Story 2 - Validate the Host Integration Experience (Priority: P2)

As a host integrator, I need a clear construction and lifecycle path for Sakshi
so I can wire protocols, safe defaults, recovery state, and failure handling
without relying on hidden global behavior or repository-specific knowledge.

**Why this priority**: Sakshi's value depends on remaining easy to embed while
the host retains ownership of runtime services and side effects.

**Independent Test**: Walk the documented integration path from installation to
runtime construction and shutdown, and verify that every host responsibility is
named, demonstrated, and consistent across public documentation and examples.

**Acceptance Scenarios**:

1. **Given** a new host integration, **When** an integrator follows the reviewed path, **Then** required protocols, lifecycle ownership, safe defaults, and cleanup responsibilities are identifiable without reading package internals.
2. **Given** a convenience API with stateless or stateful behavior, **When** it appears in the integration path, **Then** the state boundary and host responsibility are unambiguous.

---

### User Story 3 - Select the Next Implementation Tranche (Priority: P3)

As a project maintainer, I need the unfinished configuration and meta-layer work
ranked with dependencies and acceptance conditions so I can choose the next
coherent Spec Kit feature instead of reopening historical planning artifacts.

**Why this priority**: The current quality ledger identifies unfinished areas,
but it does not yet turn those areas into a decision-ready sequence.

**Independent Test**: Confirm that each unfinished area has a current evidence
summary, a package-versus-host boundary decision, and a prioritized next action
that can be converted into a separate specification.

**Acceptance Scenarios**:

1. **Given** the configuration area is currently incomplete, **When** the review closes, **Then** it has a readiness verdict, justified scope, dependencies, and measurable next-step acceptance conditions.
2. **Given** the meta area still has documented gaps, **When** the review closes, **Then** package work is separated from host-adapter work and the highest-leverage package work is prioritized.
3. **Given** all review findings, **When** maintainers choose what to build next, **Then** they can select from a ranked set of no more than three coherent implementation tranches.

### Edge Cases

- A public symbol is exported but absent from the stability document or API documentation.
- Documentation claims a lifecycle or safety guarantee that differs from tested behavior.
- An apparent package gap is actually host-owned and must not be pulled into Sakshi core.
- A quality label is stale relative to current code, tests, or examples.
- A recommendation would combine public API redesign, host rewiring, and unrelated cleanup in one tranche.
- Evidence is unavailable or indirect; the review must mark the conclusion unverified rather than infer readiness.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The review MUST inventory every symbol in Sakshi's exported public surface and assign exactly one compatibility disposition: preserve, revise before 1.0, deprecate, or remove before 1.0.
- **FR-002**: Each non-preserve disposition MUST include direct evidence, affected user behavior, and the compatibility obligation it creates.
- **FR-003**: The review MUST reconcile the exported surface with the stability commitment, API documentation, architecture documentation, examples, and current tests.
- **FR-004**: The review MUST map the complete host integration journey, including construction, required protocol injection, safe defaults, state ownership, failure propagation, recovery lifecycle, and shutdown or cleanup responsibilities.
- **FR-005**: The review MUST identify host-integration friction, ambiguity, or missing guidance and classify each finding by severity and whether it belongs in package core, documentation, an example, or a host adapter.
- **FR-006**: The review MUST assess the current configuration area and meta area against their quality labels using current code, tests, and documentation rather than historical plans.
- **FR-007**: Every unfinished-area finding MUST state the desired outcome, package boundary, dependencies, acceptance evidence, and explicit exclusions.
- **FR-008**: The review MUST produce a ranked set of no more than three coherent implementation tranches for subsequent Spec Kit specifications.
- **FR-009**: Every conclusion MUST cite direct repository evidence or be marked unverified with the missing evidence named.
- **FR-010**: The review MUST distinguish blockers, pre-1.0 requirements, post-1.0 candidates, and host-only work.
- **FR-011**: The review MUST update the quality ledger when current evidence contradicts an existing quality label.
- **FR-012**: The review MUST NOT change public runtime behavior; implementation changes require separate accepted specifications.

### Compatibility & Boundary Constraints *(mandatory)*

- **CB-001**: This review lane does not itself change the public Python API, serialized data shapes, documented runtime behavior, or minimum supported Python version.
- **CB-002**: Recommendations MUST preserve explicit host ownership and MUST NOT introduce package-level runtime service getters, implicit construction, or module-global lifecycle state.
- **CB-003**: Recommendations involving dependencies, configuration, persistence, security, or failure behavior MUST identify the compatibility and migration impact before they can enter planning.
- **CB-004**: The review deliverable requires evidence from tests, API docs, examples, the quality ledger, and the full repository gate; any later behavior change requires focused regression tests and documentation updates.
- **CB-005**: Implementing recommendations, wiring a concrete host runtime, changing release metadata, and declaring 1.0 are out of scope for this review lane.

### Key Entities

- **Public Contract Record**: One exported symbol, its documented purpose, compatibility disposition, evidence, and required follow-up.
- **Host Integration Responsibility**: One construction, lifecycle, safety, state, or cleanup obligation owned by the host or package.
- **Readiness Finding**: An evidence-backed gap or confirmation with severity, ownership boundary, timing, and acceptance evidence.
- **Implementation Tranche**: A coherent, separately specifiable body of follow-up work with dependencies, success conditions, and exclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of exported public symbols receive exactly one compatibility disposition with supporting evidence.
- **SC-002**: 100% of public host protocols and documented runtime defaults are mapped to an explicit owner and lifecycle responsibility.
- **SC-003**: Every configuration and meta-layer gap has a verified readiness finding or is explicitly marked unverified with the missing evidence named.
- **SC-004**: The final recommendation contains no more than three ranked implementation tranches, and each tranche has dependencies, acceptance evidence, and out-of-scope boundaries.
- **SC-005**: A maintainer can select the next implementation specification using the review packet without consulting ignored historical planning material.
- **SC-006**: The review introduces no runtime behavior change and the repository's full quality gate remains green.

## Assumptions

- The current merged `main` branch is the authoritative implementation baseline.
- `sakshi.__all__`, published API documentation, and the stability commitment together define the public review surface.
- Current tests and examples are evidence of supported behavior, but absence of a failing test is not proof of a documented guarantee.
- Host-specific particle lifecycle and LinOSS/AIS dispatch remain outside package core unless direct evidence shows a missing reusable protocol seam.
- The next implementation tranche will receive its own Spec Kit specification rather than being implemented inside this review lane.

## Out of Scope

- Implementing configuration fields or meta-layer capabilities.
- Adding a concrete host adapter, persistence backend, web framework, graph database, or model SDK to package core.
- Changing, deprecating, or removing public symbols during the review.
- Releasing or declaring Sakshi 1.0.
- Re-importing ignored `.archive/` material into active planning context.
