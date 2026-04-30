"""Anomaly-to-goal generation.

Converts anomaly events and canalization reports into structured goals.
The generator can optionally validate and insert into an injected
`GoalGraph`, but it never subscribes to a host bus or writes host memory.
Adapters own those side effects.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sakshi.goals.explainer import AnomalyExplanation, find_most_shifted_key
from sakshi.goals.graph import GoalGraph
from sakshi.goals.validator import GoalValidator
from sakshi.interpret.a_distance import AnomalyEvent
from sakshi.models import Goal, GoalPredicate

logger = logging.getLogger(__name__)

DEFAULT_CANALIZATION_DEDUP_SECONDS = 300


class GoalGenerator:
    """Convert anomaly-shaped inputs into actionable goals."""

    def __init__(
        self,
        *,
        validator: GoalValidator | None = None,
        graph: GoalGraph | None = None,
        canalization_dedup_seconds: int = DEFAULT_CANALIZATION_DEDUP_SECONDS,
    ) -> None:
        self._validator = validator
        self._graph = graph
        self._generated_count = 0
        self._canalization_dedup_window = timedelta(seconds=canalization_dedup_seconds)
        self._recent_canalization_patterns: dict[str, datetime] = {}

    async def generate_from_anomaly(
        self,
        anomaly_event: AnomalyEvent | object,
        *,
        explanation: AnomalyExplanation | None = None,
        add_to_graph: bool = False,
    ) -> Goal | None:
        """Generate a goal from a statistical anomaly event."""
        if anomaly_event is None:
            return None

        self._generated_count += 1
        goal = Goal(
            id=f"anomaly-goal-{self._generated_count:04d}",
            predicate=GoalPredicate(
                name="INVESTIGATE_ANOMALY",
                args=self._anomaly_predicate_args(anomaly_event, explanation),
            ),
            priority=severity_to_priority(
                str(getattr(anomaly_event, "severity", "LOW"))
            ),
            source="anomaly_goal_generator",
            prior_type="λ",
            description=explanation.hypothesis if explanation is not None else "",
        )
        return self._finalize(goal, add_to_graph=add_to_graph)

    async def generate_from_canalization_event(
        self,
        event_data: Mapping[str, Any],
        *,
        add_to_graph: bool = False,
    ) -> Goal | None:
        """Generate a goal from a canalization-detection payload."""
        if event_data.get("anomaly_type") != "CANALIZATION_DETECTED":
            return None

        pattern = str(event_data.get("pattern", "unknown"))
        basin_id = str(event_data.get("basin_id", ""))
        dedup_key = hashlib.md5(f"{pattern}:{basin_id}".encode()).hexdigest()
        now = datetime.now(UTC)

        last_seen = self._recent_canalization_patterns.get(dedup_key)
        if last_seen is not None and now - last_seen < self._canalization_dedup_window:
            logger.debug("GoalGenerator: canalization dedup hit for %s", pattern)
            return None

        self._generated_count += 1
        goal = Goal(
            id=f"canalization-goal-{self._generated_count:04d}",
            predicate=GoalPredicate(
                name="CANALIZATION_BREAK",
                args={
                    "pattern": pattern,
                    "basin_id": basin_id,
                    "severity": event_data.get("severity", 0.5),
                },
            ),
            priority=3,
            source="canalization_detector",
            prior_type="D",
            description=f"Break canalization: {pattern}",
        )
        finalized = self._finalize(goal, add_to_graph=add_to_graph)
        if finalized is not None:
            self._recent_canalization_patterns[dedup_key] = now
        return finalized

    async def mutate_goal(
        self,
        goal_id: str,
        anomaly_count: int,
        *,
        add_to_graph: bool = False,
    ) -> Goal | None:
        """Generate a widened investigation goal for persistent anomalies."""
        self._generated_count += 1
        goal = Goal(
            id=f"mutated-goal-{self._generated_count:04d}",
            predicate=GoalPredicate(
                name="INVESTIGATE_ANOMALY_WIDENED",
                args={
                    "original_goal_id": goal_id,
                    "anomaly_count": anomaly_count,
                    "relaxed_tolerance": True,
                    "widen_search_scope": True,
                },
            ),
            priority=1,
            source="anomaly_escalation",
            prior_type="λ",
            description=(
                f"Widened investigation for goal {goal_id} after "
                f"{anomaly_count} consecutive anomalies."
            ),
        )
        return self._finalize(goal, add_to_graph=add_to_graph)

    def _finalize(self, goal: Goal, *, add_to_graph: bool) -> Goal | None:
        if self._validator is not None:
            validation = self._validator.validate(goal)
            if not validation.is_valid:
                logger.warning(
                    "GoalGenerator: rejected generated goal %s: %s",
                    goal.id,
                    validation.reason,
                )
                return None

        if add_to_graph:
            if self._graph is None:
                raise ValueError("add_to_graph=True requires a GoalGraph")
            self._graph.add_goal(goal)

        logger.info("GoalGenerator: generated goal %s", goal.id)
        return goal

    def _anomaly_predicate_args(
        self,
        anomaly_event: object,
        explanation: AnomalyExplanation | None,
    ) -> dict[str, Any]:
        current = getattr(anomaly_event, "current_activations", {}) or {}
        baseline = getattr(anomaly_event, "baseline_mean", {}) or {}
        args: dict[str, Any] = {
            "a_distance": getattr(anomaly_event, "a_distance", 0.0),
            "severity": getattr(anomaly_event, "severity", "LOW"),
            "basin": find_most_shifted_key(current, baseline),
        }
        if explanation is not None:
            args.update(
                {
                    "recurrence_count": explanation.recurrence_count,
                    "prior_resolution": explanation.prior_resolution,
                    "explanation_confidence": explanation.confidence,
                }
            )
        return args


def severity_to_priority(severity: str) -> int:
    """Map anomaly severity label to goal priority."""
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(severity.upper(), 1)


__all__ = [
    "DEFAULT_CANALIZATION_DEDUP_SECONDS",
    "GoalGenerator",
    "severity_to_priority",
]
