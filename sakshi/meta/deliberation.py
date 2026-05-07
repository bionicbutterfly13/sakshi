"""Cost-aware deliberation gate.

A small, deterministic threshold function that decides whether the
host should escalate from a fast routine response (a stored heuristic,
a cached policy) to a slower deliberative path (a full meta-cycle, an
expensive planner call, an LLM consultation).

The gate is not the host's reasoning system; it answers exactly one
question: given current confidence, recent failure pressure, and
remaining budget, is the cheap path good enough? Hosts pass three
small numbers in and read one ``DeliberationDecision`` out.

Defaults are tuned so the gate stays out of the way most of the time:
high confidence and low recent failure pressure → use the cheap path;
low confidence or high failure pressure → escalate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

DEFAULT_CONFIDENCE_FLOOR = 0.6
DEFAULT_FAILURE_CEILING = 0.4
DEFAULT_BUDGET_FLOOR = 0.1


class DeliberationPath(StrEnum):
    """Two paths the gate can recommend."""

    ROUTINE = "routine"
    DELIBERATIVE = "deliberative"


@dataclass(frozen=True)
class DeliberationDecision:
    """Typed verdict returned by ``DeliberationGate.decide``."""

    path: DeliberationPath
    reason: str = ""

    @property
    def escalated(self) -> bool:
        return self.path == DeliberationPath.DELIBERATIVE


class DeliberationGate:
    """Decide between routine and deliberative paths.

    Args:
        confidence_floor: Below this self-reported confidence the gate
            recommends escalation. Default 0.6.
        failure_ceiling: Above this rolling failure rate the gate
            recommends escalation. Default 0.4.
        budget_floor: When remaining budget falls below this, the gate
            stays on the routine path even if confidence/failure
            signals would normally escalate (you can't afford the
            deliberative path; do the cheap thing). Default 0.1.
    """

    def __init__(
        self,
        *,
        confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
        failure_ceiling: float = DEFAULT_FAILURE_CEILING,
        budget_floor: float = DEFAULT_BUDGET_FLOOR,
    ) -> None:
        for label, value in (
            ("confidence_floor", confidence_floor),
            ("failure_ceiling", failure_ceiling),
            ("budget_floor", budget_floor),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be in [0, 1], got {value!r}")
        self._conf = confidence_floor
        self._fail = failure_ceiling
        self._budget = budget_floor

    def decide(
        self,
        *,
        confidence: float,
        recent_failure_rate: float,
        remaining_budget: float,
    ) -> DeliberationDecision:
        """Recommend a path given three small numbers."""
        for label, value in (
            ("confidence", confidence),
            ("recent_failure_rate", recent_failure_rate),
            ("remaining_budget", remaining_budget),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be in [0, 1], got {value!r}")

        if remaining_budget < self._budget:
            return DeliberationDecision(
                path=DeliberationPath.ROUTINE,
                reason=(
                    f"budget {remaining_budget:.2f} below floor "
                    f"{self._budget:.2f}; staying on routine path"
                ),
            )

        if confidence < self._conf:
            return DeliberationDecision(
                path=DeliberationPath.DELIBERATIVE,
                reason=(
                    f"confidence {confidence:.2f} below floor "
                    f"{self._conf:.2f}; escalating"
                ),
            )

        if recent_failure_rate > self._fail:
            return DeliberationDecision(
                path=DeliberationPath.DELIBERATIVE,
                reason=(
                    f"failure rate {recent_failure_rate:.2f} above ceiling "
                    f"{self._fail:.2f}; escalating"
                ),
            )

        return DeliberationDecision(
            path=DeliberationPath.ROUTINE,
            reason=(
                f"confidence {confidence:.2f} >= "
                f"{self._conf:.2f} and failure {recent_failure_rate:.2f} <= "
                f"{self._fail:.2f}; routine sufficient"
            ),
        )


__all__ = [
    "DEFAULT_BUDGET_FLOOR",
    "DEFAULT_CONFIDENCE_FLOOR",
    "DEFAULT_FAILURE_CEILING",
    "DeliberationDecision",
    "DeliberationGate",
    "DeliberationPath",
]
