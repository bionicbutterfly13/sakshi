"""Intervention validation.

Every metacognitive control action (``SUPPRESS_MODULE``,
``ADJUST_PRECISION``, ``SWAP_MODULE``, ``STRENGTHEN_MODULE``,
``REPLACE_MODULE``) goes through an ``InterventionExecutor`` before it
fires. The executor decides whether the intervention is permissible
given current system state and recent history, recording every
decision in a typed audit trail.

Three permission checks compose:

1. **Permissible-given-state** — does the host's current state
   classify the intervention as allowed at all?
2. **Recently-tried** — has the same intervention been emitted within
   the configured cooldown window?
3. **Recent-outcome** — did the previous attempt succeed, fail, or
   produce no change? (Hosts pass outcomes back via
   ``record_outcome``; the executor uses them as a hint.)

Hosts plug their own permission policy through the
``InterventionPermissionPolicy`` protocol. The default policy permits
everything once cooldown has elapsed — useful for tests and trivial
hosts; production deployments should supply a policy that consults
their own safety state.
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable

from sakshi.models.cycle import ControlAction, ControlActionType

logger = logging.getLogger(__name__)


DEFAULT_COOLDOWN_SECONDS = 30.0
DEFAULT_HISTORY_SIZE = 100


class InterventionDecision(StrEnum):
    """Outcome of running ``InterventionExecutor.validate``."""

    PERMIT = "permit"
    DENY_POLICY = "deny_policy"
    DENY_COOLDOWN = "deny_cooldown"


class InterventionOutcome(StrEnum):
    """Reportable outcome after an intervention has run."""

    SUCCESS = "success"
    FAILURE = "failure"
    NO_CHANGE = "no_change"
    UNKNOWN = "unknown"


class InterventionType(StrEnum):
    """Pattern-level label for what kind of intervention is happening.

    Independent of the mechanism-level ``ControlActionType`` (which
    answers "what action did the meta-cycle emit"). The pattern
    label answers "what was the meta-cycle trying to accomplish."
    A single ``ADJUST_PRECISION`` action can implement
    ``DROP_CONFIDENCE`` or ``WIDEN_SEARCH`` depending on the precision
    delta sign; the pattern label makes that intent explicit in audit
    records.
    """

    PAUSE_AND_REEVALUATE = "pause_and_reevaluate"
    DROP_CONFIDENCE = "drop_confidence"
    WIDEN_SEARCH = "widen_search"
    RELAX_GOAL = "relax_goal"
    FLUSH_MEMORY = "flush_memory"
    TRIGGER_EXPLORATION = "trigger_exploration"
    SUSPEND_RECOVERY = "suspend_recovery"
    ESCALATE_TO_OPERATOR = "escalate_to_operator"


@dataclass(frozen=True)
class InterventionRecord:
    """One entry in the executor's audit trail."""

    action_type: ControlActionType
    target: str
    decision: InterventionDecision
    reason: str = ""
    outcome: InterventionOutcome = InterventionOutcome.UNKNOWN
    pattern: InterventionType | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class InterventionPermissionPolicy(Protocol):
    """Host-supplied policy: is this intervention permissible right now?"""

    def is_permitted(
        self,
        action: ControlAction,
        history: Iterable[InterventionRecord],
    ) -> tuple[bool, str]: ...


class AlwaysPermitPolicy:
    """Default policy that permits every intervention.

    Test- and trivial-host-friendly. Production deployments should
    provide a policy that consults their own safety state.
    """

    def is_permitted(
        self,
        action: ControlAction,
        history: Iterable[InterventionRecord],
    ) -> tuple[bool, str]:
        del action, history
        return True, "default policy: permit"


class InterventionExecutor:
    """Gate every meta-cycle intervention through typed validation.

    Args:
        policy: Host-supplied permission policy. Defaults to
            ``AlwaysPermitPolicy``.
        cooldown_seconds: Minimum elapsed seconds between two
            interventions of the same ``(action_type, target)`` pair.
        history_size: Bounded ring buffer of past records.
    """

    def __init__(
        self,
        *,
        policy: InterventionPermissionPolicy | None = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        history_size: int = DEFAULT_HISTORY_SIZE,
    ) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        if history_size < 1:
            raise ValueError("history_size must be at least 1")
        self._policy = policy or AlwaysPermitPolicy()
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._history: deque[InterventionRecord] = deque(maxlen=history_size)

    @property
    def history(self) -> tuple[InterventionRecord, ...]:
        """Snapshot of recent intervention records (oldest first)."""
        return tuple(self._history)

    def validate(
        self,
        action: ControlAction,
        *,
        pattern: InterventionType | None = None,
        now: datetime | None = None,
    ) -> InterventionRecord:
        """Decide whether to permit ``action`` and append a record.

        ``pattern`` is the optional pattern-level label describing what
        the meta-cycle was trying to accomplish (independent of the
        mechanism-level ``action.action_type``).
        """
        timestamp = now or datetime.now(UTC)

        # Cooldown check first — cheaper than calling host policy.
        cooldown_violation = self._most_recent_match(action, before=timestamp)
        if cooldown_violation is not None:
            elapsed = timestamp - cooldown_violation.occurred_at
            if elapsed < self._cooldown:
                return self._record(
                    action,
                    decision=InterventionDecision.DENY_COOLDOWN,
                    reason=(
                        f"same {action.action_type.value} on {action.target!r} "
                        f"emitted {elapsed.total_seconds():.1f}s ago "
                        f"(cooldown {self._cooldown.total_seconds():.1f}s)"
                    ),
                    pattern=pattern,
                    timestamp=timestamp,
                )

        permitted, reason = self._policy.is_permitted(action, self.history)
        decision = (
            InterventionDecision.PERMIT
            if permitted
            else InterventionDecision.DENY_POLICY
        )
        return self._record(
            action,
            decision=decision,
            reason=reason,
            pattern=pattern,
            timestamp=timestamp,
        )

    def record_outcome(
        self,
        record: InterventionRecord,
        outcome: InterventionOutcome,
    ) -> InterventionRecord:
        """Update an existing record with the observed outcome.

        The record is replaced in the history deque. Callers should
        keep the returned value if they cache the record elsewhere.
        """
        try:
            index = next(i for i, item in enumerate(self._history) if item is record)
        except StopIteration:
            logger.warning("InterventionExecutor.record_outcome: record not in history")
            return record
        updated = InterventionRecord(
            action_type=record.action_type,
            target=record.target,
            decision=record.decision,
            reason=record.reason,
            outcome=outcome,
            pattern=record.pattern,
            occurred_at=record.occurred_at,
        )
        # deque does not support direct index assignment of a single
        # element when maxlen is set; rebuild as a list and refill.
        rebuilt = list(self._history)
        rebuilt[index] = updated
        self._history.clear()
        self._history.extend(rebuilt)
        return updated

    def _record(
        self,
        action: ControlAction,
        *,
        decision: InterventionDecision,
        reason: str,
        timestamp: datetime,
        pattern: InterventionType | None = None,
    ) -> InterventionRecord:
        record = InterventionRecord(
            action_type=action.action_type,
            target=action.target,
            decision=decision,
            reason=reason,
            pattern=pattern,
            occurred_at=timestamp,
        )
        self._history.append(record)
        logger.debug(
            "InterventionExecutor: %s on %s -> %s (%s)",
            action.action_type.value,
            action.target or "<no-target>",
            decision.value,
            reason,
        )
        return record

    def _most_recent_match(
        self,
        action: ControlAction,
        *,
        before: datetime,
    ) -> InterventionRecord | None:
        for record in reversed(self._history):
            if (
                record.action_type == action.action_type
                and record.target == action.target
                and record.decision == InterventionDecision.PERMIT
                and record.occurred_at < before
            ):
                return record
        return None


__all__ = [
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_HISTORY_SIZE",
    "AlwaysPermitPolicy",
    "InterventionDecision",
    "InterventionExecutor",
    "InterventionOutcome",
    "InterventionPermissionPolicy",
    "InterventionRecord",
    "InterventionType",
]
