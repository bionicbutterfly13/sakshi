"""Tests for InterventionExecutor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sakshi.meta import (
    AlwaysPermitPolicy,
    DenyByDefaultPolicy,
    InterventionDecision,
    InterventionExecutor,
    InterventionOutcome,
)
from sakshi.models import ControlAction, ControlActionType


def _action(target: str = "planner") -> ControlAction:
    return ControlAction(
        action_type=ControlActionType.SUPPRESS_MODULE,
        target=target,
        magnitude=1.0,
        rationale="test",
    )


def test_default_executor_permits_first_call() -> None:
    executor = InterventionExecutor()
    record = executor.validate(_action())
    assert record.decision == InterventionDecision.PERMIT
    assert record.action_type == ControlActionType.SUPPRESS_MODULE


def test_cooldown_denies_second_identical_call() -> None:
    executor = InterventionExecutor(cooldown_seconds=60.0)
    t0 = datetime.now(UTC)
    first = executor.validate(_action(), now=t0)
    second = executor.validate(_action(), now=t0 + timedelta(seconds=10))
    assert first.decision == InterventionDecision.PERMIT
    assert second.decision == InterventionDecision.DENY_COOLDOWN
    assert "cooldown" in second.reason.lower()


def test_cooldown_lifts_after_window() -> None:
    executor = InterventionExecutor(cooldown_seconds=60.0)
    t0 = datetime.now(UTC)
    executor.validate(_action(), now=t0)
    later = executor.validate(_action(), now=t0 + timedelta(seconds=61))
    assert later.decision == InterventionDecision.PERMIT


def test_different_targets_do_not_share_cooldown() -> None:
    executor = InterventionExecutor(cooldown_seconds=60.0)
    t0 = datetime.now(UTC)
    a = executor.validate(_action(target="planner"), now=t0)
    b = executor.validate(_action(target="evaluator"), now=t0 + timedelta(seconds=1))
    assert a.decision == InterventionDecision.PERMIT
    assert b.decision == InterventionDecision.PERMIT


def test_policy_can_deny() -> None:
    class DenyAll:
        def is_permitted(self, action, history):
            del action, history
            return False, "test policy denies everything"

    executor = InterventionExecutor(policy=DenyAll())
    record = executor.validate(_action())
    assert record.decision == InterventionDecision.DENY_POLICY
    assert "denies" in record.reason


def test_record_outcome_updates_history() -> None:
    executor = InterventionExecutor()
    record = executor.validate(_action())
    updated = executor.record_outcome(record, InterventionOutcome.SUCCESS)
    assert updated.outcome == InterventionOutcome.SUCCESS
    assert any(r.outcome == InterventionOutcome.SUCCESS for r in executor.history)


def test_history_is_bounded() -> None:
    executor = InterventionExecutor(history_size=3, cooldown_seconds=0.0)
    t0 = datetime.now(UTC)
    for i in range(5):
        executor.validate(_action(), now=t0 + timedelta(seconds=i))
    assert len(executor.history) == 3


def test_invalid_construction() -> None:
    with pytest.raises(ValueError):
        InterventionExecutor(cooldown_seconds=-1.0)
    with pytest.raises(ValueError):
        InterventionExecutor(history_size=0)


def test_always_permit_policy_signature() -> None:
    policy = AlwaysPermitPolicy()
    permitted, reason = policy.is_permitted(_action(), [])
    assert permitted is True
    assert "default policy" in reason


def test_deny_by_default_policy_denies_until_host_policy_is_supplied() -> None:
    executor = InterventionExecutor(policy=DenyByDefaultPolicy())

    record = executor.validate(_action())

    assert record.decision == InterventionDecision.DENY_POLICY
    assert "deny until host permission policy is supplied" in record.reason
