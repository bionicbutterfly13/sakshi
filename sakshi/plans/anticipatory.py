"""Anticipatory risk scoring for plans.

A small EVAL-phase helper that takes a candidate plan plus the host's
risk model and returns a typed ``PlanRiskAssessment``: where the plan
has identified risks, the cost-benefit estimate, and a single
``risk_score`` scalar a host can route on.

The shape mirrors the three-step framework from the anticipatory
thinking literature: identify, estimate cost-benefit, decide. Sakshi
does not implement the host's domain-specific risk model — it
provides the typed pipeline so the host's model produces a comparable
report on every plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class RiskBand(StrEnum):
    """Three coarse bands derived from the numeric ``risk_score``."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


LOW_RISK_CEILING = 0.33
HIGH_RISK_FLOOR = 0.66


@dataclass(frozen=True)
class PlanRisk:
    """One identified risk on one plan step."""

    step_name: str
    description: str
    likelihood: float  # [0, 1]
    impact: float  # [0, 1]
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.likelihood <= 1.0:
            raise ValueError("likelihood must be in [0, 1]")
        if not 0.0 <= self.impact <= 1.0:
            raise ValueError("impact must be in [0, 1]")

    @property
    def severity(self) -> float:
        """Product of likelihood and impact, in [0, 1]."""
        return self.likelihood * self.impact


@dataclass(frozen=True)
class PlanRiskAssessment:
    """Aggregated assessment over one plan's identified risks."""

    plan_id: str
    risks: tuple[PlanRisk, ...] = ()
    expected_benefit: float = 0.5
    risk_score: float = field(default=0.0)
    band: RiskBand = field(default=RiskBand.LOW)
    notes: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.expected_benefit <= 1.0:
            raise ValueError("expected_benefit must be in [0, 1]")
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be in [0, 1]")


@runtime_checkable
class RiskModel(Protocol):
    """Host-supplied identifier for plan-step risks.

    Implementations inspect the plan + world state and return a tuple
    of ``PlanRisk`` records. The package never inspects host state
    directly.
    """

    def identify(
        self,
        plan_id: str,
        plan_steps: Sequence[str],
        world_state: dict[str, Any] | None = None,
    ) -> tuple[PlanRisk, ...]: ...


def aggregate_risk_score(
    risks: Sequence[PlanRisk],
    *,
    expected_benefit: float = 0.5,
) -> float:
    """Combine per-step risks and benefit into a single score in [0, 1].

    Strategy: take the maximum severity (so one big risk dominates)
    and reduce by ``(1 - expected_benefit) ** 2`` so a high-benefit
    plan can absorb more risk than a low-benefit plan can.
    """

    if not 0.0 <= expected_benefit <= 1.0:
        raise ValueError("expected_benefit must be in [0, 1]")
    if not risks:
        return 0.0
    worst = max(risk.severity for risk in risks)
    benefit_discount = (1.0 - expected_benefit) ** 2
    return min(1.0, worst * benefit_discount + worst * 0.5)


def classify_band(risk_score: float) -> RiskBand:
    """Map a numeric risk score to a coarse three-band label."""
    if risk_score >= HIGH_RISK_FLOOR:
        return RiskBand.HIGH
    if risk_score > LOW_RISK_CEILING:
        return RiskBand.MEDIUM
    return RiskBand.LOW


class AnticipatoryRiskScorer:
    """Three-step risk pipeline for the EVAL phase.

    Step 1: ``risk_model.identify(...)`` enumerates per-step risks.
    Step 2: ``aggregate_risk_score`` reduces them plus ``expected_benefit``
            into one scalar.
    Step 3: ``classify_band`` maps the scalar to a coarse label.

    Every call returns a frozen ``PlanRiskAssessment``.
    """

    def __init__(self, risk_model: RiskModel) -> None:
        self._risk_model = risk_model

    def assess(
        self,
        *,
        plan_id: str,
        plan_steps: Sequence[str],
        world_state: dict[str, Any] | None = None,
        expected_benefit: float = 0.5,
        notes: str = "",
    ) -> PlanRiskAssessment:
        risks = tuple(
            self._risk_model.identify(plan_id, plan_steps, world_state)
        )
        score = aggregate_risk_score(risks, expected_benefit=expected_benefit)
        band = classify_band(score)
        return PlanRiskAssessment(
            plan_id=plan_id,
            risks=risks,
            expected_benefit=expected_benefit,
            risk_score=score,
            band=band,
            notes=notes,
        )


__all__ = [
    "HIGH_RISK_FLOOR",
    "LOW_RISK_CEILING",
    "AnticipatoryRiskScorer",
    "PlanRisk",
    "PlanRiskAssessment",
    "RiskBand",
    "RiskModel",
    "aggregate_risk_score",
    "classify_band",
]
