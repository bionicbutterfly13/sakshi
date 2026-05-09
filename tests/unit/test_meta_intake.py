from __future__ import annotations

from datetime import timedelta

import pytest

from sakshi.goals import DomainRegistry, GoalGenerator, GoalGraph, GoalValidator
from sakshi.intake import InstructionIngestRequest, InstructionIngestService
from sakshi.meta import (
    DenyByDefaultPolicy,
    InterventionDecision,
    InterventionExecutor,
    MetaController,
    build_world_state_from_trace,
)
from sakshi.models import ControlActionType, CycleTrace, OODAPhase, PhaseResult


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, dict(payload)))


class FakeWriteGuard:
    def __init__(self, permitted: bool = True) -> None:
        self.permitted = permitted
        self.calls: list[tuple[str, dict]] = []

    async def check(self, source_origin: str, payload: dict) -> bool:
        self.calls.append((source_origin, dict(payload)))
        return self.permitted


@pytest.mark.asyncio
async def test_instruction_ingest_creates_goal_and_deduplicates() -> None:
    graph = GoalGraph()
    service = InstructionIngestService(
        goal_graph=graph,
        dedup_window=timedelta(minutes=5),
    )
    request = InstructionIngestRequest(text="Calibrate attention", source="user")

    first = await service.ingest_instruction(request)
    second = await service.ingest_instruction(request)

    assert first.accepted is True
    assert first.reason == "created"
    assert first.goal_id is not None
    assert graph.get_node(first.goal_id).goal.predicate.name == "FOLLOW_INSTRUCTION"
    assert second.accepted is False
    assert second.reason == "duplicate_instruction"
    assert second.goal_id == first.goal_id


@pytest.mark.asyncio
async def test_meta_controller_monitors_assesses_controls_and_emits() -> None:
    graph = GoalGraph()
    await _goal_from_instruction(graph, "Pay attention to workspace")
    bus = FakeEventBus()
    controller = MetaController(
        goal_graph=graph,
        event_bus=bus,
        anomaly_frequency_provider=lambda: 0.0,
    )
    trace = CycleTrace(
        cycle_id="cycle-1",
        phase_results=[
            PhaseResult(
                phase_name="PERCEIVE",
                ooda_phase=OODAPhase.OBSERVE,
                output={"confidence": 0.2, "active_basins": ["WORKSPACE"]},
            )
        ],
        achieved_goals=[],
    )

    result = await controller.run_meta_cycle(trace, opacity_level=0.5)

    assert result.monitoring_data["phase_count"] == 1
    assert any(
        action.action_type == ControlActionType.ADJUST_PRECISION
        for action in result.actions
    )
    assert any(
        action.action_type == ControlActionType.STRENGTHEN_MODULE
        for action in result.actions
    )
    assert result.intervention_records
    assert all(
        record.decision == InterventionDecision.PERMIT
        for record in result.intervention_records
    )
    assert bus.events[0][0] == "sakshi.meta.control"
    assert len(bus.events[0][1]["actions"]) == len(result.actions)


@pytest.mark.asyncio
async def test_meta_controller_denied_intervention_blocks_publication() -> None:
    bus = FakeEventBus()
    controller = MetaController(
        event_bus=bus,
        intervention_executor=InterventionExecutor(
            policy=DenyByDefaultPolicy(),
            cooldown_seconds=0.0,
        ),
    )
    trace = CycleTrace(
        cycle_id="cycle-1",
        phase_results=[
            PhaseResult(
                phase_name="PERCEIVE",
                ooda_phase=OODAPhase.OBSERVE,
                output={"confidence": 0.2},
            )
        ],
    )

    result = await controller.run_meta_cycle(trace, opacity_level=0.5)

    assert result.actions == []
    assert result.intervention_records
    assert all(
        record.decision == InterventionDecision.DENY_POLICY
        for record in result.intervention_records
    )
    assert bus.events == []


@pytest.mark.asyncio
async def test_meta_controller_escalation_mutates_goal_through_write_guard() -> None:
    graph = GoalGraph()
    domain = DomainRegistry()
    domain.add_predicate("INVESTIGATE_ANOMALY_WIDENED")
    generator = GoalGenerator(
        validator=GoalValidator(domain),
        graph=graph,
    )
    goal = await _goal_from_instruction(graph, "Investigate anomaly")
    guard = FakeWriteGuard(permitted=True)
    controller = MetaController(
        goal_graph=graph,
        goal_generator=generator,
        write_guard=guard,
        anomaly_frequency_provider=lambda: 1.0,
    )
    trace = CycleTrace(cycle_id="cycle-1")

    for _ in range(4):
        await controller.run_meta_cycle(trace)

    assert guard.calls
    assert any(
        goal_id.startswith("mutated-goal") for goal_id in graph.as_dict()["goals"]
    )
    assert graph.get_node(goal.id).goal.status.value == "active"


def test_build_world_state_from_trace_extracts_active_basins() -> None:
    trace = CycleTrace(
        cycle_id="cycle-1",
        phase_results=[
            PhaseResult(
                phase_name="PERCEIVE",
                ooda_phase=OODAPhase.OBSERVE,
                output={"active_basins": ["A", "B"]},
            )
        ],
    )

    snapshot = build_world_state_from_trace(trace)
    assert snapshot.contains("A")
    assert snapshot.contains("B")


async def _goal_from_instruction(graph: GoalGraph, text: str):
    service = InstructionIngestService(goal_graph=graph, dedup_window=timedelta(0))
    result = await service.ingest_instruction(InstructionIngestRequest(text=text))
    assert result.goal_id is not None
    return graph.get_node(result.goal_id).goal
