"""Tests for GoalMode, GoalEvent, and Goal.record_transition."""

from __future__ import annotations

from sakshi.models import (
    Goal,
    GoalEvent,
    GoalEventType,
    GoalMode,
    GoalPredicate,
    GoalStatus,
)


def _make_goal() -> Goal:
    return Goal(
        id="g-1",
        predicate=GoalPredicate(name="ON", args={"x": "A"}),
    )


def test_goal_default_mode_is_formulating() -> None:
    goal = _make_goal()
    assert goal.mode == GoalMode.FORMULATING
    assert goal.transitions == []


def test_record_transition_appends_event_and_updates_mode() -> None:
    goal = _make_goal()
    event = goal.record_transition(
        event_type=GoalEventType.SELECTED,
        to_mode=GoalMode.SELECTED,
        cause="picked by selector",
        cycle_id="cycle-001",
    )
    assert isinstance(event, GoalEvent)
    assert event.event_type == GoalEventType.SELECTED
    assert event.from_mode == GoalMode.FORMULATING
    assert event.to_mode == GoalMode.SELECTED
    assert event.cause == "picked by selector"
    assert event.cycle_id == "cycle-001"
    assert goal.mode == GoalMode.SELECTED
    assert goal.transitions == [event]


def test_status_and_mode_are_orthogonal() -> None:
    goal = _make_goal()
    assert goal.status == GoalStatus.ACTIVE
    goal.record_transition(
        event_type=GoalEventType.DISPATCHED,
        to_mode=GoalMode.DISPATCHED,
    )
    # Mode advanced; status untouched.
    assert goal.mode == GoalMode.DISPATCHED
    assert goal.status == GoalStatus.ACTIVE


def test_transition_without_to_mode_keeps_mode() -> None:
    goal = _make_goal()
    goal.mode = GoalMode.MONITORING
    goal.record_transition(
        event_type=GoalEventType.MONITOR_OK,
    )
    assert goal.mode == GoalMode.MONITORING
    assert goal.transitions[-1].from_mode == GoalMode.MONITORING
    assert goal.transitions[-1].to_mode is None


def test_goal_serialises_transitions() -> None:
    goal = _make_goal()
    goal.record_transition(
        event_type=GoalEventType.SELECTED, to_mode=GoalMode.SELECTED
    )
    payload = goal.model_dump()
    rebuilt = Goal.model_validate(payload)
    assert len(rebuilt.transitions) == 1
    assert rebuilt.mode == GoalMode.SELECTED
