from __future__ import annotations

import pytest

from sakshi.plans import PlanDeviationTracker, PlanSoundnessVerifier


def test_plan_soundness_verifier_detects_precondition_order_and_resource_errors() -> (
    None
):
    result = PlanSoundnessVerifier().verify(
        [
            {
                "step_id": "second",
                "preconditions": ["ready"],
                "must_follow": "first",
                "resources": {"energy": 2.0},
            },
            {
                "step_id": "first",
                "resources": {"energy": 2.0},
            },
        ],
        world_state={"ready": False},
        available_resources={"energy": 3.0},
    )

    assert result.is_sound is False
    assert "second" in result.blocked_steps
    assert "first" in result.blocked_steps
    assert result.confidence == 0.0
    assert any("precondition" in violation for violation in result.violations)
    assert any("ordering" in violation for violation in result.violations)
    assert any("resource" in violation for violation in result.violations)


def test_plan_soundness_verifier_accepts_empty_and_valid_plans() -> None:
    verifier = PlanSoundnessVerifier()

    assert verifier.verify([]).is_sound is True
    valid = verifier.verify(
        [
            {"step_id": "first", "preconditions": ["ready"]},
            {"step_id": "second", "must_follow": "first"},
        ],
        world_state={"ready": True},
    )

    assert valid.is_sound is True
    assert valid.violations == []
    assert valid.confidence == 1.0


def test_plan_deviation_tracker_records_and_triggers_once() -> None:
    tracker = PlanDeviationTracker(deviation_threshold=0.3)
    tracker.set_reference_plan(["search", "summarize", "write"])

    assert tracker.record_action("search") is None
    first_deviation = tracker.record_action("browse")
    second_deviation = tracker.record_action("draft")

    assert first_deviation is not None
    assert first_deviation.deviation_score == 1.0
    assert second_deviation is not None
    assert tracker.get_deviation_ratio() == pytest.approx(2 / 3)
    assert tracker.should_replan() is True
    assert tracker.should_replan() is False


@pytest.mark.asyncio
async def test_plan_deviation_tracker_learning_signal_adjusts_threshold() -> None:
    tracker = PlanDeviationTracker(deviation_threshold=0.3)

    await tracker.on_learning_signal({"strength_label": "strong"})
    strong_threshold = tracker.dynamic_threshold
    await tracker.on_learning_signal({"strength_label": "weak"})

    assert strong_threshold == pytest.approx(0.27)
    assert tracker.dynamic_threshold > strong_threshold
