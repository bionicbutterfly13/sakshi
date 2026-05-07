"""Tests for AnomalyExplainer.explain_distribution."""

from __future__ import annotations

import pytest

from sakshi.goals import AnomalyExplainer
from sakshi.interpret import AnomalyEvent


def _event(current: dict[str, float], baseline: dict[str, float]) -> AnomalyEvent:
    return AnomalyEvent(
        a_distance=0.7,
        current_activations=current,
        baseline_mean=baseline,
    )


@pytest.mark.asyncio
async def test_distribution_returns_top_k_ranked() -> None:
    explainer = AnomalyExplainer()
    event = _event(
        current={"alpha": 1.0, "beta": 0.5, "gamma": 0.2, "delta": 0.0},
        baseline={"alpha": 0.0, "beta": 0.4, "gamma": 0.3, "delta": 0.0},
    )
    distribution = await explainer.explain_distribution(event, top_k=3)
    assert len(distribution) == 3
    # Sorted by descending confidence.
    confidences = [exp.confidence for exp in distribution]
    assert confidences == sorted(confidences, reverse=True)


@pytest.mark.asyncio
async def test_distribution_empty_inputs_falls_back_to_single_explain() -> None:
    explainer = AnomalyExplainer()
    event = _event(current={}, baseline={})
    distribution = await explainer.explain_distribution(event, top_k=3)
    assert len(distribution) == 1


@pytest.mark.asyncio
async def test_distribution_top_k_cap() -> None:
    explainer = AnomalyExplainer()
    event = _event(
        current={"a": 1.0, "b": 0.9, "c": 0.5},
        baseline={"a": 0.0, "b": 0.0, "c": 0.5},
    )
    distribution = await explainer.explain_distribution(event, top_k=2)
    assert len(distribution) == 2


@pytest.mark.asyncio
async def test_distribution_invalid_top_k_rejected() -> None:
    explainer = AnomalyExplainer()
    event = _event(current={"a": 1.0}, baseline={"a": 0.0})
    with pytest.raises(ValueError):
        await explainer.explain_distribution(event, top_k=0)
