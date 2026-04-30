from __future__ import annotations

import pytest

from sakshi.interpret import (
    ADistanceDetector,
    AnomalyPersistenceTracker,
    DRFreeAmbiguityDetector,
    ExpectationEvaluator,
)
from sakshi.models import (
    CognitiveExpectation,
    CycleTrace,
    ExpectationSeverity,
    PhaseResult,
)
from sakshi.world import WorldSimulator


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, dict(payload)))


@pytest.mark.asyncio
async def test_world_simulator_predicts_and_detects_discrepancy() -> None:
    simulator = WorldSimulator()

    predicted = await simulator.simulate(
        {"energy": 10.0},
        {"tool_name": "charge", "expected_outcome": "increase energy"},
    )
    discrepancy = simulator.detect_discrepancy(predicted, {"energy": 10.0})

    assert predicted.action_applied == "charge"
    assert predicted.predicted_state["energy"] == 11.0
    assert discrepancy == {"energy": {"predicted": 11.0, "actual": 10.0}}


def test_world_simulator_extracts_act_phase_output() -> None:
    trace = CycleTrace(
        cycle_id="cycle-1",
        phase_results=[
            PhaseResult(
                phase_name="ACT",
                ooda_phase="ACT",
                output={"tool_name": "search"},
            )
        ],
    )

    assert WorldSimulator().extract_last_action(trace) == {"tool_name": "search"}


@pytest.mark.asyncio
async def test_expectation_evaluator_reports_violation() -> None:
    evaluator = ExpectationEvaluator()
    evaluator.register(
        CognitiveExpectation(
            expectation_id="exp-1",
            phase_name="PLAN",
            post_condition_key="plan",
            relationship="exists",
            severity=ExpectationSeverity.CRITICAL,
        )
    )

    violations = await evaluator.evaluate_phase(
        "PLAN",
        "cycle-1",
        pre_state={},
        post_state={},
    )

    assert len(violations) == 1
    assert violations[0].expectation_id == "exp-1"
    assert violations[0].severity == ExpectationSeverity.CRITICAL


@pytest.mark.asyncio
async def test_a_distance_detector_emits_when_threshold_exceeded() -> None:
    bus = FakeEventBus()
    detector = ADistanceDetector(
        threshold=0.1,
        baseline_window=2,
        event_bus=bus,
    )

    assert await detector.observe({"a": 0.0}) is None
    assert await detector.observe({"a": 0.0}) is None
    event = await detector.observe({"a": 1.0})

    assert event is not None
    assert event.severity in {"MEDIUM", "HIGH"}
    assert bus.events[0][0] == "sakshi.anomaly.detected"


def test_anomaly_persistence_escalates_and_resets() -> None:
    tracker = AnomalyPersistenceTracker()

    first = tracker.record_anomaly("goal-1")
    second = tracker.record_anomaly("goal-1")
    tracker.record_success("goal-1")
    reset = tracker.get_escalation("goal-1")

    assert first.current_level == "MONITOR"
    assert second.current_level == "WIDEN_PRECISION"
    assert reset.current_level == "MONITOR"


def test_ambiguity_detector_flags_decision_relevant_entropy() -> None:
    report = DRFreeAmbiguityDetector().detect(
        {"refund": 0.5, "exchange": 0.5},
        ["resolve refund"],
    )

    assert report.decision_relevant is True
    assert report.epistemic_action == "seek_clarification"
    assert report.blocked_goals == ["resolve refund"]
