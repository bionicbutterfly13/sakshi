"""Tests for the Phase E motivation primitives."""

from __future__ import annotations

import pytest

from sakshi.goals import MotivationAuditor
from sakshi.models import (
    ComputationalMotivationMetrics,
    CreativityEnvelope,
    GoalRelevanceFilter,
    MotivationEvent,
    MotivationType,
    evaluate_envelope,
)


def test_motivation_type_taxonomy() -> None:
    expected = {
        "achievement",
        "affiliation",
        "power",
        "novelty",
        "competence",
        "surprise",
        "extrinsic",
        "unclassified",
    }
    assert {member.value for member in MotivationType} == expected


def test_envelope_accepts_within_bounds() -> None:
    envelope = CreativityEnvelope(
        allowed_predicates=("ON", "CLEAR"),
        forbidden_attributes=("target_human",),
        max_novelty_score=0.7,
    )
    verdict = evaluate_envelope(
        envelope=envelope,
        motivation_type=MotivationType.ACHIEVEMENT,
        predicate_name="ON",
        predicate_args={"x": "A"},
        novelty_score=0.5,
    )
    assert verdict.accepted is True


def test_envelope_rejects_forbidden_motivation_type() -> None:
    envelope = CreativityEnvelope(
        forbidden_motivation_types=(MotivationType.POWER,),
    )
    verdict = evaluate_envelope(
        envelope=envelope,
        motivation_type=MotivationType.POWER,
        predicate_name="ANYTHING",
    )
    assert verdict.accepted is False
    assert "power motivation" in verdict.reason


def test_envelope_rejects_disallowed_predicate() -> None:
    envelope = CreativityEnvelope(allowed_predicates=("ON",))
    verdict = evaluate_envelope(
        envelope=envelope,
        motivation_type=MotivationType.NOVELTY,
        predicate_name="DESTROY",
    )
    assert verdict.accepted is False
    assert verdict.violated_field == "predicate_name"


def test_envelope_rejects_forbidden_attribute() -> None:
    envelope = CreativityEnvelope(forbidden_attributes=("target_human",))
    verdict = evaluate_envelope(
        envelope=envelope,
        motivation_type=MotivationType.ACHIEVEMENT,
        predicate_name="MOVE",
        predicate_args={"target_human": "operator"},
    )
    assert verdict.accepted is False
    assert verdict.violated_field == "target_human"


def test_envelope_caps_novelty() -> None:
    envelope = CreativityEnvelope(max_novelty_score=0.5)
    verdict = evaluate_envelope(
        envelope=envelope,
        motivation_type=MotivationType.NOVELTY,
        predicate_name="X",
        novelty_score=0.9,
    )
    assert verdict.accepted is False
    assert verdict.violated_field == "novelty_score"


def test_relevance_filter_accepts_overlap() -> None:
    f = GoalRelevanceFilter(allowed_value_tags=("safety", "throughput"))
    verdict = f.evaluate(("throughput",))
    assert verdict.accepted is True


def test_relevance_filter_rejects_disjoint_tags() -> None:
    f = GoalRelevanceFilter(allowed_value_tags=("safety",))
    verdict = f.evaluate(("entertainment",))
    assert verdict.accepted is False


def test_relevance_filter_requires_tags_when_configured() -> None:
    permissive = GoalRelevanceFilter(allowed_value_tags=("safety",))
    strict = GoalRelevanceFilter(
        allowed_value_tags=("safety",), require_value_tag=True
    )
    assert permissive.evaluate(()).accepted is True
    assert strict.evaluate(()).accepted is False


def test_auditor_records_and_metrics_empty() -> None:
    auditor = MotivationAuditor()
    metrics = auditor.metrics()
    assert metrics.diversity_score == 0.0
    assert metrics.stability_score == 1.0
    assert metrics.risk_assessment == 0.0


def test_auditor_metrics_diversity_and_risk() -> None:
    auditor = MotivationAuditor()
    for _ in range(4):
        auditor.record(
            MotivationEvent(motivation_type=MotivationType.ACHIEVEMENT)
        )
    for _ in range(4):
        auditor.record(
            MotivationEvent(motivation_type=MotivationType.POWER)
        )
    metrics = auditor.metrics()
    assert 0.9 < metrics.diversity_score <= 1.0
    assert metrics.risk_assessment == 0.5


def test_auditor_acceptance_rate() -> None:
    auditor = MotivationAuditor()
    auditor.record(
        MotivationEvent(
            motivation_type=MotivationType.ACHIEVEMENT, accepted=True
        )
    )
    auditor.record(
        MotivationEvent(
            motivation_type=MotivationType.ACHIEVEMENT, accepted=False
        )
    )
    auditor.record(
        MotivationEvent(
            motivation_type=MotivationType.ACHIEVEMENT, accepted=True
        )
    )
    assert auditor.acceptance_rate() == pytest.approx(2 / 3)


def test_auditor_filter_by_type() -> None:
    auditor = MotivationAuditor()
    auditor.record(MotivationEvent(motivation_type=MotivationType.NOVELTY))
    auditor.record(MotivationEvent(motivation_type=MotivationType.POWER))
    novelty_only = auditor.filter_by_type(MotivationType.NOVELTY)
    assert len(novelty_only) == 1


def test_metrics_validates_bounds() -> None:
    with pytest.raises(ValueError):
        ComputationalMotivationMetrics(
            diversity_score=1.5,
            stability_score=0.5,
            risk_assessment=0.0,
            communication_cost=0.0,
        )
