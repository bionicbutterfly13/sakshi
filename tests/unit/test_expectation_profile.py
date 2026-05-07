"""Tests for the 5-property ExpectationProfile."""

from __future__ import annotations

import pytest

from sakshi.models import ExpectationProfile, ExpectationSeverity, FailureMode


def test_minimal_profile_has_sane_defaults() -> None:
    p = ExpectationProfile(module_name="planner")
    assert p.module_name == "planner"
    assert p.runtime_bound_seconds == 2.0
    assert p.output_schema == {}
    assert p.confidence_range == (0.0, 1.0)
    assert p.side_effects_contract == ()
    assert p.failure_modes == ()


def test_full_profile() -> None:
    p = ExpectationProfile(
        module_name="planner",
        runtime_bound_seconds=1.5,
        output_schema={"type": "Plan"},
        confidence_range=(0.4, 0.95),
        side_effects_contract=("goal_graph", "blackboard"),
        failure_modes=(
            FailureMode(name="empty_plan", severity=ExpectationSeverity.CRITICAL),
            FailureMode(name="timeout"),
        ),
    )
    assert p.confidence_in_band(0.5) is True
    assert p.confidence_in_band(0.99) is False
    assert p.confidence_in_band(0.39) is False
    assert p.is_declared_failure("empty_plan") is True
    assert p.is_declared_failure("crash") is False
    assert p.has_side_effect("goal_graph") is True
    assert p.has_side_effect("filesystem") is False


def test_invalid_confidence_range_rejected() -> None:
    with pytest.raises(ValueError):
        ExpectationProfile(module_name="m", confidence_range=(0.5, 0.4))
    with pytest.raises(ValueError):
        ExpectationProfile(module_name="m", confidence_range=(-0.1, 0.5))
    with pytest.raises(ValueError):
        ExpectationProfile(module_name="m", confidence_range=(0.0, 1.5))


def test_runtime_bound_must_be_non_negative() -> None:
    with pytest.raises(ValueError):
        ExpectationProfile(module_name="m", runtime_bound_seconds=-0.1)


def test_round_trip() -> None:
    original = ExpectationProfile(
        module_name="planner",
        runtime_bound_seconds=1.5,
        output_schema="Plan",
        confidence_range=(0.4, 0.95),
        side_effects_contract=("goal_graph",),
        failure_modes=(FailureMode(name="empty_plan"),),
    )
    rebuilt = ExpectationProfile.model_validate(original.model_dump())
    assert rebuilt == original
