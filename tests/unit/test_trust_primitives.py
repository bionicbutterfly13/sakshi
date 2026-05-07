"""Tests for trust and uncertainty primitives."""

from __future__ import annotations

import pytest

from sakshi.models import (
    TrustBifurcation,
    TrustRepairAction,
    TrustRepairRecommendation,
    TrustReport,
    UncertaintyBoundary,
    UncertaintyType,
)


def test_default_bifurcation() -> None:
    t = TrustBifurcation()
    assert t.competence_confidence == 0.5
    assert t.integrity_confidence == 1.0


def test_aggregate_geometric_mean() -> None:
    t = TrustBifurcation(competence_confidence=0.81, integrity_confidence=1.0)
    assert t.aggregate == pytest.approx(0.9)


def test_aggregate_penalizes_either_axis() -> None:
    competent_only = TrustBifurcation(
        competence_confidence=0.9, integrity_confidence=0.1
    )
    intact_only = TrustBifurcation(competence_confidence=0.1, integrity_confidence=0.9)
    balanced = TrustBifurcation(competence_confidence=0.7, integrity_confidence=0.7)
    assert competent_only.aggregate < balanced.aggregate
    assert intact_only.aggregate < balanced.aggregate


def test_bifurcation_validates_bounds() -> None:
    with pytest.raises(ValueError):
        TrustBifurcation(competence_confidence=1.5)
    with pytest.raises(ValueError):
        TrustBifurcation(integrity_confidence=-0.1)


def test_uncertainty_type_values() -> None:
    assert {member.value for member in UncertaintyType} == {
        "probability",
        "ambiguity",
        "ignorance",
    }


def test_uncertainty_boundary_values() -> None:
    assert {member.value for member in UncertaintyBoundary} == {
        "stochastic",
        "ambiguous",
        "ignorant",
        "epistemic",
        "ontological",
    }


def test_trust_report_minimal() -> None:
    report = TrustReport(cycle_id="c-1")
    assert report.uncertainty_type == UncertaintyType.PROBABILITY
    assert report.uncertainty_boundary == UncertaintyBoundary.STOCHASTIC
    assert report.trust.competence_confidence == 0.5
    assert report.competing_hypothesis_labels == ()
    assert report.repair_recommendations == ()


def test_trust_repair_action_values() -> None:
    assert {member.value for member in TrustRepairAction} == {
        "gather_evidence",
        "widen_hypotheses",
        "recalibrate_module",
        "verify_integrity",
        "escalate_to_operator",
        "reframe_model",
    }


def test_repair_recommendation_defaults_and_validation() -> None:
    rec = TrustRepairRecommendation(
        action=TrustRepairAction.GATHER_EVIDENCE,
        reason="Sensor evidence is missing.",
    )
    assert rec.target == ""
    assert rec.severity == 0.5
    assert rec.uncertainty_boundary is None
    assert rec.evidence_needed == ()

    with pytest.raises(ValueError):
        TrustRepairRecommendation(
            action=TrustRepairAction.ESCALATE_TO_OPERATOR,
            reason="Invalid severity.",
            severity=1.5,
        )


def test_repair_recommendation_round_trip() -> None:
    original = TrustRepairRecommendation(
        action=TrustRepairAction.REFRAME_MODEL,
        reason="The model class may not cover the observed behavior.",
        target="plan:risk-assessment",
        severity=0.9,
        uncertainty_boundary=UncertaintyBoundary.ONTOLOGICAL,
        evidence_needed=("operator_review", "alternative_model"),
    )
    rebuilt = TrustRepairRecommendation.model_validate(original.model_dump())
    assert rebuilt == original


def test_trust_report_full_round_trip() -> None:
    repair = TrustRepairRecommendation(
        action=TrustRepairAction.WIDEN_HYPOTHESES,
        reason="Two close-to-equiprobable explanations remain.",
        target="anomaly:event-7",
        severity=0.7,
        uncertainty_boundary=UncertaintyBoundary.AMBIGUOUS,
        evidence_needed=("runner_up_hypothesis",),
    )
    original = TrustReport(
        cycle_id="c-1",
        subject="anomaly:event-7",
        trust=TrustBifurcation(competence_confidence=0.85, integrity_confidence=0.9),
        uncertainty_type=UncertaintyType.AMBIGUITY,
        uncertainty_boundary=UncertaintyBoundary.AMBIGUOUS,
        competing_hypothesis_labels=("model_a", "model_b"),
        calibration_status="well_calibrated",
        trajectory="stable",
        recommendation="verify_before_action",
        repair_recommendations=(repair,),
        notes="two close-to-equiprobable models",
    )
    rebuilt = TrustReport.model_validate(original.model_dump())
    assert rebuilt == original
    assert rebuilt.trust.aggregate > 0.8
    assert (
        rebuilt.repair_recommendations[0].action == TrustRepairAction.WIDEN_HYPOTHESES
    )
