"""Tests for CanalizationMetrics."""

from __future__ import annotations

import pytest

from sakshi.meta import (
    CanalizationMetrics,
    CanalizationRisk,
    metrics_from_static_cycles,
)


def test_default_metrics_are_healthy() -> None:
    m = CanalizationMetrics()
    assert m.depth == 0.0
    assert m.dwell_time == 0
    assert m.risk == CanalizationRisk.HEALTHY


def test_depth_thresholds() -> None:
    assert CanalizationMetrics(depth=0.4).risk == CanalizationRisk.HEALTHY
    assert CanalizationMetrics(depth=0.5).risk == CanalizationRisk.HEALTHY
    assert CanalizationMetrics(depth=0.6).risk == CanalizationRisk.DEEPENING
    assert CanalizationMetrics(depth=0.79).risk == CanalizationRisk.DEEPENING
    assert CanalizationMetrics(depth=0.8).risk == CanalizationRisk.PATHOLOGICAL
    assert CanalizationMetrics(depth=1.0).risk == CanalizationRisk.PATHOLOGICAL


def test_metrics_validation_rejects_out_of_band() -> None:
    with pytest.raises(ValueError):
        CanalizationMetrics(depth=1.1)
    with pytest.raises(ValueError):
        CanalizationMetrics(depth=-0.01)
    with pytest.raises(ValueError):
        CanalizationMetrics(dwell_time=-1)
    with pytest.raises(ValueError):
        CanalizationMetrics(perturbation_resistance=2.0)
    with pytest.raises(ValueError):
        CanalizationMetrics(temperature_sensitivity=-0.1)


def test_factory_from_static_cycles() -> None:
    m = metrics_from_static_cycles(
        static_cycles=4,
        max_history=10,
        perturbation_count=2,
        perturbation_capacity=5,
        temperature_sensitivity=0.3,
    )
    assert m.depth == 0.4
    assert m.dwell_time == 4
    assert m.perturbation_resistance == 0.4
    assert m.temperature_sensitivity == 0.3
    assert m.risk == CanalizationRisk.HEALTHY


def test_factory_clamps_depth_to_one() -> None:
    m = metrics_from_static_cycles(static_cycles=20, max_history=10)
    assert m.depth == 1.0
    assert m.risk == CanalizationRisk.PATHOLOGICAL


def test_factory_requires_positive_max_history() -> None:
    with pytest.raises(ValueError):
        metrics_from_static_cycles(static_cycles=1, max_history=0)


def test_metrics_are_frozen() -> None:
    from dataclasses import FrozenInstanceError

    m = CanalizationMetrics(depth=0.6)
    with pytest.raises(FrozenInstanceError):
        m.depth = 0.1  # type: ignore[misc]
