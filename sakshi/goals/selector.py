"""Goal selection.

Ranks candidate goals by a simple performance / limiting-factor score,
with small modifiers for maintenance and avoidance goals.
"""

from __future__ import annotations

import logging

from sakshi.models import Goal

logger = logging.getLogger(__name__)

PRIORITY_SCALE = 3.0


class ModSelectionCriteria:
    """Compute a bounded selection score for one goal."""

    _MAINTENANCE_BOOST = 1.2
    _MAINTENANCE_THRESHOLD = 0.7
    _AVOIDANCE_BOOST = 1.1

    def score(self, goal: Goal, performance: float, limiting_factor: float) -> float:
        """Compute `performance / limiting_factor`, capped to `[0.0, 1.0]`."""
        if limiting_factor <= 0.0:
            return 0.0

        base = performance / limiting_factor

        if (
            goal.goal_type == "maintenance"
            and performance > self._MAINTENANCE_THRESHOLD
        ):
            base *= self._MAINTENANCE_BOOST
        elif goal.goal_type == "avoidance":
            base *= self._AVOIDANCE_BOOST

        return min(max(base, 0.0), 1.0)


class GoalSelector:
    """Rank goals by `ModSelectionCriteria` score."""

    def __init__(self, criteria: ModSelectionCriteria | None = None) -> None:
        self._criteria = criteria or ModSelectionCriteria()

    def select(
        self,
        goals: list[Goal],
        performance_map: dict[str, float] | None = None,
        limiting_factor_map: dict[str, float] | None = None,
    ) -> list[Goal]:
        """Return goals ordered highest selection score first."""
        if not goals:
            return []

        performance_map = performance_map or {}
        limiting_factor_map = limiting_factor_map or {}

        scored: list[tuple[float, Goal]] = []
        for goal in goals:
            performance = performance_map.get(goal.id, goal.priority / PRIORITY_SCALE)
            limiting_factor = limiting_factor_map.get(goal.id, 1.0)
            score = self._criteria.score(goal, performance, limiting_factor)
            scored.append((score, goal))
            logger.debug(
                "GoalSelector: goal %s score=%.4f (perf=%.3f, lf=%.3f, type=%s)",
                goal.id,
                score,
                performance,
                limiting_factor,
                goal.goal_type,
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [goal for _, goal in scored]


__all__ = ["GoalSelector", "ModSelectionCriteria", "PRIORITY_SCALE"]
