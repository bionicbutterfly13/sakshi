"""Execution DTOs for goal closure.

These models describe the small action-result shape Sakshi needs to
classify goal outcomes. Host applications translate their richer
runtime summaries into these DTOs at the adapter boundary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionExecutionStatus(StrEnum):
    """Execution status for one planned action."""

    COMPLETED = "completed"
    FAILED = "failed"
    DEFERRED = "deferred"


class ActionExecutionResult(BaseModel):
    """Result of one action execution."""

    status: ActionExecutionStatus
    action_type: str = ""
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class GoalExecutionSummary(BaseModel):
    """Execution summary for a focused goal."""

    focus_goal_id: str | None = None
    action_results: list[ActionExecutionResult] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    cycle_id: str | None = None


__all__ = [
    "ActionExecutionResult",
    "ActionExecutionStatus",
    "GoalExecutionSummary",
]
