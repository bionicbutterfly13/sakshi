"""Meta-cycle scheduling policy.

Hosts that run the meta-cycle every object-cycle pay for the
metacognitive layer on every iteration even when nothing interesting
has happened. A ``MetaSchedulingPolicy`` lets the host swap that
default for a smarter rule: only run when an anomaly fired, only run
when load is below a threshold, run on a fixed cadence, etc.

Three default policies ship with the package:

* ``EveryCyclePolicy`` — current behavior; run on every cycle.
* ``OnAnomalyPolicy`` — run only when ``decide_to_run`` is called
  with at least one anomaly recorded. Cheapest default for hosts
  whose object-level cycle is already stable.
* ``ThrottledByLoadPolicy`` — run only when the supplied
  ``CanalizationMetrics`` shows load below a configured depth band.

The protocol is sync; deciding whether to run the meta-cycle is a
fast structural check, not an I/O step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sakshi.meta.canalization import CanalizationMetrics, CanalizationRisk


@dataclass(frozen=True)
class SchedulingDecision:
    """Result of one ``decide_to_run`` call."""

    should_run: bool
    reason: str = ""


@runtime_checkable
class MetaSchedulingPolicy(Protocol):
    """Decide whether to run the meta-cycle on this iteration.

    Hosts pass the latest ``CanalizationMetrics`` (or a default
    ``CanalizationMetrics()``) and the count of anomalies recorded
    since the previous meta-cycle. Implementations decide.
    """

    def decide_to_run(
        self,
        *,
        anomalies_since_last_run: int,
        canalization: CanalizationMetrics,
    ) -> SchedulingDecision: ...


class EveryCyclePolicy:
    """Run the meta-cycle on every iteration."""

    def decide_to_run(
        self,
        *,
        anomalies_since_last_run: int,
        canalization: CanalizationMetrics,
    ) -> SchedulingDecision:
        del anomalies_since_last_run, canalization
        return SchedulingDecision(should_run=True, reason="every-cycle policy")


class OnAnomalyPolicy:
    """Run only when at least one anomaly fired since the previous run."""

    def decide_to_run(
        self,
        *,
        anomalies_since_last_run: int,
        canalization: CanalizationMetrics,
    ) -> SchedulingDecision:
        del canalization
        if anomalies_since_last_run > 0:
            return SchedulingDecision(
                should_run=True,
                reason=(f"{anomalies_since_last_run} anomaly(ies) since last run"),
            )
        return SchedulingDecision(should_run=False, reason="no anomalies")


class ThrottledByLoadPolicy:
    """Skip the meta-cycle when canalization load is above the threshold.

    Args:
        max_run_risk: Highest ``CanalizationRisk`` band that still
            permits a run. ``HEALTHY`` and ``DEEPENING`` permit runs by
            default; ``PATHOLOGICAL`` skips runs to prevent thrashing.
        always_run_on_anomaly: When True, an anomaly overrides the
            throttle and forces a run. Defaults to True; an anomaly
            during high load is exactly when a host needs the meta
            layer.
    """

    _RISK_RANK = {
        CanalizationRisk.HEALTHY: 0,
        CanalizationRisk.DEEPENING: 1,
        CanalizationRisk.PATHOLOGICAL: 2,
    }

    def __init__(
        self,
        *,
        max_run_risk: CanalizationRisk = CanalizationRisk.DEEPENING,
        always_run_on_anomaly: bool = True,
    ) -> None:
        self._max_rank = self._RISK_RANK[max_run_risk]
        self._always_run_on_anomaly = always_run_on_anomaly

    def decide_to_run(
        self,
        *,
        anomalies_since_last_run: int,
        canalization: CanalizationMetrics,
    ) -> SchedulingDecision:
        if self._always_run_on_anomaly and anomalies_since_last_run > 0:
            return SchedulingDecision(
                should_run=True,
                reason=(
                    f"anomaly override ({anomalies_since_last_run}) "
                    f"despite {canalization.risk.value} load"
                ),
            )
        rank = self._RISK_RANK[canalization.risk]
        if rank <= self._max_rank:
            return SchedulingDecision(
                should_run=True,
                reason=f"load {canalization.risk.value} permits run",
            )
        return SchedulingDecision(
            should_run=False,
            reason=(
                f"load {canalization.risk.value} above threshold; skipping meta-cycle"
            ),
        )


__all__ = [
    "EveryCyclePolicy",
    "MetaSchedulingPolicy",
    "OnAnomalyPolicy",
    "SchedulingDecision",
    "ThrottledByLoadPolicy",
]
