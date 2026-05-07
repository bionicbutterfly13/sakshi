"""In-memory goal outcome store.

The outcome memory is a typed log of past goal closures; it does not
learn anything on its own. Hosts that want strategy-level
post-mortems use ``recent`` and ``find_similar`` to pull the slices
they need without running through the full filter API.
"""

from __future__ import annotations

from collections.abc import Iterable

from sakshi.models import GoalOutcomeRecord, GoalStatus


class GoalOutcomeMemory:
    """Small in-memory store for structured goal outcome records."""

    def __init__(self) -> None:
        self._records: list[GoalOutcomeRecord] = []

    def record(self, outcome: GoalOutcomeRecord) -> GoalOutcomeRecord:
        """Store and return a goal outcome record."""
        self._records.append(outcome)
        return outcome

    def __len__(self) -> int:
        return len(self._records)

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

    def recent(self, n: int = 10) -> list[GoalOutcomeRecord]:
        """Return the most recent ``n`` records (newest first).

        Order is by record insertion; callers that need a different
        sort key can post-process the result.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return []
        return list(reversed(self._records[-n:]))

    def find_similar(
        self,
        *,
        predicate_name: str,
        outcome_status: GoalStatus | None = None,
        limit: int = 10,
    ) -> list[GoalOutcomeRecord]:
        """Return up to ``limit`` recent records sharing a predicate name.

        Filters by ``predicate_name`` and optionally ``outcome_status``,
        returns the most recent matches first. Useful for "have we
        tried something like this before" checks before issuing an
        identical goal.
        """
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        results: list[GoalOutcomeRecord] = []
        for record in reversed(self._records):
            if record.predicate_name != predicate_name:
                continue
            if outcome_status is not None and record.outcome_status != outcome_status:
                continue
            results.append(record)
            if len(results) >= limit:
                break
        return results

    def hit_rate(
        self,
        *,
        predicate_name: str | None = None,
    ) -> float:
        """Return the fraction of recorded records that achieved their goal.

        Optionally narrowed to one predicate name. Returns 0.0 when
        the matching set is empty.
        """
        records: Iterable[GoalOutcomeRecord]
        if predicate_name is None:
            records = self._records
        else:
            records = [r for r in self._records if r.predicate_name == predicate_name]
        records = list(records)
        if not records:
            return 0.0
        achieved = sum(1 for r in records if r.outcome_status == GoalStatus.ACHIEVED)
        return achieved / len(records)

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()


__all__ = ["GoalOutcomeMemory"]
