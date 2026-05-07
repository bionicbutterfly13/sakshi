"""Tests for MetaSchedulingPolicy and three default policies."""

from __future__ import annotations

from sakshi.meta import (
    CanalizationMetrics,
    CanalizationRisk,
    EveryCyclePolicy,
    MetaSchedulingPolicy,
    OnAnomalyPolicy,
    SchedulingDecision,
    ThrottledByLoadPolicy,
)


def _healthy() -> CanalizationMetrics:
    return CanalizationMetrics(depth=0.1)


def _pathological() -> CanalizationMetrics:
    return CanalizationMetrics(depth=0.9)


def test_protocol_runtime_check() -> None:
    assert isinstance(EveryCyclePolicy(), MetaSchedulingPolicy)
    assert isinstance(OnAnomalyPolicy(), MetaSchedulingPolicy)
    assert isinstance(ThrottledByLoadPolicy(), MetaSchedulingPolicy)


def test_every_cycle_always_runs() -> None:
    p = EveryCyclePolicy()
    decision = p.decide_to_run(anomalies_since_last_run=0, canalization=_healthy())
    assert decision.should_run is True
    decision2 = p.decide_to_run(
        anomalies_since_last_run=5, canalization=_pathological()
    )
    assert decision2.should_run is True


def test_on_anomaly_only_runs_when_anomaly_present() -> None:
    p = OnAnomalyPolicy()
    no_anomaly = p.decide_to_run(anomalies_since_last_run=0, canalization=_healthy())
    assert no_anomaly.should_run is False
    with_anomaly = p.decide_to_run(anomalies_since_last_run=2, canalization=_healthy())
    assert with_anomaly.should_run is True


def test_throttled_runs_in_healthy_load() -> None:
    p = ThrottledByLoadPolicy()
    decision = p.decide_to_run(anomalies_since_last_run=0, canalization=_healthy())
    assert decision.should_run is True


def test_throttled_skips_in_pathological_load() -> None:
    p = ThrottledByLoadPolicy(always_run_on_anomaly=False)
    decision = p.decide_to_run(anomalies_since_last_run=0, canalization=_pathological())
    assert decision.should_run is False


def test_throttled_anomaly_override_runs_during_pathological_load() -> None:
    p = ThrottledByLoadPolicy(always_run_on_anomaly=True)
    decision = p.decide_to_run(anomalies_since_last_run=1, canalization=_pathological())
    assert decision.should_run is True
    assert "anomaly override" in decision.reason


def test_throttled_skips_pathological_when_override_off() -> None:
    p = ThrottledByLoadPolicy(always_run_on_anomaly=False)
    decision = p.decide_to_run(anomalies_since_last_run=5, canalization=_pathological())
    assert decision.should_run is False


def test_throttled_max_run_risk_at_pathological_permits_all() -> None:
    p = ThrottledByLoadPolicy(
        max_run_risk=CanalizationRisk.PATHOLOGICAL,
        always_run_on_anomaly=False,
    )
    decision = p.decide_to_run(anomalies_since_last_run=0, canalization=_pathological())
    assert decision.should_run is True


def test_decision_is_frozen() -> None:
    decision = SchedulingDecision(should_run=True, reason="x")
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.should_run = False  # type: ignore[misc]
