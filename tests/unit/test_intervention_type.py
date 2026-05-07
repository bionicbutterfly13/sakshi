"""Tests for the InterventionType taxonomy + InterventionRecord.pattern field."""

from __future__ import annotations

from sakshi.meta import (
    InterventionExecutor,
    InterventionOutcome,
    InterventionType,
)
from sakshi.models import ControlAction, ControlActionType


def _action() -> ControlAction:
    return ControlAction(
        action_type=ControlActionType.ADJUST_PRECISION,
        target="attention",
        magnitude=0.1,
        rationale="test",
    )


def test_taxonomy_members() -> None:
    expected = {
        "pause_and_reevaluate",
        "drop_confidence",
        "widen_search",
        "relax_goal",
        "flush_memory",
        "trigger_exploration",
        "suspend_recovery",
        "escalate_to_operator",
    }
    assert {member.value for member in InterventionType} == expected


def test_record_carries_pattern_when_supplied() -> None:
    executor = InterventionExecutor()
    record = executor.validate(_action(), pattern=InterventionType.WIDEN_SEARCH)
    assert record.pattern == InterventionType.WIDEN_SEARCH


def test_record_pattern_default_is_none() -> None:
    executor = InterventionExecutor()
    record = executor.validate(_action())
    assert record.pattern is None


def test_record_outcome_preserves_pattern() -> None:
    executor = InterventionExecutor()
    record = executor.validate(_action(), pattern=InterventionType.DROP_CONFIDENCE)
    updated = executor.record_outcome(record, InterventionOutcome.SUCCESS)
    assert updated.pattern == InterventionType.DROP_CONFIDENCE
    assert updated.outcome == InterventionOutcome.SUCCESS
