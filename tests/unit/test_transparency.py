"""Tests for TransparencyLevel and the three tier DTOs."""

from __future__ import annotations

from sakshi.models import (
    ProjectionTransparency,
    ReasoningTransparency,
    StatusTransparency,
    TransparencyLevel,
)


def test_levels_are_distinct() -> None:
    assert TransparencyLevel.STATUS.value == "status"
    assert TransparencyLevel.REASONING.value == "reasoning"
    assert TransparencyLevel.PROJECTION.value == "projection"


def test_status_minimal() -> None:
    s = StatusTransparency(cycle_id="cycle-1")
    assert s.active_goal_ids == []
    assert s.pending_plan_ids == []
    assert s.summary == ""


def test_reasoning_round_trip() -> None:
    original = ReasoningTransparency(
        cycle_id="cycle-2",
        selected_motivator="anomaly:basin_shift",
        candidate_explanations=["a", "b"],
        chosen_explanation="a",
        choice_rationale="higher confidence",
        confidence=0.72,
    )
    rebuilt = ReasoningTransparency.model_validate(original.model_dump())
    assert rebuilt == original


def test_projection_with_forecast() -> None:
    p = ProjectionTransparency(
        cycle_id="cycle-3",
        horizon_steps=4,
        forecast_states=[{"step": 1, "state": "x"}],
        resource_forecast={"cpu": 0.4},
        risk_estimates={"failure": 0.1},
    )
    assert p.horizon_steps == 4
    assert p.resource_forecast == {"cpu": 0.4}
    assert p.risk_estimates == {"failure": 0.1}
