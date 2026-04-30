"""Goal validity monitoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sakshi.goals.outcome_memory import GoalOutcomeMemory
from sakshi.models import Goal, GoalStatus, WorldStateSnapshot
from sakshi.protocols import GoalStateStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoalMonitorResult:
    """Result of a goal validity check."""

    goal_id: str
    is_valid: bool
    reason: str


class GoalMonitor:
    """Check whether a goal is still meaningful to pursue."""

    def __init__(
        self,
        *,
        futile_abandonment_threshold: float = 0.6,
        minimum_history_records: int = 3,
        efe_completion_threshold: float = 0.1,
    ) -> None:
        self._futile_abandonment_threshold = futile_abandonment_threshold
        self._minimum_history_records = minimum_history_records
        self._efe_completion_threshold = efe_completion_threshold

    def check_validity(
        self,
        goal: Goal,
        world_state: WorldStateSnapshot,
    ) -> GoalMonitorResult:
        """Check whether pursuing this goal is still meaningful."""
        if (
            goal.expected_efe is not None
            and goal.expected_efe < self._efe_completion_threshold
            and goal.goal_type == "achievement"
        ):
            return GoalMonitorResult(
                goal_id=goal.id,
                is_valid=False,
                reason="already_satisfied",
            )

        predicate_name = goal.predicate.name
        predicate_present = world_state.contains(predicate_name)

        if goal.goal_type == "achievement" and predicate_present:
            return GoalMonitorResult(
                goal_id=goal.id,
                is_valid=False,
                reason="already_satisfied",
            )

        if goal.goal_type in {"maintenance", "avoidance"} and not predicate_present:
            return GoalMonitorResult(
                goal_id=goal.id,
                is_valid=False,
                reason="no_longer_relevant",
            )

        return GoalMonitorResult(goal_id=goal.id, is_valid=True, reason="valid")

    def check_outcome_history(
        self,
        goal: Goal,
        outcome_memory: GoalOutcomeMemory,
    ) -> GoalMonitorResult | None:
        """Return historically-futile result when structured outcomes warrant it."""
        instruction_id = goal.metadata.get("instruction_id")
        if instruction_id:
            lineage_records = outcome_memory.list_records(instruction_id=instruction_id)
            if lineage_records:
                return self._records_to_result(goal, lineage_records)

        predicate_records = outcome_memory.list_records(
            predicate_name=goal.predicate.name
        )
        if predicate_records:
            return self._records_to_result(goal, predicate_records)
        return None

    async def check_validity_with_store(
        self,
        goal: Goal,
        world_state: WorldStateSnapshot,
        store: GoalStateStore,
        *,
        valid_at: datetime | None = None,
    ) -> GoalMonitorResult:
        """Check validity and confirm against host world-state store.

        The store receives an opaque query. Hosts decide how to interpret
        `predicate_name` and `valid_at`. If the store raises, this method
        returns the in-memory result so host-store outages do not block
        metacognitive flow.
        """
        base_result = self.check_validity(goal, world_state)
        if not base_result.is_valid:
            return base_result

        try:
            stored_state = await store.fetch_world_state(
                {
                    "predicate_name": goal.predicate.name,
                    "valid_at": valid_at or datetime.now(UTC),
                }
            )
        except Exception as exc:
            logger.warning("GoalMonitor: state-store check failed: %s", exc)
            return base_result

        if not stored_state.contains(goal.predicate.name):
            return GoalMonitorResult(
                goal_id=goal.id,
                is_valid=False,
                reason="no_longer_relevant",
            )
        return base_result

    def _records_to_result(
        self,
        goal: Goal,
        records: list,
    ) -> GoalMonitorResult | None:
        total = len(records)
        if total < self._minimum_history_records:
            return None
        abandoned_count = sum(
            1 for record in records if record.outcome_status == GoalStatus.ABANDONED
        )
        if abandoned_count / total > self._futile_abandonment_threshold:
            return GoalMonitorResult(
                goal_id=goal.id,
                is_valid=False,
                reason="historically_futile",
            )
        return None


__all__ = ["GoalMonitor", "GoalMonitorResult"]
