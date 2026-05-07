"""Tests for RebelHook + RebelDecision."""

from __future__ import annotations

from collections.abc import Iterable

from sakshi.goals import (
    AcceptingRebelHook,
    RebelDecision,
    RebelHook,
    RebelVerdict,
)
from sakshi.models import (
    CognitiveExpectation,
    Goal,
    GoalPredicate,
)


def _goal() -> Goal:
    return Goal(id="g-1", predicate=GoalPredicate(name="ON", args={"x": "A"}))


def test_default_hook_accepts() -> None:
    decision = AcceptingRebelHook().on_goal_assignment(_goal(), [])
    assert decision.verdict == RebelVerdict.ACCEPT
    assert decision.goal is not None


def test_decision_factories() -> None:
    g = _goal()
    accept = RebelDecision.accept(g, "ok")
    assert accept.verdict == RebelVerdict.ACCEPT
    assert accept.goal is g

    rewrite = RebelDecision.rewrite(g, "rewritten because X")
    assert rewrite.verdict == RebelVerdict.REWRITE
    assert rewrite.reason == "rewritten because X"

    reject = RebelDecision.reject("no")
    assert reject.verdict == RebelVerdict.REJECT
    assert reject.goal is None


def test_protocol_runtime_check() -> None:
    class CustomHook:
        def on_goal_assignment(
            self,
            goal: Goal,
            expectations: Iterable[CognitiveExpectation],
        ) -> RebelDecision:
            del expectations
            return RebelDecision.reject("test refuses everything")

    hook: RebelHook = CustomHook()
    assert isinstance(hook, RebelHook)
    decision = hook.on_goal_assignment(_goal(), [])
    assert decision.verdict == RebelVerdict.REJECT


def test_decision_is_frozen() -> None:
    import dataclasses

    import pytest

    decision = RebelDecision.accept(_goal())
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.reason = "changed"  # type: ignore[misc]
