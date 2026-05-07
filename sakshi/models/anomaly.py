"""Anomaly escalation DTOs.

When anomalies recur on the same goal, the meta-loop escalates through
progressive response levels: observe, widen precision, mutate the goal
itself, or delegate to a human.

Anomalies are tagged with a source lane (``WORLD``, ``COGNITIVE``, or
``COMPOUND``) so calibration and explanation can be reported per-lane.
Cross-lane aggregates conflate object-level and meta-level signals and
mislead host operators.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AnomalySourceType(StrEnum):
    """Origin lane of a detected anomaly.

    ``WORLD`` anomalies are mismatches between expected and observed
    environment state and trigger world-model corrections. ``COGNITIVE``
    anomalies are mismatches inside the agent's own reasoning trace
    (impasse, expectation violation, plan deviation) and trigger
    meta-cycle adjustments. ``COMPOUND`` anomalies present in both lanes
    and are decomposed at detection, not at explanation.
    """

    WORLD = "WORLD"
    COGNITIVE = "COGNITIVE"
    COMPOUND = "COMPOUND"


EscalationLevel = Literal[
    "MONITOR",
    "WIDEN_PRECISION",
    "MUTATE_GOAL",
    "DELEGATE_HUMAN",
]


ESCALATION_THRESHOLDS: dict[str, int] = {
    "MONITOR": 0,
    "WIDEN_PRECISION": 2,
    "MUTATE_GOAL": 4,
    "DELEGATE_HUMAN": 6,
}


class AnomalyEscalation(BaseModel):
    """Tracks anomaly persistence and escalation state for a goal."""

    goal_id: str = Field(..., description="Goal experiencing repeated anomalies")
    anomaly_count: int = Field(
        ...,
        ge=0,
        description="Total anomaly occurrences for this goal",
    )
    current_level: EscalationLevel = Field(..., description="Current escalation level")
    threshold_breached: bool = Field(
        ...,
        description="Whether a new threshold was crossed this cycle",
    )
    recommended_action: str = Field(
        ..., description="Natural language recommended response"
    )
    source: AnomalySourceType = Field(
        default=AnomalySourceType.WORLD,
        description=(
            "Origin lane of the anomaly. WORLD anomalies trigger world-model "
            "corrections; COGNITIVE anomalies trigger meta-cycle adjustments; "
            "COMPOUND anomalies are decomposed before explanation."
        ),
    )

    @classmethod
    def from_count(
        cls,
        goal_id: str,
        anomaly_count: int,
        recommended_action: str = "",
        source: AnomalySourceType = AnomalySourceType.WORLD,
    ) -> AnomalyEscalation:
        """Determine escalation level from anomaly count.

        Args:
            goal_id: The goal being tracked.
            anomaly_count: Current count of anomalies.
            recommended_action: Optional action description.
            source: Origin lane of the anomaly stream. Defaults to
                ``WORLD`` for backward compatibility with callers that
                were emitting environment anomalies before the lane
                taxonomy existed.

        Returns:
            An `AnomalyEscalation` with computed level and breach flag.
        """
        level: EscalationLevel = "MONITOR"
        breached = False

        for lvl_name in ("DELEGATE_HUMAN", "MUTATE_GOAL", "WIDEN_PRECISION"):
            threshold = ESCALATION_THRESHOLDS[lvl_name]
            if anomaly_count >= threshold:
                level = lvl_name  # type: ignore[assignment]
                breached = anomaly_count == threshold
                break

        return cls(
            goal_id=goal_id,
            anomaly_count=anomaly_count,
            current_level=level,
            threshold_breached=breached,
            recommended_action=recommended_action,
            source=source,
        )

    @property
    def requires_human(self) -> bool:
        """Whether this escalation requires human intervention."""
        return self.current_level == "DELEGATE_HUMAN"


__all__ = [
    "AnomalyEscalation",
    "AnomalySourceType",
    "ESCALATION_THRESHOLDS",
    "EscalationLevel",
]
