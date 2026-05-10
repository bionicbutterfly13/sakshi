from __future__ import annotations

import asyncio

import pytest

from sakshi.cycle import CognitiveBlackboard, CycleHistory
from sakshi.errors import PhaseTransitionError
from sakshi.models import (
    BlackboardKey,
    CycleTrace,
    Goal,
    GoalPredicate,
    WorldStateSnapshot,
)
from sakshi.protocols import DenyByDefaultWriteGuard
from sakshi.registries import ModuleRegistry, PhaseRegistry


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, dict(payload)))


@pytest.mark.asyncio
async def test_blackboard_snapshots_are_decoupled_from_live_state() -> None:
    blackboard = CognitiveBlackboard()

    value = {"position": 1}
    await blackboard.set(BlackboardKey.STATES, value)
    snapshot = await blackboard.snapshot("cycle-1")
    value["position"] = 2

    assert snapshot.cycle_id == "cycle-1"
    assert snapshot.data["states"]["position"] == 1


@pytest.mark.asyncio
async def test_blackboard_clear_is_atomic_against_concurrent_writers() -> None:
    """clear() must hold every per-key lock so concurrent sets cannot leave
    a partially-cleared dict — i.e. no key written *before* clear() may
    survive into the post-clear state.
    """
    blackboard = CognitiveBlackboard()

    pre_clear_keys = [BlackboardKey.STATES, BlackboardKey.GOALS]
    for key in pre_clear_keys:
        await blackboard.set(key, {"phase": "pre-clear"})

    async def late_writer(key: BlackboardKey) -> None:
        await blackboard.set(key, {"phase": "post-clear"})

    writer_task = asyncio.create_task(late_writer(BlackboardKey.STATES))
    await blackboard.clear()
    await writer_task

    keys_after = await blackboard.keys()
    for key in keys_after:
        value = await blackboard.get(key)
        assert value == {"phase": "post-clear"}, (
            f"key {key!r} carries pre-clear residue: {value!r}"
        )


def test_cycle_history_tracks_latest_trace() -> None:
    history = CycleHistory(max_size=3)

    history.add(CycleTrace(cycle_id="cycle-1"))
    history.add(CycleTrace(cycle_id="cycle-2"))

    assert history.get_latest() is not None
    assert history.get_latest().cycle_id == "cycle-2"
    assert history.get_n_prev_cycle(1).cycle_id == "cycle-1"


def test_module_registry_swaps_active_module() -> None:
    registry = ModuleRegistry()
    registry.register("PERCEIVE", "primary", priority=1)
    registry.register("PERCEIVE", "fallback", priority=2)

    assert registry.get_active_module("PERCEIVE").name == "primary"
    assert registry.swap_module("PERCEIVE", "fallback") is True
    assert registry.get_active_module("PERCEIVE").name == "fallback"


@pytest.mark.asyncio
async def test_phase_registry_records_and_emits_cycle_complete() -> None:
    bus = FakeEventBus()
    registry = PhaseRegistry(event_bus=bus)

    await registry.start_cycle("cycle-1")
    await registry.record_phase_output("PERCEIVE", {"observed": True})
    trace = await registry.finalize_cycle()

    assert trace.cycle_id == "cycle-1"
    assert len(trace.phase_results) == 1
    assert bus.events == [
        (
            "sakshi.cycle.complete",
            {
                "cycle_id": "cycle-1",
                "phase_count": 1,
                "achieved_goal_ids": [],
            },
        )
    ]


@pytest.mark.asyncio
async def test_phase_registry_fail_fast_callbacks_surfaces_callback_failure() -> None:
    bus = FakeEventBus()
    registry = PhaseRegistry(event_bus=bus, fail_fast_callbacks=True)

    async def failing_callback(trace: CycleTrace) -> None:
        del trace
        raise RuntimeError("callback storage failed")

    registry.on_cycle_complete(failing_callback)
    await registry.start_cycle("cycle-1")

    with pytest.raises(PhaseTransitionError, match="callback failed"):
        await registry.finalize_cycle()

    assert bus.events == []


@pytest.mark.asyncio
async def test_deny_by_default_write_guard_denies_without_host_guard() -> None:
    guard = DenyByDefaultWriteGuard()

    allowed = await guard.check(
        "sakshi.goal_outcome",
        {"goal_id": "g", "status": "achieved"},
    )

    assert allowed is False


def test_core_dtos_instantiate() -> None:
    goal = Goal(id="goal-1", predicate=GoalPredicate(name="CLEAR"))
    snapshot = WorldStateSnapshot(facts={"CLEAR": {}})

    assert goal.id == "goal-1"
    assert snapshot.contains("CLEAR")
