"""Canalization metrics.

Typed signal for "agent stuck in a no-progress loop" — the situation
where a host's planner cycles through near-identical actions without
the world state changing in response. The metrics let a meta-cycle
react before resources are wasted further: widen search precision,
swap a module, escalate to a human, etc.

Four numbers in a frozen dataclass plus a coarse three-band risk
label. Callers compute the inputs from primitives their existing
detectors already emit (consecutive static cycles, A-distance
averages); Sakshi never reads host state directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CanalizationRisk(StrEnum):
    """Three-band classifier over the depth signal."""

    HEALTHY = "healthy"
    DEEPENING = "deepening"
    PATHOLOGICAL = "pathological"


HEALTHY_DEPTH_CEILING = 0.5
PATHOLOGICAL_DEPTH_FLOOR = 0.8


@dataclass(frozen=True)
class CanalizationMetrics:
    """Typed snapshot of canalization signals at a point in time.

    Attributes:
        depth: Normalized [0.0, 1.0] measure of how entrenched the
            current policy is. Conventionally
            ``static_cycles / max_history``.
        dwell_time: Number of cycles spent in the current near-static
            regime.
        perturbation_resistance: How much external perturbation
            (anomaly, expectation violation, intervention) the regime
            has absorbed without leaving. Higher means harder to break
            out of.
        temperature_sensitivity: Inverse of rigidity. Low values mean
            the agent's policy is largely deterministic given inputs;
            high values mean small input changes already produce
            meaningful policy variation.

    The ``risk`` property derives a coarse three-band label from
    ``depth`` for routing decisions; callers that need more nuance
    should read the four numbers directly.
    """

    depth: float = 0.0
    dwell_time: int = 0
    perturbation_resistance: float = 0.0
    temperature_sensitivity: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.depth <= 1.0:
            raise ValueError(f"depth must be in [0, 1], got {self.depth!r}")
        if self.dwell_time < 0:
            raise ValueError(
                f"dwell_time must be non-negative, got {self.dwell_time!r}"
            )
        if not 0.0 <= self.perturbation_resistance <= 1.0:
            raise ValueError(
                "perturbation_resistance must be in [0, 1], "
                f"got {self.perturbation_resistance!r}"
            )
        if not 0.0 <= self.temperature_sensitivity <= 1.0:
            raise ValueError(
                "temperature_sensitivity must be in [0, 1], "
                f"got {self.temperature_sensitivity!r}"
            )

    @property
    def risk(self) -> CanalizationRisk:
        if self.depth >= PATHOLOGICAL_DEPTH_FLOOR:
            return CanalizationRisk.PATHOLOGICAL
        if self.depth > HEALTHY_DEPTH_CEILING:
            return CanalizationRisk.DEEPENING
        return CanalizationRisk.HEALTHY


def metrics_from_static_cycles(
    *,
    static_cycles: int,
    max_history: int,
    perturbation_count: int = 0,
    perturbation_capacity: int = 0,
    temperature_sensitivity: float = 1.0,
) -> CanalizationMetrics:
    """Convenience factory wrapping the most common derivation.

    ``perturbation_resistance`` is computed as
    ``perturbation_count / perturbation_capacity`` when capacity is
    positive; otherwise it defaults to 0.0.
    """

    if max_history <= 0:
        raise ValueError("max_history must be positive")
    depth = min(1.0, max(0.0, static_cycles / max_history))
    if perturbation_capacity > 0:
        resistance = min(1.0, max(0.0, perturbation_count / perturbation_capacity))
    else:
        resistance = 0.0
    dwell = max(0, static_cycles)
    return CanalizationMetrics(
        depth=depth,
        dwell_time=dwell,
        perturbation_resistance=resistance,
        temperature_sensitivity=temperature_sensitivity,
    )


__all__ = [
    "HEALTHY_DEPTH_CEILING",
    "PATHOLOGICAL_DEPTH_FLOOR",
    "CanalizationMetrics",
    "CanalizationRisk",
    "metrics_from_static_cycles",
]
