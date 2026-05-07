"""Tests for the TracePruner protocol and shipped defaults."""

from __future__ import annotations

from sakshi.cycle import (
    LastNPruner,
    SinceAnomalyPruner,
    TracePruner,
    WhereExpectationFiredPruner,
)
from sakshi.models import CycleTrace, OODAPhase, PhaseResult


def _trace(*outputs: dict[str, object]) -> CycleTrace:
    phase_names = ["PERCEIVE", "INTERPRET", "EVAL", "INTEND", "PLAN", "ACT"]
    ooda = [
        OODAPhase.OBSERVE,
        OODAPhase.ORIENT,
        OODAPhase.ORIENT,
        OODAPhase.DECIDE,
        OODAPhase.DECIDE,
        OODAPhase.ACT,
    ]
    results = [
        PhaseResult(phase_name=phase_names[i], ooda_phase=ooda[i], output=output)
        for i, output in enumerate(outputs)
    ]
    return CycleTrace(cycle_id="c-1", phase_results=results)


def test_protocol_runtime_check() -> None:
    assert isinstance(LastNPruner(), TracePruner)
    assert isinstance(SinceAnomalyPruner(), TracePruner)
    assert isinstance(WhereExpectationFiredPruner(), TracePruner)


def test_last_n_pruner_keeps_tail() -> None:
    trace = _trace({}, {}, {}, {}, {}, {})
    pruned = LastNPruner(n=2).prune(trace)
    assert [r.phase_name for r in pruned.phase_results] == ["PLAN", "ACT"]
    # Original trace is unchanged.
    assert len(trace.phase_results) == 6


def test_last_n_pruner_short_circuits_when_already_short() -> None:
    trace = _trace({}, {})
    pruned = LastNPruner(n=10).prune(trace)
    assert pruned is trace


def test_since_anomaly_pruner_picks_last_anchor() -> None:
    trace = _trace(
        {"anomaly": True},
        {},
        {"anomaly_event": {"a_distance": 0.9}},
        {},
        {},
        {},
    )
    pruned = SinceAnomalyPruner().prune(trace)
    # Anchored at index 2 (the most recent anomaly).
    names = [r.phase_name for r in pruned.phase_results]
    assert names == ["EVAL", "INTEND", "PLAN", "ACT"]


def test_since_anomaly_pruner_returns_empty_when_no_anomaly() -> None:
    trace = _trace({}, {}, {})
    pruned = SinceAnomalyPruner().prune(trace)
    assert pruned.phase_results == []


def test_where_expectation_fired_pruner_filters() -> None:
    trace = _trace(
        {},
        {"expectation_violations": [{"id": "x"}]},
        {},
        {"expectation_fired": True},
        {"expectation_fired": False},
        {"expectations": []},
    )
    pruned = WhereExpectationFiredPruner().prune(trace)
    names = [r.phase_name for r in pruned.phase_results]
    assert names == ["INTERPRET", "INTEND"]


def test_pruners_do_not_mutate_input() -> None:
    trace = _trace({}, {}, {})
    LastNPruner(n=1).prune(trace)
    SinceAnomalyPruner().prune(trace)
    WhereExpectationFiredPruner().prune(trace)
    assert len(trace.phase_results) == 3
