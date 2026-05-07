"""Goal-assignment rebel hook.

When a host posts a goal, the agent does not have to accept it
unconditionally. The ``RebelHook`` protocol gives the meta-layer a
chance to evaluate every assigned goal against its declared
expectations and either accept, rewrite, or refuse with a reason.

Three response shapes:

* ``RebelDecision.accept(goal)`` — go ahead, no objection.
* ``RebelDecision.rewrite(new_goal, reason)`` — accept a different
  goal that resolves the same intent without violating expectations.
* ``RebelDecision.reject(reason)`` — refuse the goal entirely.

The hook itself does not enforce the decision; it returns a typed
verdict the host's INTEND phase reads. Hosts that reject the verdict
can override (audit trails make that visible).

The default ``AcceptingRebelHook`` is what most hosts want at first:
no rebellions, full backward compatibility. Hosts opt in by injecting
their own implementation.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from sakshi.models import CognitiveExpectation, Goal


class RebelVerdict(StrEnum):
    """Three response shapes a rebel hook may return."""

    ACCEPT = "accept"
    REWRITE = "rewrite"
    REJECT = "reject"


@dataclass(frozen=True)
class RebelDecision:
    """Typed verdict from a ``RebelHook.on_goal_assignment`` call."""

    verdict: RebelVerdict
    goal: Goal | None = None
    reason: str = ""
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def accept(cls, goal: Goal, reason: str = "") -> RebelDecision:
        return cls(verdict=RebelVerdict.ACCEPT, goal=goal, reason=reason)

    @classmethod
    def rewrite(cls, new_goal: Goal, reason: str) -> RebelDecision:
        return cls(verdict=RebelVerdict.REWRITE, goal=new_goal, reason=reason)

    @classmethod
    def reject(cls, reason: str) -> RebelDecision:
        return cls(verdict=RebelVerdict.REJECT, goal=None, reason=reason)


@runtime_checkable
class RebelHook(Protocol):
    """Evaluate an assigned goal against agent expectations."""

    def on_goal_assignment(
        self,
        goal: Goal,
        expectations: Iterable[CognitiveExpectation],
    ) -> RebelDecision: ...


class AcceptingRebelHook:
    """Default hook that accepts every assigned goal.

    Backward-compatible default. Hosts wanting principled refusal
    inject their own ``RebelHook`` implementation.
    """

    def on_goal_assignment(
        self,
        goal: Goal,
        expectations: Iterable[CognitiveExpectation],
    ) -> RebelDecision:
        del expectations
        return RebelDecision.accept(goal, reason="default accepting hook")


__all__ = [
    "AcceptingRebelHook",
    "RebelDecision",
    "RebelHook",
    "RebelVerdict",
]
