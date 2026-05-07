"""Tiered transparency DTOs.

Hosts that surface agent reasoning to humans benefit from offering
multiple depths of disclosure: a brief status line, a deeper
reasoning trace, and a forward-looking projection. This module
defines the three-tier shape so hosts can pick the right depth for
the right consumer (operator dashboard vs. compliance audit vs. peer
agent).

The tiers are intentionally typed separately rather than threaded
through a single union; consumers usually want exactly one tier and
can subscribe to the level they need without unpacking variants.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TransparencyLevel(StrEnum):
    """The three published transparency tiers.

    ``STATUS`` is the lightest disclosure — current state and active
    goals only. ``REASONING`` adds the chain that produced the most
    recent decision: which motivator fired, which candidate
    explanations were considered, why the chosen one won. ``PROJECTION``
    adds forward-looking forecasts: expected next states, resource
    forecasts, risk estimates.
    """

    STATUS = "status"
    REASONING = "reasoning"
    PROJECTION = "projection"


class StatusTransparency(BaseModel):
    """Tier-1 disclosure: current state and active goals."""

    cycle_id: str
    current_phase: str = ""
    active_goal_ids: list[str] = Field(default_factory=list)
    pending_plan_ids: list[str] = Field(default_factory=list)
    summary: str = ""
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReasoningTransparency(BaseModel):
    """Tier-2 disclosure: the most recent decision's reasoning chain."""

    cycle_id: str
    selected_motivator: str = Field(
        default="",
        description="What drove the decision (anomaly, intrinsic goal, instruction)",
    )
    candidate_explanations: list[str] = Field(default_factory=list)
    chosen_explanation: str = ""
    choice_rationale: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectionTransparency(BaseModel):
    """Tier-3 disclosure: forecasts and risk estimates."""

    cycle_id: str
    horizon_steps: int = Field(default=1, ge=1)
    forecast_states: list[dict[str, Any]] = Field(default_factory=list)
    resource_forecast: dict[str, float] = Field(default_factory=dict)
    risk_estimates: dict[str, float] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "ProjectionTransparency",
    "ReasoningTransparency",
    "StatusTransparency",
    "TransparencyLevel",
]
