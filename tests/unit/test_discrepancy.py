"""Tests for the DiscrepancyResolution DTO."""

from __future__ import annotations

import pytest

from sakshi.models import (
    AnomalySourceType,
    DiscrepancyResolution,
    ResolutionLevel,
)


def test_object_level_resolution_minimal() -> None:
    res = DiscrepancyResolution(
        cycle_id="cycle-1",
        level=ResolutionLevel.OBJECT,
        symptom="block A is not clear",
        explanation="block A is on fire",
    )
    assert res.level == ResolutionLevel.OBJECT
    assert res.source == AnomalySourceType.WORLD
    assert res.confidence == 0.5
    assert res.goal_id is None
    assert res.plan_id is None


def test_meta_level_resolution_with_lane_override() -> None:
    res = DiscrepancyResolution(
        cycle_id="cycle-2",
        level=ResolutionLevel.META,
        source=AnomalySourceType.COGNITIVE,
        symptom="planner returned no plan (impasse)",
        explanation="planner module unsuitable for current goal class",
        goal_id="meta-g-1",
        plan_id="meta-p-1",
        confidence=0.8,
    )
    assert res.source == AnomalySourceType.COGNITIVE
    assert res.goal_id == "meta-g-1"
    assert res.plan_id == "meta-p-1"


def test_round_trip() -> None:
    original = DiscrepancyResolution(
        cycle_id="cycle-3",
        level=ResolutionLevel.OBJECT,
        source=AnomalySourceType.COMPOUND,
        symptom="symptom",
        explanation="explanation",
    )
    rebuilt = DiscrepancyResolution.model_validate(original.model_dump())
    assert rebuilt.source == original.source
    assert rebuilt.level == original.level


def test_confidence_bounds_enforced() -> None:
    with pytest.raises(ValueError):
        DiscrepancyResolution(
            cycle_id="cycle-4",
            level=ResolutionLevel.OBJECT,
            symptom="x",
            explanation="y",
            confidence=1.5,
        )
    with pytest.raises(ValueError):
        DiscrepancyResolution(
            cycle_id="cycle-5",
            level=ResolutionLevel.OBJECT,
            symptom="x",
            explanation="y",
            confidence=-0.1,
        )
