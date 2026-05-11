"""Smoke tests for the toy_blocks_agent reference integration.

These tests live in the package test suite so the example cannot
silently break when Sakshi's seams evolve. They exercise the world
model, the agent's planner, and the Sakshi wiring end-to-end.
"""

from __future__ import annotations

import pytest

from examples.toy_blocks_agent import (
    BlocksAgent,
    BlocksWorld,
    InMemoryEventBus,
    InMemoryGoalStateStore,
    InvalidActionError,
    LoggingWriteGuard,
    PickupAction,
    PutdownAction,
    block_stack,
)
from examples.toy_blocks_agent.main import run_until_goal


def test_world_pickup_and_putdown_round_trip() -> None:
    world = BlocksWorld()
    world.apply(PickupAction(block="A"))
    assert world.held == "A"
    assert "A" not in world.on
    world.apply(PutdownAction(block="A", target="B"))
    assert world.held is None
    assert world.on["A"] == "B"


def test_world_rejects_pickup_when_already_holding() -> None:
    world = BlocksWorld()
    world.apply(PickupAction(block="A"))
    with pytest.raises(InvalidActionError, match="already holding|while holding"):
        world.apply(PickupAction(block="B"))


def test_world_rejects_putdown_onto_occupied_block() -> None:
    world = BlocksWorld()
    world.on["A"] = "B"  # A already sits on B
    world.apply(PickupAction(block="C"))
    with pytest.raises(InvalidActionError, match="not clear"):
        world.apply(PutdownAction(block="C", target="B"))


def test_block_stack_walks_chain_to_table() -> None:
    world = BlocksWorld(on={"A": "B", "B": "C", "C": "table"})
    assert block_stack(world, "A") == ["A", "B", "C"]


def test_agent_reports_goal_already_satisfied() -> None:
    world = BlocksWorld(on={"A": "B", "B": "C", "C": "table"})
    agent = BlocksAgent(world=world, target_stack=["A", "B", "C"])
    assert agent.is_goal_reached
    report = agent.run_cycle()
    assert report.planned_action is None
    assert report.acted is False


def test_agent_rejects_duplicate_blocks_in_target() -> None:
    with pytest.raises(ValueError, match="distinct"):
        BlocksAgent(world=BlocksWorld(), target_stack=["A", "A"])


@pytest.mark.asyncio
async def test_run_until_goal_drives_clean_stack_in_four_cycles() -> None:
    reports, bus, store = await run_until_goal(target_stack=["A", "B", "C"])

    assert all(r.error is None for r in reports), [r.error for r in reports]
    assert len(reports) == 4, "the greedy planner needs four moves"
    assert reports[-1].acted is True
    assert store.facts["ON(A,B)"] == "true"
    assert store.facts["ON(B,C)"] == "true"
    assert store.facts["ON(C,table)"] == "true"
    event_types = [t for t, _ in bus.events]
    assert event_types.count("sakshi.cycle.complete") == 4


@pytest.mark.asyncio
async def test_run_until_goal_records_one_write_check_per_action() -> None:
    """Every executed action should fire the WriteGuard seam exactly once."""
    bus = InMemoryEventBus()
    store = InMemoryGoalStateStore()
    write_guard = LoggingWriteGuard()
    world = BlocksWorld()
    agent = BlocksAgent(world=world, target_stack=["A", "B", "C"])

    from examples.toy_blocks_agent.main import run_one_cycle
    from sakshi.registries import PhaseRegistry

    registry = PhaseRegistry(event_bus=bus)

    acted_count = 0
    for i in range(8):
        report = await run_one_cycle(
            agent=agent,
            registry=registry,
            write_guard=write_guard,
            store=store,
            cycle_id=f"toy-{i + 1:03d}",
        )
        if report.acted:
            acted_count += 1
        if agent.is_goal_reached:
            break

    assert len(write_guard.checks) == acted_count
    assert all(
        origin.startswith("examples.toy_blocks_agent")
        for origin, _ in write_guard.checks
    )
