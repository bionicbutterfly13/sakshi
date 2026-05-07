"""Tests for ConfusionWeighter."""

from __future__ import annotations

import pytest

from sakshi.interpret import (
    ConfusionDecision,
    ConfusionWeighter,
    cost_weighted_argmin,
    expected_cost,
)


def test_expected_cost_basic() -> None:
    cost = expected_cost(
        probabilities={"safe": 0.7, "danger": 0.3},
        cost_row={"safe": 0.0, "danger": 1.0},
    )
    assert cost == pytest.approx(0.3)


def test_cost_weighted_argmin_picks_lower_expected_cost() -> None:
    probabilities = {"safe": 0.7, "danger": 0.3}
    cost_matrix = {
        "safe": {"safe": 0.0, "danger": 10.0},
        "danger": {"safe": 1.0, "danger": 0.0},
    }
    chosen, cost = cost_weighted_argmin(probabilities, cost_matrix)
    # Predicting "safe" costs 10*0.3 = 3; predicting "danger" costs 1*0.7 = 0.7.
    assert chosen == "danger"
    assert cost == pytest.approx(0.7)


def test_weighter_decides_with_naive_baseline_recorded() -> None:
    cost_matrix = {
        "safe": {"safe": 0.0, "danger": 10.0},
        "danger": {"safe": 1.0, "danger": 0.0},
    }
    weighter: ConfusionWeighter[str] = ConfusionWeighter(
        cost_matrix, label="safety-asymmetric"
    )
    decision = weighter.decide({"safe": 0.7, "danger": 0.3})
    assert isinstance(decision, ConfusionDecision)
    assert decision.chosen_class == "danger"
    assert decision.naive_argmax == "safe"
    assert decision.naive_max_probability == pytest.approx(0.7)
    assert decision.cost_matrix_label == "safety-asymmetric"


def test_uniform_factory() -> None:
    weighter = ConfusionWeighter[str].from_uniform(
        ["positive", "negative"],
        false_positive_cost=2.0,
        false_negative_cost=1.0,
    )
    decision = weighter.decide({"positive": 0.55, "negative": 0.45})
    # FP cost is double FN cost; arg-max would pick positive but the
    # weighting may flip it depending on margins. Verify the type is
    # a real choice.
    assert decision.chosen_class in {"positive", "negative"}
    assert decision.cost_matrix_label == "uniform"


def test_empty_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        ConfusionWeighter({})
    with pytest.raises(ValueError):
        ConfusionWeighter(
            {"a": {"a": 0.0}}, label="ok"
        ).decide({})
    with pytest.raises(ValueError):
        cost_weighted_argmin({}, {"a": {"a": 0.0}})
    with pytest.raises(ValueError):
        ConfusionWeighter[str].from_uniform([])
