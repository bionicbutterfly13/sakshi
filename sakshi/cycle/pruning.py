"""Trace pruning.

Long-running agents accumulate cycle traces that grow without bound.
The metacognitive layer cannot reason cleanly over an unbounded trace,
so hosts pass a ``TracePruner`` into the meta-controller to reduce a
``CycleTrace`` to the slice that is relevant for the current
metacognitive question.

Three default pruners ship with the package:

* ``LastNPruner`` keeps only the final N phase results — the simplest
  default and the right pick when host operators just want a recency
  window.
* ``SinceAnomalyPruner`` keeps every phase from the most recent
  anomaly forward; useful when the meta-cycle is diagnosing a
  developing failure.
* ``WhereExpectationFiredPruner`` keeps only phases whose output
  triggered at least one expectation (any kind of explicit signal in
  the phase output dictionary).

Hosts can write their own implementations against the ``TracePruner``
protocol. The package never selects a pruner on the caller's behalf.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from sakshi.models.cycle import CycleTrace, PhaseResult


@runtime_checkable
class TracePruner(Protocol):
    """Reduce a ``CycleTrace`` to the slice the meta-cycle should reason over."""

    def prune(self, trace: CycleTrace) -> CycleTrace: ...


class LastNPruner:
    """Keep only the final ``n`` phase results."""

    def __init__(self, n: int = 6) -> None:
        if n < 1:
            raise ValueError("LastNPruner requires n >= 1")
        self._n = n

    def prune(self, trace: CycleTrace) -> CycleTrace:
        if len(trace.phase_results) <= self._n:
            return trace
        return _replace_phase_results(trace, trace.phase_results[-self._n :])


class SinceAnomalyPruner:
    """Keep every phase from the last phase that recorded an anomaly forward.

    A phase is considered to have recorded an anomaly if its ``output``
    dict carries any of the keys in ``anomaly_keys`` with a truthy
    value. The default looks for ``anomaly``, ``anomalies``, and
    ``anomaly_event`` to match the conventions used elsewhere in the
    package.
    """

    DEFAULT_KEYS: tuple[str, ...] = ("anomaly", "anomalies", "anomaly_event")

    def __init__(self, anomaly_keys: Iterable[str] | None = None) -> None:
        self._keys = tuple(anomaly_keys) if anomaly_keys else self.DEFAULT_KEYS

    def prune(self, trace: CycleTrace) -> CycleTrace:
        results = trace.phase_results
        anchor: int | None = None
        for index, result in enumerate(results):
            if any(_truthy(result.output.get(key)) for key in self._keys):
                anchor = index
        if anchor is None:
            return _replace_phase_results(trace, [])
        return _replace_phase_results(trace, results[anchor:])


class WhereExpectationFiredPruner:
    """Keep phases whose output flagged at least one expectation.

    A phase is considered to have fired an expectation if its
    ``output`` dict contains a non-empty ``expectations`` list, an
    ``expectation_violations`` list, or a truthy ``expectation_fired``
    flag. The host can extend the keys checked by passing
    ``expectation_keys``.
    """

    DEFAULT_KEYS: tuple[str, ...] = (
        "expectations",
        "expectation_violations",
        "expectation_fired",
    )

    def __init__(self, expectation_keys: Iterable[str] | None = None) -> None:
        self._keys = tuple(expectation_keys) if expectation_keys else self.DEFAULT_KEYS

    def prune(self, trace: CycleTrace) -> CycleTrace:
        kept = [
            result
            for result in trace.phase_results
            if any(_truthy(result.output.get(key)) for key in self._keys)
        ]
        return _replace_phase_results(trace, kept)


def _truthy(value: object) -> bool:
    """Return whether a phase-output value should count as 'set'.

    Empty containers, empty strings, ``None``, and ``False`` are all
    treated as not-set; everything else counts as a signal worth
    keeping. This matches how phase output dictionaries are populated
    elsewhere in the package.
    """

    if value is None or value is False:
        return False
    if isinstance(value, (str, list, tuple, set, dict)):
        return len(value) > 0
    return True


def _replace_phase_results(
    trace: CycleTrace,
    phase_results: list[PhaseResult],
) -> CycleTrace:
    """Return a copy of ``trace`` with ``phase_results`` substituted."""

    return trace.model_copy(update={"phase_results": list(phase_results)})


__all__ = [
    "LastNPruner",
    "SinceAnomalyPruner",
    "TracePruner",
    "WhereExpectationFiredPruner",
]
