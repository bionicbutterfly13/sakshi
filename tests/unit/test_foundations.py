from __future__ import annotations

import pytest

from sakshi.cycle import CognitiveBlackboard, CycleHistory
from sakshi.models import (
    BlackboardKey,
    CycleTrace,
    Goal,
    GoalPredicate,
    WorldStateSnapshot,
)
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


def test_core_dtos_instantiate() -> None:
    goal = Goal(id="goal-1", predicate=GoalPredicate(name="CLEAR"))
    snapshot = WorldStateSnapshot(facts={"CLEAR": {}})

    assert goal.id == "goal-1"
    assert snapshot.contains("CLEAR")
