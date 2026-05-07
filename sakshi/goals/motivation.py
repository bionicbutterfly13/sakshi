"""Motivation auditor + metrics.

A read-only event log of host-supplied motivation events. The
auditor never modifies events, never makes acceptance decisions
(those are the host's job, gated by ``CreativityEnvelope`` and
``GoalRelevanceFilter``); it stores typed records and exposes a
metrics view a host can route on.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from math import log2

from sakshi.models.motivation import (
    ComputationalMotivationMetrics,
    MotivationEvent,
    MotivationType,
)

DEFAULT_AUDITOR_WINDOW = 500
RISK_TYPES: frozenset[MotivationType] = frozenset(
    {MotivationType.POWER, MotivationType.SURPRISE}
)


class MotivationAuditor:
    """Bounded ring-buffer audit log over ``MotivationEvent`` records.

    Args:
        window_size: Maximum number of recent events to retain.
    """

    def __init__(self, *, window_size: int = DEFAULT_AUDITOR_WINDOW) -> None:
        if window_size < 1:
            raise ValueError("window_size must be at least 1")
        self._events: deque[MotivationEvent] = deque(maxlen=window_size)

    def __len__(self) -> int:
        return len(self._events)

    @property
    def events(self) -> tuple[MotivationEvent, ...]:
        """Snapshot of recorded events, oldest first."""
        return tuple(self._events)

    def record(self, event: MotivationEvent) -> MotivationEvent:
        """Append an event to the audit log and return it unchanged."""
        self._events.append(event)
        return event

    def filter_by_type(
        self,
        motivation_type: MotivationType,
    ) -> list[MotivationEvent]:
        """Return events of the given motivation type, oldest first."""
        return [
            event
            for event in self._events
            if event.motivation_type == motivation_type
        ]

    def acceptance_rate(self) -> float:
        """Fraction of events with ``accepted=True``."""
        if not self._events:
            return 0.0
        accepted = sum(1 for event in self._events if event.accepted)
        return accepted / len(self._events)

    def metrics(self) -> ComputationalMotivationMetrics:
        """Return the four-scalar metrics view over the current window."""
        events = list(self._events)
        if not events:
            return ComputationalMotivationMetrics(
                diversity_score=0.0,
                stability_score=1.0,
                risk_assessment=0.0,
                communication_cost=0.0,
            )

        diversity = _diversity_score(events)
        stability = _stability_score(events)
        risk = _risk_score(events)
        comms = sum(1 for e in events if e.reason) / len(events)
        return ComputationalMotivationMetrics(
            diversity_score=diversity,
            stability_score=stability,
            risk_assessment=risk,
            communication_cost=comms,
        )


def _diversity_score(events: Iterable[MotivationEvent]) -> float:
    counts = Counter(event.motivation_type for event in events)
    total = sum(counts.values())
    distinct = len(counts)
    if total == 0 or distinct < 2:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count == 0:
            continue
        p = count / total
        entropy -= p * log2(p)
    max_entropy = log2(distinct)
    if max_entropy <= 0:
        return 0.0
    return max(0.0, min(1.0, entropy / max_entropy))


def _stability_score(events: list[MotivationEvent]) -> float:
    if len(events) < 4:
        return 1.0
    half = len(events) // 2
    early = events[:half]
    late = events[half:]
    early_rate = sum(1 for e in early if e.accepted) / len(early)
    late_rate = sum(1 for e in late if e.accepted) / len(late)
    drift = abs(early_rate - late_rate)
    return max(0.0, min(1.0, 1.0 - drift))


def _risk_score(events: list[MotivationEvent]) -> float:
    if not events:
        return 0.0
    risky = sum(1 for e in events if e.motivation_type in RISK_TYPES)
    return risky / len(events)


__all__ = [
    "DEFAULT_AUDITOR_WINDOW",
    "RISK_TYPES",
    "MotivationAuditor",
]
