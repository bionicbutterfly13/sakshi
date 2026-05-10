"""Explanation generation for Goal-Driven Autonomy (GDA).

Implements the XPLAIN-style logic where anomalies (e.g., unexpected observations)
are resolved into causal hypotheses, which are then used to formulate new goals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sakshi.models import AnomalyType, Goal
from sakshi.models.goal import GoalPredicate

logger = logging.getLogger(__name__)


@dataclass
class ExplanationHypothesis:
    """A causal hypothesis explaining an anomaly."""

    anomaly_type: AnomalyType
    description: str
    confidence: float
    suggested_goal_predicate: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ExplanationEngine:
    """Generates explanations for anomalies to drive GDA.

    In a fully realized GDA system, this would use abductive logic or
    a library of causal rules to explain why 'expected != observed'.
    """

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def explain_anomaly(
        self, anomaly_type: AnomalyType, context: dict[str, Any]
    ) -> ExplanationHypothesis | None:
        """Attempt to explain an anomaly and return a hypothesis."""

        # In a real GDA implementation (like MIDCA's XPLAIN), this would search
        # a knowledge base for causal linkages. For Sakshi, we provide a scaffold.

        if anomaly_type == AnomalyType.CANALIZATION_DETECTED:
            return ExplanationHypothesis(
                anomaly_type=anomaly_type,
                description=(
                    "Agent is caught in a local minimum and repeating "
                    "actions without world state change."
                ),
                confidence=0.9,
                suggested_goal_predicate="break_canalization",
            )

        if anomaly_type == AnomalyType.BASIN_SHIFT:
            return ExplanationHypothesis(
                anomaly_type=anomaly_type,
                description=(
                    "The environmental basin shifted unexpectedly, "
                    "likely due to an exogenous event."
                ),
                confidence=0.7,
                suggested_goal_predicate="stabilize_basin",
            )

        logger.info("No explanation found for anomaly: %s", anomaly_type)
        return None

    def formulate_goal_from_hypothesis(
        self, hypothesis: ExplanationHypothesis
    ) -> Goal | None:
        """Formulate a new goal to resolve the root cause in the explanation."""
        if not hypothesis.suggested_goal_predicate:
            return None

        return Goal(
            id=f"gda-{hypothesis.suggested_goal_predicate}-{int(datetime.now(UTC).timestamp())}",
            predicate=GoalPredicate(name=hypothesis.suggested_goal_predicate),
            basin_name="metacognitive_repair",
            priority=3,
        )


__all__ = ["ExplanationEngine", "ExplanationHypothesis"]
