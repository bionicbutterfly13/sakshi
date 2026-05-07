"""Tests for DeliberationGate."""

from __future__ import annotations

import pytest

from sakshi.meta import DeliberationGate, DeliberationPath


def test_high_confidence_low_failure_stays_routine() -> None:
    gate = DeliberationGate()
    decision = gate.decide(
        confidence=0.9, recent_failure_rate=0.1, remaining_budget=1.0
    )
    assert decision.path == DeliberationPath.ROUTINE
    assert decision.escalated is False


def test_low_confidence_escalates() -> None:
    gate = DeliberationGate(confidence_floor=0.6)
    decision = gate.decide(
        confidence=0.3, recent_failure_rate=0.1, remaining_budget=1.0
    )
    assert decision.path == DeliberationPath.DELIBERATIVE
    assert "confidence" in decision.reason


def test_high_failure_escalates() -> None:
    gate = DeliberationGate(failure_ceiling=0.4)
    decision = gate.decide(
        confidence=0.9, recent_failure_rate=0.7, remaining_budget=1.0
    )
    assert decision.path == DeliberationPath.DELIBERATIVE
    assert "failure" in decision.reason


def test_low_budget_keeps_routine_even_with_low_confidence() -> None:
    gate = DeliberationGate(budget_floor=0.2)
    decision = gate.decide(
        confidence=0.1, recent_failure_rate=0.9, remaining_budget=0.05
    )
    assert decision.path == DeliberationPath.ROUTINE
    assert "budget" in decision.reason


def test_invalid_thresholds_rejected() -> None:
    with pytest.raises(ValueError):
        DeliberationGate(confidence_floor=1.5)
    with pytest.raises(ValueError):
        DeliberationGate(failure_ceiling=-0.1)


def test_invalid_inputs_rejected() -> None:
    gate = DeliberationGate()
    with pytest.raises(ValueError):
        gate.decide(confidence=2.0, recent_failure_rate=0.0, remaining_budget=1.0)
