"""A-distance anomaly detection.

Computes a practical approximation of A-distance over activation
streams and optionally emits anomaly events through the host-supplied
`EventBus`.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from sakshi.models.anomaly import AnomalySourceType
from sakshi.protocols import EventBus

logger = logging.getLogger(__name__)

PRIOR_BASELINE_WINDOWS: dict[str, int | None] = {
    "B": 20,
    "L": None,
    "D": None,
    "λ": 5,
    "lambda": 5,
}


class AnomalyEvent(BaseModel):
    """Statistical anomaly detected in an activation stream.

    The ``source`` field tags the anomaly's origin lane. The A-distance
    detector defaults to ``WORLD`` because it operates on environment
    activations; meta-cycle internal detectors should construct events
    with ``source=COGNITIVE``. ``COMPOUND`` is reserved for events that
    legitimately straddle both lanes and must be decomposed before
    explanation.
    """

    a_distance: float = Field(
        ge=0.0,
        le=2.0,
        description="A-distance value in the theoretical 0-2 range",
    )
    current_activations: dict[str, float] = Field(default_factory=dict)
    baseline_mean: dict[str, float] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    threshold_used: float = 0.5
    source: AnomalySourceType = Field(
        default=AnomalySourceType.WORLD,
        description="Origin lane: WORLD | COGNITIVE | COMPOUND",
    )

    @property
    def severity(self) -> str:
        if self.a_distance >= 1.5:
            return "HIGH"
        if self.a_distance >= 0.8:
            return "MEDIUM"
        return "LOW"


class PredicateStream:
    """Sliding-window buffer for activation observations."""

    def __init__(self, max_size: int = 50) -> None:
        self._buffer: deque[dict[str, float]] = deque(maxlen=max_size)

    def push(self, activations: dict[str, float]) -> None:
        """Append a new observation."""
        self._buffer.append(dict(activations))

    def get_window(self, size: int | None = None) -> list[dict[str, float]]:
        """Return the last `size` observations, or all observations."""
        data = list(self._buffer)
        if size is None or size >= len(data):
            return data
        return data[-size:]

    def mean_vector(self, keys: list[str] | None = None) -> dict[str, float]:
        """Compute element-wise mean across all stored observations."""
        if not self._buffer:
            return {}
        all_keys = keys or list(self._buffer[-1].keys())
        return {
            key: sum(obs.get(key, 0.0) for obs in self._buffer) / len(self._buffer)
            for key in all_keys
        }

    def __len__(self) -> int:
        return len(self._buffer)


class ADistanceDetector:
    """Compute A-distance between current activations and a rolling baseline.

    The implementation uses normalized L2 distance as a deterministic,
    dependency-free proxy for minimum classification error:

    `a_dist ~= 2 * ||current - baseline||_2 / sqrt(d)`
    """

    def __init__(
        self,
        *,
        threshold: float = 0.5,
        baseline_window: int = 10,
        prior_type: str | None = None,
        event_bus: EventBus | None = None,
        anomaly_event_type: str = "sakshi.anomaly.detected",
    ) -> None:
        override = (
            PRIOR_BASELINE_WINDOWS.get(prior_type or "")
            if prior_type is not None
            else None
        )
        self._baseline_window = override if override is not None else baseline_window
        self._threshold = threshold
        self._prior_type = prior_type
        self._event_bus = event_bus
        self._anomaly_event_type = anomaly_event_type
        self._stream = PredicateStream(max_size=max(self._baseline_window * 3, 50))
        self._observation_count = 0
        self._anomaly_count = 0

    @property
    def baseline_window(self) -> int:
        return self._baseline_window

    @property
    def baseline_window_size(self) -> int:
        """Alias for compatibility with existing tests."""
        return self._baseline_window

    @property
    def has_baseline(self) -> bool:
        """True once enough observations exist to form a baseline."""
        return len(self._stream) >= self._baseline_window

    async def observe(self, activations: dict[str, float]) -> AnomalyEvent | None:
        """Process one observation and return an event if anomalous."""
        self._stream.push(activations)
        self._observation_count += 1

        if not self.has_baseline:
            return None

        baseline_mean = compute_mean(
            self._stream.get_window(size=self._baseline_window)
        )
        distance = compute_a_distance(activations, baseline_mean)

        if distance <= self._threshold:
            return None

        self._anomaly_count += 1
        event = AnomalyEvent(
            a_distance=distance,
            current_activations=dict(activations),
            baseline_mean=baseline_mean,
            threshold_used=self._threshold,
        )
        logger.info(
            "a_distance anomaly detected distance=%.3f threshold=%.3f severity=%s",
            distance,
            self._threshold,
            event.severity,
        )
        await self._publish_anomaly(event)
        return event

    def get_anomaly_frequency(self) -> float:
        """Return fraction of observations that triggered an anomaly."""
        if self._observation_count == 0:
            return 0.0
        return min(1.0, self._anomaly_count / self._observation_count)

    async def update_baseline(self, window_size: int | None = None) -> None:
        """Optionally set a new baseline window size."""
        if window_size is not None:
            self._baseline_window = min(window_size, len(self._stream))

    def get_baseline_snapshot(self) -> dict[str, float]:
        """Return baseline mean vector using current window size."""
        window = self._stream.get_window(size=self._baseline_window)
        return compute_mean(window) if window else {}

    async def _publish_anomaly(self, event: AnomalyEvent) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.emit(
                self._anomaly_event_type,
                event.model_dump(),
            )
        except Exception:
            logger.exception("failed to publish anomaly event")


def compute_mean(observations: list[dict[str, float]]) -> dict[str, float]:
    """Return element-wise mean for a list of activation dicts."""
    if not observations:
        return {}
    keys: set[str] = set()
    for observation in observations:
        keys.update(observation.keys())
    return {
        key: sum(observation.get(key, 0.0) for observation in observations)
        / len(observations)
        for key in keys
    }


def compute_a_distance(
    current: dict[str, float],
    baseline_mean: dict[str, float],
) -> float:
    """Compute approximate A-distance between current and baseline means."""
    if not baseline_mean:
        return 0.0
    keys = set(current.keys()) | set(baseline_mean.keys())
    if not keys:
        return 0.0
    squared_sum = sum(
        (current.get(key, 0.0) - baseline_mean.get(key, 0.0)) ** 2 for key in keys
    )
    distance = 2.0 * math.sqrt(squared_sum) / math.sqrt(len(keys))
    return min(2.0, distance)
