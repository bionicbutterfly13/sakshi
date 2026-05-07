"""Tests for the episode-retrieval extensions on GoalOutcomeMemory."""

from __future__ import annotations

import pytest

from sakshi.goals.outcome_memory import GoalOutcomeMemory
from sakshi.models import GoalOutcomeRecord, GoalStatus


def _record(predicate: str, status: GoalStatus, goal_id: str) -> GoalOutcomeRecord:
    return GoalOutcomeRecord(
        goal_id=goal_id,
        predicate_name=predicate,
        outcome_status=status,
    )


def test_recent_returns_newest_first() -> None:
    mem = GoalOutcomeMemory()
    for i in range(5):
        mem.record(_record("ON", GoalStatus.ACHIEVED, f"g-{i}"))
    recent = mem.recent(3)
    assert [r.goal_id for r in recent] == ["g-4", "g-3", "g-2"]


def test_recent_zero_returns_empty() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    assert mem.recent(0) == []


def test_recent_negative_rejected() -> None:
    mem = GoalOutcomeMemory()
    with pytest.raises(ValueError):
        mem.recent(-1)


def test_find_similar_filters_by_predicate() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    mem.record(_record("CLEAR", GoalStatus.ACHIEVED, "g-2"))
    mem.record(_record("ON", GoalStatus.ABANDONED, "g-3"))
    matches = mem.find_similar(predicate_name="ON")
    assert [r.goal_id for r in matches] == ["g-3", "g-1"]


def test_find_similar_filters_by_outcome_status() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    mem.record(_record("ON", GoalStatus.ABANDONED, "g-2"))
    matches = mem.find_similar(predicate_name="ON", outcome_status=GoalStatus.ABANDONED)
    assert [r.goal_id for r in matches] == ["g-2"]


def test_find_similar_respects_limit() -> None:
    mem = GoalOutcomeMemory()
    for i in range(20):
        mem.record(_record("ON", GoalStatus.ACHIEVED, f"g-{i}"))
    assert len(mem.find_similar(predicate_name="ON", limit=5)) == 5


def test_hit_rate_overall() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    mem.record(_record("ON", GoalStatus.ABANDONED, "g-2"))
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-3"))
    assert mem.hit_rate() == pytest.approx(2 / 3)


def test_hit_rate_per_predicate() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    mem.record(_record("CLEAR", GoalStatus.ABANDONED, "g-2"))
    assert mem.hit_rate(predicate_name="ON") == 1.0
    assert mem.hit_rate(predicate_name="CLEAR") == 0.0
    assert mem.hit_rate(predicate_name="UNKNOWN") == 0.0


def test_len_reflects_records() -> None:
    mem = GoalOutcomeMemory()
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-1"))
    mem.record(_record("ON", GoalStatus.ACHIEVED, "g-2"))
    assert len(mem) == 2
    mem.clear()
    assert len(mem) == 0
