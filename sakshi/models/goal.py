"""Goal DTOs.

Hierarchical goal structures with predicate representation, lifecycle
status, plans, and outcome records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    """Goal lifecycle status."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    DELEGATED = "delegated"


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
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


__all__ = [
    "Goal",
    "GoalOutcomeRecord",
    "GoalPlan",
    "GoalPredicate",
    "GoalStatus",
]
