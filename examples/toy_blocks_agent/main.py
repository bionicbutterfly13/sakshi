"""End-to-end runner: drive the BlocksAgent through Sakshi's seams.

Wires a real ``PhaseRegistry`` with an ``InMemoryEventBus``, records
each cycle's PERCEIVE / PLAN / ACT outputs, and prints the observation
transcript Sakshi captured.

Run from the repo root::

    python -m examples.toy_blocks_agent.main
"""

from __future__ import annotations

import asyncio
import json
import logging

from examples.toy_blocks_agent.adapters import (
    InMemoryEventBus,
    InMemoryGoalStateStore,
    LoggingWriteGuard,
)
from examples.toy_blocks_agent.agent import AgentCycleReport, BlocksAgent
from examples.toy_blocks_agent.world import BlocksWorld
from sakshi.registries import PhaseRegistry

MAX_CYCLES = 12


def report_to_phase_outputs(report: AgentCycleReport) -> dict[str, dict[str, object]]:
    """Translate one agent cycle into per-phase Sakshi payloads."""
    perceive_payload: dict[str, object] = {
        "facts": dict(report.perceived_facts),
        "confidence": 1.0,
    }
    plan_payload: dict[str, object] = {
        "action": report.planned_action.name if report.planned_action else None,
        "confidence": 0.9 if report.planned_action else 1.0,
    }
    act_payload: dict[str, object] = {
        "acted": report.acted,
        "error": report.error,
        "confidence": 1.0 if report.acted else 0.0,
    }
    return {
        "PERCEIVE": perceive_payload,
        "PLAN": plan_payload,
        "ACT": act_payload,
    }


async def run_one_cycle(
    agent: BlocksAgent,
    registry: PhaseRegistry,
    write_guard: LoggingWriteGuard,
    store: InMemoryGoalStateStore,
    cycle_id: str,
) -> AgentCycleReport:
    """Drive one host cognitive cycle through Sakshi's PhaseRegistry."""
    await registry.start_cycle(cycle_id=cycle_id)
    report = agent.run_cycle()
    outputs = report_to_phase_outputs(report)
    for phase_name, payload in outputs.items():
        await registry.record_phase_output(phase_name, payload)

    if report.acted and report.planned_action is not None:
        permit = await write_guard.check(
            "examples.toy_blocks_agent.act",
            {"action": report.planned_action.name},
        )
        if permit:
            store.facts = dict(agent.world.snapshot_facts())

    await registry.finalize_cycle()
    return report


async def run_until_goal(
    *,
    target_stack: list[str],
    initial_world: BlocksWorld | None = None,
    max_cycles: int = MAX_CYCLES,
) -> tuple[list[AgentCycleReport], InMemoryEventBus, InMemoryGoalStateStore]:
    """Run the toy agent until the goal stack is reached or budget runs out."""
    bus = InMemoryEventBus()
    registry = PhaseRegistry(event_bus=bus)
    write_guard = LoggingWriteGuard()
    store = InMemoryGoalStateStore()
    world = initial_world if initial_world is not None else BlocksWorld()
    agent = BlocksAgent(world=world, target_stack=target_stack)

    reports: list[AgentCycleReport] = []
    for i in range(max_cycles):
        cycle_id = f"toy-{i + 1:03d}"
        report = await run_one_cycle(
            agent=agent,
            registry=registry,
            write_guard=write_guard,
            store=store,
            cycle_id=cycle_id,
        )
        reports.append(report)
        if agent.is_goal_reached:
            break

    return reports, bus, store


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    reports, bus, store = await run_until_goal(target_stack=["A", "B", "C"])

    print("=== agent cycle transcript ===")
    for report in reports:
        action = report.planned_action.name if report.planned_action else "<noop>"
        status = (
            "ok" if report.acted else ("idle" if report.error is None else "blocked")
        )
        print(f"  {report.cycle_id}: action={action} status={status}")

    print()
    print(f"final world.on: {store.facts}")
    print(f"sakshi cycle.complete events emitted: {len(bus.events)}")
    if bus.events:
        last_type, last_payload = bus.events[-1]
        print(f"last event: {last_type} {json.dumps(last_payload, sort_keys=True)}")


if __name__ == "__main__":
    asyncio.run(_main())
