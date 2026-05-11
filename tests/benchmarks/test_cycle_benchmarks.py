"""Benchmarks for the hot paths in a Sakshi cycle.

These measure the latency and throughput Sakshi adds to a host's
cognitive loop. They are not coverage tests — runs persist to
``.benchmarks/`` and compare against the committed baseline so a
regression in any minor release fails the gate.
"""

from __future__ import annotations

import asyncio

import pytest

from sakshi.cycle import CognitiveBlackboard
from sakshi.goals.graph import GoalGraph
from sakshi.meta import AlwaysPermitPolicy, InterventionExecutor
from sakshi.models import (
    BlackboardKey,
    ControlAction,
    ControlActionType,
    Goal,
    GoalPredicate,
)
from sakshi.protocols import NoOpEventBus
from sakshi.registries import PhaseRegistry


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _make_goal(id_: str, *, parent: str | None = None) -> Goal:
    """Goal factory shared by graph benchmarks."""
    del parent
    return Goal(
        id=id_,
        predicate=GoalPredicate(name="ANSWER", args={}),
        priority=2,
    )


def test_phase_registry_full_cycle(benchmark, event_loop) -> None:
    """One full PERCEIVE → INTERPRET → EVAL → INTEND → PLAN → ACT cycle.

    This is the per-cycle overhead Sakshi adds to a host. The unit-test
    suite asserts behavior; this run measures wall time.
    """
    bus = NoOpEventBus()
    registry = PhaseRegistry(event_bus=bus)

    async def one_cycle(cycle_id: str) -> None:
        await registry.start_cycle(cycle_id=cycle_id)
        await registry.record_phase_output("PERCEIVE", {"x": 1, "confidence": 1.0})
        await registry.record_phase_output("INTERPRET", {"y": 2, "confidence": 0.9})
        await registry.record_phase_output("EVAL", {"ok": True, "confidence": 0.9})
        await registry.record_phase_output("INTEND", {"goal": "g1", "confidence": 0.9})
        await registry.record_phase_output("PLAN", {"step": "do", "confidence": 0.9})
        await registry.record_phase_output("ACT", {"acted": True, "confidence": 1.0})
        await registry.finalize_cycle()

    counter = {"n": 0}

    def run_one() -> None:
        counter["n"] += 1
        event_loop.run_until_complete(one_cycle(f"bench-{counter['n']:05d}"))

    benchmark(run_one)


def test_blackboard_set_get_roundtrip(benchmark, event_loop) -> None:
    """Async set + get on a per-key lock."""
    bb = CognitiveBlackboard()

    async def roundtrip() -> None:
        await bb.set(BlackboardKey.STATES, {"position": 1})
        await bb.get(BlackboardKey.STATES)

    def run_one() -> None:
        event_loop.run_until_complete(roundtrip())

    benchmark(run_one)


def test_blackboard_snapshot_with_payload(benchmark, event_loop) -> None:
    """Snapshot with a non-trivial payload exercises deepcopy."""
    bb = CognitiveBlackboard()
    payload = {"facts": {f"k{i}": i for i in range(100)}}

    async def fill_and_snapshot() -> None:
        await bb.set(BlackboardKey.STATES, payload)
        await bb.snapshot(cycle_id="snap-1")

    def run_one() -> None:
        event_loop.run_until_complete(fill_and_snapshot())

    benchmark(run_one)


def test_goal_graph_add_chain_50(benchmark) -> None:
    """Adding a 50-deep chain of parent→child goals."""

    def build() -> GoalGraph:
        graph = GoalGraph()
        prev: str | None = None
        for i in range(50):
            goal_id = f"g{i:03d}"
            graph.add_goal(_make_goal(goal_id), parent_id=prev)
            prev = goal_id
        return graph

    benchmark(build)


def test_goal_graph_active_frontier_500(benchmark) -> None:
    """Computing the active frontier over a wide graph."""
    graph = GoalGraph()
    graph.add_goal(_make_goal("root"))
    for i in range(500):
        graph.add_goal(_make_goal(f"leaf-{i:04d}"), parent_id="root")

    benchmark(graph.get_active_frontier)


def test_intervention_executor_validate(benchmark) -> None:
    """Cooldown lookup + policy call + audit append on a permitted action."""
    executor = InterventionExecutor(
        policy=AlwaysPermitPolicy(), cooldown_seconds=0.0, history_size=1024
    )
    counter = {"n": 0}

    def run_one() -> None:
        counter["n"] += 1
        action = ControlAction(
            action_type=ControlActionType.SWAP_MODULE,
            target=f"module-{counter['n'] % 16}",
            rationale="benchmark",
        )
        executor.validate(action)

    benchmark(run_one)


def test_blocks_agent_end_to_end(benchmark, event_loop) -> None:
    """Full toy_blocks_agent run from a flat table to A-on-B-on-C.

    This is the integration baseline — Sakshi seam overhead + a real
    host loop. If it ever exceeds ~5x its baseline that's a real
    regression somewhere in the cycle infrastructure.
    """
    from examples.toy_blocks_agent.main import run_until_goal

    def run_one() -> None:
        event_loop.run_until_complete(run_until_goal(target_stack=["A", "B", "C"]))

    benchmark(run_one)
