"""Anomaly persistence tracking."""

from __future__ import annotations

import logging

from sakshi.models.anomaly import AnomalyEscalation

logger = logging.getLogger(__name__)


class AnomalyPersistenceTracker:
    """Track consecutive anomaly counts per goal and compute escalation."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def record_anomaly(self, goal_id: str) -> AnomalyEscalation:
        """Increment anomaly count for a goal and return escalation state."""
        self._counts[goal_id] = self._counts.get(goal_id, 0) + 1
        escalation = AnomalyEscalation.from_count(
            goal_id,
            self._counts[goal_id],
        )
        logger.debug(
            "anomaly persistence goal=%s count=%d level=%s breached=%s",
            goal_id,
            self._counts[goal_id],
            escalation.current_level,
            escalation.threshold_breached,
        )
        return escalation

    def record_success(self, goal_id: str) -> None:
        """Reset a goal's anomaly streak after a successful cycle."""
        self._counts.pop(goal_id, None)

    def get_escalation(self, goal_id: str) -> AnomalyEscalation:
        """Return current escalation for a goal without changing state."""
        return AnomalyEscalation.from_count(goal_id, self._counts.get(goal_id, 0))
