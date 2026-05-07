"""Goal DTOs.

Hierarchical goal structures with predicate representation, lifecycle
status, plans, and outcome records.

``GoalStatus`` and ``GoalMode`` are intentionally orthogonal. ``GoalStatus``
records the *terminal* state of a goal (active, achieved, abandoned,
blocked, delegated). ``GoalMode`` records the *current lifecycle phase*
within an active goal (formulating, dispatched, monitoring, repairing,
deferred). Both coexist on every goal so callers can ask
"is this goal still in play?" (status) separately from
"what is the goal currently doing?" (mode).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class GoalStatus(StrEnum):
    """Goal lifecycle status (terminal-state axis)."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    DELEGATED = "delegated"


class GoalMode(StrEnum):
    """Active-phase axis for a goal in flight.

    Mirrors the goal-lifecycle-network state machine: a goal is
    formulated, then selected and dispatched into execution, then
    monitored, then either repaired or deferred when monitoring finds
    trouble. ``COMPLETED`` is a terminal mode independent of whether
    ``GoalStatus`` recorded the close as ``ACHIEVED`` or ``ABANDONED``.
    """

    FORMULATING = "formulating"
    SELECTED = "selected"
    DISPATCHED = "dispatched"
    MONITORING = "monitoring"
    REPAIRING = "repairing"
    DEFERRED = "deferred"
    COMPLETED = "completed"


class GoalEventType(StrEnum):
    """Causes of a transition recorded on a goal's event history."""

    FORMULATED = "formulated"
    SELECTED = "selected"
    DISPATCHED = "dispatched"
    MONITOR_OK = "monitor_ok"
    MONITOR_VIOLATION = "monitor_violation"
    REPAIR_STARTED = "repair_started"
    REPAIR_COMPLETED = "repair_completed"
    DEFERRED = "deferred"
    RESUMED = "resumed"
    COMPLETED = "completed"


class GoalEvent(BaseModel):
    """One transition record in a goal's lifecycle history."""

    event_type: GoalEventType
    from_mode: GoalMode | None = None
    to_mode: GoalMode | None = None
    cause: str = Field(
        default="",
        description="Short human-readable reason for the transition",
    )
    cycle_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GoalPredicate(BaseModel):
    """Predicate representation for a goal state.

    Example: ``GoalPredicate(name="ON", args={"object": "A", "surface": "table"})``.
    Inspired by MIDCA-style predicate-based world models.
    """

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    domain: str | None = None
    expected_state: dict[str, Any] | None = None

    def __str__(self) -> str:
        if not self.args:
            return self.name
        args_str = ", ".join(f"{k}={v}" for k, v in self.args.items())
        return f"{self.name}({args_str})"


class Goal(BaseModel):
    """A single goal in the goal graph."""

    id: str
    predicate: GoalPredicate
    basin_name: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    mode: GoalMode = GoalMode.FORMULATING
    transitions: list[GoalEvent] = Field(default_factory=list)
    priority: int = 1
    prior_type: str = "λ"
    source: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    goal_type: Literal["achievement", "maintenance", "avoidance"] = "achievement"

    prior_preference_vector: list[float] | None = None
    expected_efe: float | None = None

    def is_terminal(self) -> bool:
        """True if the goal is no longer in active consideration."""
        return self.status in (
            GoalStatus.ACHIEVED,
            GoalStatus.ABANDONED,
            GoalStatus.DELEGATED,
        )

    def record_transition(
        self,
        *,
        event_type: GoalEventType,
        to_mode: GoalMode | None = None,
        cause: str = "",
        cycle_id: str | None = None,
    ) -> GoalEvent:
        """Append a lifecycle transition event and update ``mode``.

        Returns the recorded event so callers can attach it to a trace
        or emit it on the host event bus.
        """
        from_mode = self.mode
        if to_mode is not None:
            self.mode = to_mode
        event = GoalEvent(
            event_type=event_type,
            from_mode=from_mode,
            to_mode=to_mode,
            cause=cause,
            cycle_id=cycle_id,
        )
        self.transitions.append(event)
        return event


class GoalPlan(BaseModel):
    """A plan associated with a goal (sequence of steps to achieve it)."""

    goal_id: str
    steps: list[str] = Field(default_factory=list)
    estimated_cycles: int = 1
    confidence: float = 0.5


class GoalOutcomeRecord(BaseModel):
    """Structured runtime outcome record for a goal closure."""

    goal_id: str
    instruction_id: str | None = None
    cycle_id: str | None = None
    predicate_name: str = ""
    outcome_status: GoalStatus
    reason: str = ""
    delegate_to: str | None = None
    action_statuses: list[str] = Field(default_factory=list)
    action_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    deferred_count: int = 0
    plan_steps: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "Goal",
    "GoalEvent",
    "GoalEventType",
    "GoalMode",
    "GoalOutcomeRecord",
    "GoalPlan",
    "GoalPredicate",
    "GoalStatus",
]
