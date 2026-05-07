"""Tests for the GoalOperation taxonomy."""

from __future__ import annotations

import pytest

from sakshi.models import (
    GOAL_OPERATION_EVENT_TYPE,
    GoalOperation,
    GoalOperationEvent,
)


def test_canonical_lifecycle_verbs_present() -> None:
    expected = {
        "formulate",
        "select",
        "expand",
        "commit",
        "dispatch",
        "monitor",
        "evaluate",
        "repair",
        "defer",
        "delegate",
        "resume",
    }
    assert {member.value for member in GoalOperation} == expected


def test_event_construction_minimal() -> None:
    event = GoalOperationEvent(
        operation=GoalOperation.FORMULATE,
        goal_id="g-99",
    )
    assert event.operation == GoalOperation.FORMULATE
    assert event.goal_id == "g-99"
    assert event.cause == ""
    assert event.metadata == {}


def test_event_round_trip() -> None:
    original = GoalOperationEvent(
        operation=GoalOperation.REPAIR,
        goal_id="g-7",
        cycle_id="cycle-12",
        cause="plan deviation exceeded threshold",
        metadata={"deviation_ratio": "0.42"},
    )
    rebuilt = GoalOperationEvent.model_validate(original.model_dump())
    assert rebuilt == original


def test_default_event_type_string() -> None:
    assert GOAL_OPERATION_EVENT_TYPE == "sakshi.goal.op"


def test_unknown_operation_rejected() -> None:
    with pytest.raises(ValueError):
        GoalOperation("retire")
