"""Plan deviation tracking.

Tracks the gap between a declared reference plan and actual execution.
Hosts that emit learning-signal events should wire their bus handler to
`PlanDeviationTracker.on_learning_signal`; the core does not subscribe
to any event bus itself.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DEVIATION_THRESHOLD = 0.3
MIN_STEPS_BEFORE_REPLAN = 3
MIN_DEVIATION_THRESHOLD = 0.1
MAX_DEVIATION_THRESHOLD = 0.5


@dataclass(frozen=True)
class DeviationRecord:
    """One actual execution step compared against the reference plan."""

    step_number: int
    expected_step: str
    actual_step: str
    deviation_score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PlanDeviationTracker:
    """Track deviations between planned and actual execution steps."""

    def __init__(
        self,
        *,
        deviation_threshold: float = DEFAULT_DEVIATION_THRESHOLD,
        min_steps_before_replan: int = MIN_STEPS_BEFORE_REPLAN,
    ) -> None:
        self._default_threshold = deviation_threshold
        self._dynamic_threshold = deviation_threshold
        self._min_steps_before_replan = min_steps_before_replan
        self._reference_steps: list[str] = []
        self._records: list[DeviationRecord] = []
        self._step_cursor = 0
        self._replan_triggered = False

    @property
    def dynamic_threshold(self) -> float:
        """Current adaptive deviation threshold."""
        return self._dynamic_threshold

    @property
    def records(self) -> list[DeviationRecord]:
        """Recorded deviations and exact-match observations."""
        return list(self._records)

    def set_reference_plan(
        self,
        steps: list[str],
        *,
        reset_threshold: bool = False,
    ) -> None:
        """Set the accepted reference plan."""
        self._reference_steps = list(steps)
        self._records = []
        self._step_cursor = 0
        self._replan_triggered = False
        if reset_threshold:
            self._dynamic_threshold = self._default_threshold

    def record_action(
        self,
        tool_name: str,
        args: Mapping[str, Any] | None = None,
    ) -> DeviationRecord | None:
        """Record an executed action and return a record only on mismatch."""
        del args
        if not self._reference_steps:
            return None

        if self._step_cursor >= len(self._reference_steps):
            record = DeviationRecord(
                step_number=self._step_cursor,
                expected_step="<end_of_plan>",
                actual_step=tool_name,
                deviation_score=1.0,
            )
            self._records.append(record)
            self._step_cursor += 1
            return record

        expected = self._reference_steps[self._step_cursor]
        score = self._compute_deviation_score(expected, tool_name)
        record = DeviationRecord(
            step_number=self._step_cursor,
            expected_step=expected,
            actual_step=tool_name,
            deviation_score=score,
        )
        self._records.append(record)
        self._step_cursor += 1

        if score > 0.0:
            logger.info(
                "PlanDeviationTracker: step %d deviated "
                "(expected=%s, actual=%s, score=%.2f)",
                record.step_number,
                expected,
                tool_name,
                score,
            )
            return record
        return None

    async def on_learning_signal(self, event: Mapping[str, Any] | object) -> None:
        """Adjust threshold from a host-wired learning signal."""
        data = _event_data(event)
        strength = data.get("strength_label", "moderate")
        if strength == "strong":
            self._dynamic_threshold = max(
                MIN_DEVIATION_THRESHOLD,
                self._dynamic_threshold * 0.9,
            )
        elif strength == "weak":
            self._dynamic_threshold = min(
                MAX_DEVIATION_THRESHOLD,
                self._dynamic_threshold * 1.05,
            )

    def get_deviation_ratio(self) -> float:
        """Return proportion of executed steps that deviated."""
        if not self._records:
            return 0.0
        deviant = sum(1 for record in self._records if record.deviation_score > 0.0)
        return deviant / len(self._records)

    def should_replan(self) -> bool:
        """True once deviation ratio exceeds threshold after enough steps."""
        if self._replan_triggered:
            return False
        if len(self._records) < self._min_steps_before_replan:
            return False
        if self.get_deviation_ratio() > self._dynamic_threshold:
            self._replan_triggered = True
            return True
        return False

    def reset(self) -> None:
        """Clear plan and observation state, preserving adaptive threshold."""
        self._reference_steps = []
        self._records = []
        self._step_cursor = 0
        self._replan_triggered = False

    def _compute_deviation_score(self, expected: str, actual: str) -> float:
        if expected == actual:
            return 0.0
        normalized_expected = expected.lower().replace("_", "").replace("-", "")
        normalized_actual = actual.lower().replace("_", "").replace("-", "")
        if normalized_expected == normalized_actual:
            return 0.0
        if normalized_expected.startswith(
            normalized_actual
        ) or normalized_actual.startswith(normalized_expected):
            return 0.3
        if (
            normalized_expected in normalized_actual
            or normalized_actual in normalized_expected
        ):
            return 0.5
        return 1.0


def _event_data(event: Mapping[str, Any] | object) -> dict[str, Any]:
    if isinstance(event, Mapping):
        return dict(event)
    data = getattr(event, "data", {})
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    return dict(data) if isinstance(data, Mapping) else {}


__all__ = [
    "DEFAULT_DEVIATION_THRESHOLD",
    "MAX_DEVIATION_THRESHOLD",
    "MIN_DEVIATION_THRESHOLD",
    "MIN_STEPS_BEFORE_REPLAN",
    "DeviationRecord",
    "PlanDeviationTracker",
]
