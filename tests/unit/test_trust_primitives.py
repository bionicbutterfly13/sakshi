"""Tests for TrustBifurcation, UncertaintyType, TrustReport."""

from __future__ import annotations

import pytest

from sakshi.models import TrustBifurcation, TrustReport, UncertaintyType


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


def test_trust_report_minimal() -> None:
    report = TrustReport(cycle_id="c-1")
    assert report.uncertainty_type == UncertaintyType.PROBABILITY
    assert report.trust.competence_confidence == 0.5
    assert report.competing_hypothesis_labels == ()


def test_trust_report_full_round_trip() -> None:
    original = TrustReport(
        cycle_id="c-1",
        subject="anomaly:event-7",
        trust=TrustBifurcation(competence_confidence=0.85, integrity_confidence=0.9),
        uncertainty_type=UncertaintyType.AMBIGUITY,
        competing_hypothesis_labels=("model_a", "model_b"),
        calibration_status="well_calibrated",
        trajectory="stable",
        recommendation="verify_before_action",
        notes="two close-to-equiprobable models",
    )
    rebuilt = TrustReport.model_validate(original.model_dump())
    assert rebuilt == original
    assert rebuilt.trust.aggregate > 0.8
