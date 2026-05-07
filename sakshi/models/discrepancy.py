"""Discrepancy-resolution DTO.

Captures the canonical four-step pipeline that connects a detected
mismatch to a corrective action: ``symptom → explanation → goal → plan``.
The same shape applies at both the object level (a fact in the world
diverges from expectation, so the agent forms a goal to fix the world)
and the meta level (a phase output diverges from expectation, so the
agent forms a goal to fix its own cognition).

Recording the four steps as a single DTO lets a host audit the chain
end-to-end in one trace record rather than reconstruct it from
scattered emissions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from sakshi.models.anomaly import AnomalySourceType


class ResolutionLevel(StrEnum):
    """Whether a discrepancy was resolved at the object or meta level.

    Object-level discrepancies are mismatches between expected and
    observed environment state. Meta-level discrepancies are mismatches
    inside the agent's own reasoning trace (impasse, expectation
    violation on a phase output, plan deviation).
    """

    OBJECT = "object"
    META = "meta"


class DiscrepancyResolution(BaseModel):
    """End-to-end record of one symptom-to-plan resolution chain.

    The four payload fields mirror the four canonical steps. They are
    typed as ``str`` rather than richer DTOs because callers wire in
    their own world-model, explanation, goal, and plan representations
    through the existing ``GoalStateStore`` and explanation seams; this
    DTO is the join row that ties them together.
    """

    cycle_id: str
    level: ResolutionLevel
    source: AnomalySourceType = Field(
        default=AnomalySourceType.WORLD,
        description=(
            "Origin lane of the discrepancy. Object-level resolutions "
            "default to WORLD; meta-level resolutions should override "
            "to COGNITIVE; bridging cases use COMPOUND."
        ),
    )
    symptom: str = Field(
        ...,
        description="What was observed that diverged from expectation.",
    )
    explanation: str = Field(
        ...,
        description="Best causal hypothesis linking symptom to a fixable cause.",
    )
    goal_id: str | None = Field(
        default=None,
        description="ID of the goal formulated to resolve the cause, if any.",
    )
    plan_id: str | None = Field(
        default=None,
        description="ID of the plan generated to achieve the goal, if any.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence the host attaches to the explanation step.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "DiscrepancyResolution",
    "ResolutionLevel",
]
