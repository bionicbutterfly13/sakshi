"""Confidence calibration tracking.

Sakshi modules attach confidence scores to many of the events they
emit (``AnomalyExplanation.confidence``, ``ControlAction`` rationale
text, plan-soundness ``SoundnessCheckResult.confidence``, etc.). The
``CalibrationTracker`` records pairs of ``(predicted_confidence,
actually_correct)`` over a sliding window and reports whether the
agent's confidence claims line up with reality.

Two reports come out of one tracker:

* ``self_trust_score`` — a single scalar in [0.0, 1.0] suitable for
  routing decisions. Computed as
  ``1.0 - mean(|predicted - actual_hit_rate|)`` over confidence
  deciles. A perfectly calibrated agent scores 1.0; an agent claiming
  90% confidence and being right half the time scores lower.
* ``calibration_warnings`` — a list of ``CalibrationWarning`` records
  identifying which confidence band is miscalibrated and by how much.
  A host can use these to widen the calibration band on a specific
  module's ``ExpectationProfile`` rather than blanket-suppress.

This consolidates what the original roadmap split across two
phases (an "inverse trust" module and a separate "calibration
auditor"). Same math, same window, one DTO surface.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

DEFAULT_WINDOW_SIZE = 200
DEFAULT_DECILES = 10
DEFAULT_MISCALIBRATION_THRESHOLD = 0.05  # 5 percentage points


@dataclass(frozen=True)
class ConfidenceObservation:
    """One predicted-confidence / actually-correct pair."""

    predicted_confidence: float
    actually_correct: bool
    label: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not 0.0 <= self.predicted_confidence <= 1.0:
            raise ValueError(
                "predicted_confidence must be in [0, 1], "
                f"got {self.predicted_confidence!r}"
            )


@dataclass(frozen=True)
class CalibrationWarning:
    """One miscalibrated decile."""

    decile_low: float
    decile_high: float
    sample_count: int
    predicted_mean: float
    empirical_hit_rate: float
    delta: float  # signed: positive = overconfident, negative = underconfident

    @property
    def is_overconfident(self) -> bool:
        return self.delta > 0

    @property
    def is_underconfident(self) -> bool:
        return self.delta < 0


@dataclass(frozen=True)
class CalibrationReport:
    """Aggregated calibration view over the current window."""

    sample_count: int
    self_trust_score: float
    warnings: tuple[CalibrationWarning, ...]


class CalibrationTracker:
    """Sliding-window tracker for ``(predicted_confidence, actual)`` pairs.

    Args:
        window_size: Maximum number of recent observations to retain.
        deciles: Number of equally spaced confidence bins. Default 10.
        miscalibration_threshold: Absolute delta between predicted mean
            and empirical hit rate above which a warning is issued for
            the bin. Default 0.05 (5 percentage points).
    """

    def __init__(
        self,
        *,
        window_size: int = DEFAULT_WINDOW_SIZE,
        deciles: int = DEFAULT_DECILES,
        miscalibration_threshold: float = DEFAULT_MISCALIBRATION_THRESHOLD,
    ) -> None:
        if window_size < 1:
            raise ValueError("window_size must be at least 1")
        if deciles < 2:
            raise ValueError("deciles must be at least 2")
        if miscalibration_threshold <= 0.0:
            raise ValueError("miscalibration_threshold must be positive")
        self._observations: deque[ConfidenceObservation] = deque(maxlen=window_size)
        self._deciles = deciles
        self._threshold = miscalibration_threshold

    @property
    def sample_count(self) -> int:
        return len(self._observations)

    def record(
        self,
        *,
        predicted_confidence: float,
        actually_correct: bool,
        label: str = "",
    ) -> ConfidenceObservation:
        """Record one observation and return its frozen DTO."""
        observation = ConfidenceObservation(
            predicted_confidence=predicted_confidence,
            actually_correct=actually_correct,
            label=label,
        )
        self._observations.append(observation)
        return observation

    def report(self) -> CalibrationReport:
        """Compute the current calibration report."""
        observations = list(self._observations)
        if not observations:
            return CalibrationReport(
                sample_count=0,
                self_trust_score=1.0,
                warnings=(),
            )
        bins = self._bin_observations(observations)
        warnings = tuple(self._warnings_from_bins(bins))
        score = self._self_trust_score(bins)
        return CalibrationReport(
            sample_count=len(observations),
            self_trust_score=score,
            warnings=warnings,
        )

    def _bin_observations(
        self,
        observations: list[ConfidenceObservation],
    ) -> list[list[ConfidenceObservation]]:
        bins: list[list[ConfidenceObservation]] = [[] for _ in range(self._deciles)]
        width = 1.0 / self._deciles
        for observation in observations:
            index = min(
                self._deciles - 1,
                int(observation.predicted_confidence / width),
            )
            bins[index].append(observation)
        return bins

    def _warnings_from_bins(
        self,
        bins: list[list[ConfidenceObservation]],
    ) -> Iterable[CalibrationWarning]:
        width = 1.0 / self._deciles
        for index, bin_obs in enumerate(bins):
            if not bin_obs:
                continue
            low = index * width
            high = low + width
            predicted_mean = sum(o.predicted_confidence for o in bin_obs) / len(bin_obs)
            hit_rate = sum(1 for o in bin_obs if o.actually_correct) / len(bin_obs)
            delta = predicted_mean - hit_rate
            if abs(delta) >= self._threshold:
                yield CalibrationWarning(
                    decile_low=low,
                    decile_high=high,
                    sample_count=len(bin_obs),
                    predicted_mean=predicted_mean,
                    empirical_hit_rate=hit_rate,
                    delta=delta,
                )

    def _self_trust_score(
        self,
        bins: list[list[ConfidenceObservation]],
    ) -> float:
        weighted_error = 0.0
        total = 0
        for bin_obs in bins:
            if not bin_obs:
                continue
            predicted_mean = sum(o.predicted_confidence for o in bin_obs) / len(bin_obs)
            hit_rate = sum(1 for o in bin_obs if o.actually_correct) / len(bin_obs)
            weighted_error += abs(predicted_mean - hit_rate) * len(bin_obs)
            total += len(bin_obs)
        if total == 0:
            return 1.0
        return max(0.0, 1.0 - weighted_error / total)


__all__ = [
    "DEFAULT_DECILES",
    "DEFAULT_MISCALIBRATION_THRESHOLD",
    "DEFAULT_WINDOW_SIZE",
    "CalibrationReport",
    "CalibrationTracker",
    "CalibrationWarning",
    "ConfidenceObservation",
]
