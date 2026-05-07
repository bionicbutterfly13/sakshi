"""Goal-operation taxonomy.

Goal reasoning is conventionally modelled as a sequence of typed
operations applied to goals over time. Sakshi exposes that taxonomy as
the ``GoalOperation`` enum together with ``GoalOperationEvent`` so hosts
can subscribe to a single high-level stream describing what their agent
is doing to its goals (formulating, selecting, dispatching, repairing,
deferring, etc.) rather than reconstructing the lifecycle from
scattered method calls.

The names align with the broader literature on goal-reasoning
lifecycles; ``apply``, ``hold``, and ``release`` are explicit additions
for hosts that delegate goals to other agents and need to mark the
control transfer separately from achievement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GoalOperation(StrEnum):
    """A typed verb describing what just happened to a goal.

    The first nine entries form the canonical goal-reasoning lifecycle
    (formulate, select, expand, commit, dispatch, monitor, evaluate,
    repair, defer). ``DELEGATE`` and ``RESUME`` cover handoff and
    deferred-goal restart, which the canonical lifecycle does not name
    explicitly.
    """

    FORMULATE = "formulate"
    SELECT = "select"
    EXPAND = "expand"
    COMMIT = "commit"
    DISPATCH = "dispatch"
    MONITOR = "monitor"
    EVALUATE = "evaluate"
    REPAIR = "repair"
    DEFER = "defer"
    DELEGATE = "delegate"
    RESUME = "resume"


class GoalOperationEvent(BaseModel):
    """An emitted record of a single goal operation.

    Hosts subscribe to ``goal.op`` events on the configured ``EventBus``
    to receive these. The package itself never publishes directly; it
    constructs the DTO and hands it to whichever bus the host injected.
    """

    operation: GoalOperation
    goal_id: str
    cycle_id: str | None = None
    cause: str = Field(
        default="",
        description="Short human-readable reason for the operation",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


GOAL_OPERATION_EVENT_TYPE = "sakshi.goal.op"
"""Default event-type string for goal-operation publication."""


__all__ = [
    "GOAL_OPERATION_EVENT_TYPE",
    "GoalOperation",
    "GoalOperationEvent",
]
