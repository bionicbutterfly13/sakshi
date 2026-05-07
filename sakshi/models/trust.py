"""Typed trust + uncertainty primitives.

Sakshi modules attach confidence scalars to many of the events they
emit. ``confidence`` alone collapses two distinct questions a host
operator needs to answer separately:

1. **Competence**: how reliable was the *capability* that produced
   this output?
2. **Integrity**: how trustworthy is the *signal itself* — was the
   pipeline that produced it tampered with, censored, or unverified?

This module supplies the typed primitives that keep those questions
separate, plus a typed taxonomy of *what kind* of uncertainty a
confidence value reflects, and a composite ``TrustReport`` DTO hosts
can surface to humans.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UncertaintyType(StrEnum):
    """What kind of uncertainty a confidence value reflects.

    * ``PROBABILITY`` — classical: the output is one of N hypotheses,
      and confidence reports the modeled probability.
    * ``AMBIGUITY`` — multiple competing hypotheses are roughly
      equiprobable; the host should hedge.
    * ``IGNORANCE`` — no model; confidence is a placeholder.
    """

    PROBABILITY = "probability"
    AMBIGUITY = "ambiguity"
    IGNORANCE = "ignorance"


class UncertaintyBoundary(StrEnum):
    """Where the uncertainty appears to live.

    ``UncertaintyType`` answers what kind of confidence statement the
    report is making. ``UncertaintyBoundary`` answers what response the
    host should consider: gather samples, widen hypotheses, admit there
    is no model, or reframe the model itself.
    """

    STOCHASTIC = "stochastic"
    AMBIGUOUS = "ambiguous"
    IGNORANT = "ignorant"
    EPISTEMIC = "epistemic"
    ONTOLOGICAL = "ontological"


class TrustBifurcation(BaseModel):
    """Two-axis self-trust scalar attached to an event or report.

    ``competence_confidence`` reports how reliable the producing
    capability is, given recent calibration; ``integrity_confidence``
    reports how trustworthy the signal pipeline is. A single integrity
    breach can collapse trust faster than competence drift; the
    separation gives operators a typed handle.
    """

    competence_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Reliability of the capability that produced this output.",
    )
    integrity_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Trust that the signal itself was not tampered with, "
            "censored, or otherwise compromised in transit."
        ),
    )

    @property
    def aggregate(self) -> float:
        """Single scalar combining both axes via the geometric mean.

        The geometric mean penalizes a weakness on either axis: a
        competent capability with a compromised pipeline scores low,
        and vice versa.
        """
        return (self.competence_confidence * self.integrity_confidence) ** 0.5


class TrustRepairAction(StrEnum):
    """Typed repair move a host may take after a degraded trust report."""

    GATHER_EVIDENCE = "gather_evidence"
    WIDEN_HYPOTHESES = "widen_hypotheses"
    RECALIBRATE_MODULE = "recalibrate_module"
    VERIFY_INTEGRITY = "verify_integrity"
    ESCALATE_TO_OPERATOR = "escalate_to_operator"
    REFRAME_MODEL = "reframe_model"


class TrustRepairRecommendation(BaseModel):
    """Typed recommendation for restoring or routing trust.

    Sakshi records the recommended repair but does not execute it. Hosts
    decide whether the action means collecting sensor evidence,
    adjusting module profiles, escalating to an operator, or trying a
    different model family.
    """

    action: TrustRepairAction
    reason: str = Field(
        min_length=1,
        description="Why this repair action is recommended.",
    )
    target: str = Field(
        default="",
        description=(
            "Optional host label for the affected module, goal, plan, or signal."
        ),
    )
    severity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How urgently the host should consider this repair.",
    )
    uncertainty_boundary: UncertaintyBoundary | None = Field(
        default=None,
        description="Optional boundary classification that motivated the repair.",
    )
    evidence_needed: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Host-specific evidence keys that would support the repair.",
    )


class TrustReport(BaseModel):
    """Composite host-facing trust DTO.

    Bundles the bifurcation, uncertainty type, list of competing
    hypothesis labels (when ``uncertainty_type == AMBIGUITY``), a
    calibration status string, a coarse trajectory band, and a
    machine-readable recommendation. Hosts surface this to humans or
    to downstream automation.
    """

    cycle_id: str
    subject: str = Field(
        default="",
        description=(
            "What the report is about: 'goal:gid', 'anomaly:event-7', "
            "'plan:p-3', etc. Free-form for host convenience."
        ),
    )
    trust: TrustBifurcation = Field(default_factory=TrustBifurcation)
    uncertainty_type: UncertaintyType = UncertaintyType.PROBABILITY
    uncertainty_boundary: UncertaintyBoundary = UncertaintyBoundary.STOCHASTIC
    competing_hypothesis_labels: tuple[str, ...] = Field(default_factory=tuple)
    calibration_status: str = Field(
        default="unknown",
        description=(
            "Free-form label: 'well_calibrated', 'overconfident', "
            "'underconfident', 'unknown'."
        ),
    )
    trajectory: str = Field(
        default="stable",
        description=(
            "Coarse band: 'improving', 'stable', 'deteriorating', "
            "'at_risk_of_collapse'."
        ),
    )
    recommendation: str = Field(
        default="",
        description=(
            "Free-form, host-facing: 'safe_to_automate', "
            "'verify_before_action', 'escalate'."
        ),
    )
    repair_recommendations: tuple[TrustRepairRecommendation, ...] = Field(
        default_factory=tuple,
        description="Typed trust-repair recommendations hosts may route or surface.",
    )
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "TrustBifurcation",
    "TrustRepairAction",
    "TrustRepairRecommendation",
    "TrustReport",
    "UncertaintyBoundary",
    "UncertaintyType",
]
