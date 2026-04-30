"""Goal outcome closure.

Classifies execution summaries, mutates an injected `GoalGraph`, and
records structured outcomes. Legacy goal-service synchronization and
host summary mutation belong in adapters.
"""

from __future__ import annotations

from sakshi.goals.graph import GoalGraph
from sakshi.goals.outcome_memory import GoalOutcomeMemory
from sakshi.models import (
    ActionExecutionStatus,
    GoalExecutionSummary,
    GoalOutcomeRecord,
    GoalStatus,
)


class GoalOutcomeClosureService:
    """Derive and apply goal closure from execution outcomes."""

    def __init__(
        self,
        *,
        graph: GoalGraph,
        outcome_memory: GoalOutcomeMemory,
    ) -> None:
        self._graph = graph
        self._outcome_memory = outcome_memory

    async def close_from_summary(
        self,
        summary: GoalExecutionSummary,
    ) -> list[GoalOutcomeRecord]:
        """Classify a focused goal's execution outcome and record it."""
        if summary.focus_goal_id is None:
            return []

        node = self._graph.get_node(summary.focus_goal_id)
        outcome = self._classify_outcome(summary)
        if outcome is None:
            return []

        delegate_to = self._delegate_target(summary)
        reason = self._reason(summary, outcome)

        if outcome == GoalStatus.ACHIEVED:
            self._graph.mark_achieved(summary.focus_goal_id)
        elif outcome == GoalStatus.ABANDONED:
            self._graph.mark_abandoned(summary.focus_goal_id)
        elif outcome == GoalStatus.DELEGATED:
            self._graph.delegate_goal(
                summary.focus_goal_id,
                delegate_to or "external",
            )

        record = GoalOutcomeRecord(
            goal_id=summary.focus_goal_id,
            instruction_id=node.goal.metadata.get("instruction_id"),
            cycle_id=summary.cycle_id,
            predicate_name=node.goal.predicate.name if node.goal.predicate else "",
            outcome_status=outcome,
            reason=reason,
            delegate_to=delegate_to,
            action_statuses=[result.status.value for result in summary.action_results],
            action_count=len(summary.action_results),
            completed_count=sum(
                1
                for result in summary.action_results
                if result.status == ActionExecutionStatus.COMPLETED
            ),
            failed_count=sum(
                1
                for result in summary.action_results
                if result.status == ActionExecutionStatus.FAILED
            ),
            deferred_count=sum(
                1
                for result in summary.action_results
                if result.status == ActionExecutionStatus.DEFERRED
            ),
            plan_steps=list(summary.plan_steps),
        )
        node.goal.metadata["last_outcome"] = record.model_dump(mode="json")
        self._outcome_memory.record(record)
        return [record]

    def _classify_outcome(
        self,
        summary: GoalExecutionSummary,
    ) -> GoalStatus | None:
        statuses = [result.status for result in summary.action_results]
        if any(status == ActionExecutionStatus.DEFERRED for status in statuses):
            return GoalStatus.DELEGATED
        if statuses and all(
            status == ActionExecutionStatus.COMPLETED for status in statuses
        ):
            return GoalStatus.ACHIEVED
        if (
            statuses
            and any(status == ActionExecutionStatus.FAILED for status in statuses)
            and not any(
                status == ActionExecutionStatus.COMPLETED for status in statuses
            )
        ):
            return GoalStatus.ABANDONED
        return None

    def _delegate_target(self, summary: GoalExecutionSummary) -> str | None:
        for result in summary.action_results:
            if result.status != ActionExecutionStatus.DEFERRED:
                continue
            delegate_to = result.data.get("delegate_to")
            if delegate_to:
                return str(delegate_to)
        return None

    def _reason(
        self,
        summary: GoalExecutionSummary,
        outcome: GoalStatus,
    ) -> str:
        if outcome == GoalStatus.DELEGATED:
            return "runtime_deferred_for_external_execution"
        if outcome == GoalStatus.ABANDONED:
            errors = [result.error for result in summary.action_results if result.error]
            return errors[0] if errors else "runtime_execution_failed"
        return "runtime_actions_completed"


__all__ = ["GoalOutcomeClosureService"]
