"""Tests for AnticipatoryRiskScorer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from sakshi.plans import (
    AnticipatoryRiskScorer,
    PlanRisk,
    RiskBand,
    aggregate_risk_score,
    classify_band,
)


def test_plan_risk_validates() -> None:
    with pytest.raises(ValueError):
        PlanRisk(step_name="s", description="x", likelihood=1.5, impact=0.1)
    with pytest.raises(ValueError):
        PlanRisk(step_name="s", description="x", likelihood=0.1, impact=2.0)


def test_severity() -> None:
    risk = PlanRisk(step_name="s", description="x", likelihood=0.5, impact=0.4)
    assert risk.severity == pytest.approx(0.2)


def test_aggregate_score_empty_is_zero() -> None:
    assert aggregate_risk_score([], expected_benefit=0.5) == 0.0


def test_aggregate_score_invalid_benefit_rejected() -> None:
    with pytest.raises(ValueError):
        aggregate_risk_score([], expected_benefit=1.5)


def test_aggregate_score_high_benefit_absorbs_risk() -> None:
    risk = PlanRisk("s", "boom", likelihood=0.6, impact=0.6)
    high_benefit = aggregate_risk_score([risk], expected_benefit=1.0)
    low_benefit = aggregate_risk_score([risk], expected_benefit=0.0)
    assert high_benefit < low_benefit


def test_classify_band_thresholds() -> None:
    assert classify_band(0.1) == RiskBand.LOW
    assert classify_band(0.33) == RiskBand.LOW
    assert classify_band(0.34) == RiskBand.MEDIUM
    assert classify_band(0.65) == RiskBand.MEDIUM
    assert classify_band(0.66) == RiskBand.HIGH
    assert classify_band(1.0) == RiskBand.HIGH


def test_scorer_pipeline() -> None:
    class FixedRiskModel:
        def identify(
            self,
            plan_id: str,
            plan_steps: Sequence[str],
            world_state: dict[str, Any] | None = None,
        ) -> tuple[PlanRisk, ...]:
            del plan_id, plan_steps, world_state
            return (
                PlanRisk("s1", "minor", likelihood=0.2, impact=0.2),
                PlanRisk("s2", "major", likelihood=0.7, impact=0.6),
            )

    scorer = AnticipatoryRiskScorer(FixedRiskModel())
    assessment = scorer.assess(
        plan_id="p-1",
        plan_steps=["s1", "s2"],
        expected_benefit=0.5,
    )
    assert len(assessment.risks) == 2
    assert 0.0 <= assessment.risk_score <= 1.0
    assert assessment.band in (RiskBand.LOW, RiskBand.MEDIUM, RiskBand.HIGH)


def test_scorer_no_risks_low_band() -> None:
    class EmptyModel:
        def identify(self, plan_id, plan_steps, world_state=None):
            del plan_id, plan_steps, world_state
            return ()

    scorer = AnticipatoryRiskScorer(EmptyModel())
    assessment = scorer.assess(plan_id="p", plan_steps=[])
    assert assessment.risk_score == 0.0
    assert assessment.band == RiskBand.LOW
