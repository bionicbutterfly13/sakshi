"""In-memory goal outcome store."""

from __future__ import annotations

from sakshi.models import GoalOutcomeRecord, GoalStatus


class GoalOutcomeMemory:
    """Small in-memory store for structured goal outcome records."""

    def __init__(self) -> None:
        self._records: list[GoalOutcomeRecord] = []

    def record(self, outcome: GoalOutcomeRecord) -> GoalOutcomeRecord:
        """Store and return a goal outcome record."""
        self._records.append(outcome)
        return outcome

    def list_records(
        self,
        *,
        goal_id: str | None = None,
        instruction_id: str | None = None,
        predicate_name: str | None = None,
        outcome_status: GoalStatus | None = None,
    ) -> list[GoalOutcomeRecord]:
        """Return records matching all provided filters."""
        records = list(self._records)
        if goal_id is not None:
            records = [record for record in records if record.goal_id == goal_id]
        if instruction_id is not None:
            records = [
                record for record in records if record.instruction_id == instruction_id
            ]
        if predicate_name is not None:
            records = [
                record for record in records if record.predicate_name == predicate_name
            ]
        if outcome_status is not None:
            records = [
                record for record in records if record.outcome_status == outcome_status
            ]
        return records

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()


__all__ = ["GoalOutcomeMemory"]
