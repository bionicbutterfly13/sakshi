"""Tests for the Phase F defensive guards."""

from __future__ import annotations

import pytest

from sakshi.meta import (
    EvidenceRequiringRewardIntegrityGuard,
    GuardDecision,
    GuardVerdict,
    IntegrityCriticalModificationGuard,
    KnowledgeRewardBalance,
    ModificationIntegrityGuard,
    RewardIntegrityGuard,
    biases_against_exploration,
    biases_toward_exploration,
    make_audit_record,
)
from sakshi.plans import GoalConstraint


def test_reward_guard_protocol_runtime_check() -> None:
    guard = EvidenceRequiringRewardIntegrityGuard()
    assert isinstance(guard, RewardIntegrityGuard)


def test_reward_guard_permits_with_evidence() -> None:
    guard = EvidenceRequiringRewardIntegrityGuard(min_evidence=1)
    verdict = guard.validate_achievement(goal_id="g-1", evidence_keys=("sensor:cam_1",))
    assert verdict.decision == GuardDecision.PERMIT
    assert verdict.evidence_count == 1


def test_reward_guard_denies_without_evidence() -> None:
    guard = EvidenceRequiringRewardIntegrityGuard(min_evidence=1)
    verdict = guard.validate_achievement(goal_id="g-1", evidence_keys=())
    assert verdict.decision == GuardDecision.DENY
    assert verdict.evidence_count == 0
    assert "exogenous evidence" in verdict.reason


def test_reward_guard_higher_threshold() -> None:
    guard = EvidenceRequiringRewardIntegrityGuard(min_evidence=2)
    one = guard.validate_achievement(goal_id="g-1", evidence_keys=("a",))
    two = guard.validate_achievement(goal_id="g-1", evidence_keys=("a", "b"))
    assert one.decision == GuardDecision.DENY
    assert two.decision == GuardDecision.PERMIT


def test_reward_guard_requires_named_evidence_keys() -> None:
    guard = EvidenceRequiringRewardIntegrityGuard(
        min_evidence=1,
        required_evidence_keys=("tool:completed", "state:changed"),
    )
    missing = guard.validate_achievement(
        goal_id="g-1",
        evidence_keys=("tool:completed",),
    )
    present = guard.validate_achievement(
        goal_id="g-1",
        evidence_keys=("tool:completed", "state:changed"),
    )
    assert missing.decision == GuardDecision.DENY
    assert "state:changed" in missing.reason
    assert present.decision == GuardDecision.PERMIT


def test_reward_guard_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        EvidenceRequiringRewardIntegrityGuard(min_evidence=0)


def test_modification_guard_protocol_check() -> None:
    guard = IntegrityCriticalModificationGuard()
    assert isinstance(guard, ModificationIntegrityGuard)


def test_modification_guard_permits_non_critical() -> None:
    guard = IntegrityCriticalModificationGuard()
    before = GoalConstraint(integrity_critical=False)
    after = GoalConstraint(integrity_critical=False)
    verdict = guard.validate_modification(before=before, after=after)
    assert verdict.decision == GuardDecision.PERMIT


def test_modification_guard_denies_demotion() -> None:
    guard = IntegrityCriticalModificationGuard()
    before = GoalConstraint(integrity_critical=True)
    after = GoalConstraint(integrity_critical=False)
    verdict = guard.validate_modification(before=before, after=after)
    assert verdict.decision == GuardDecision.DENY
    assert "demote" in verdict.reason


def test_modification_guard_denies_dropping_safety_constraint() -> None:
    guard = IntegrityCriticalModificationGuard()
    before = GoalConstraint(
        safety_constraints=("not on_fire(*)", "not collision(*)"),
        integrity_critical=True,
    )
    after = GoalConstraint(
        safety_constraints=("not on_fire(*)",),
        integrity_critical=True,
    )
    verdict = guard.validate_modification(before=before, after=after)
    assert verdict.decision == GuardDecision.DENY
    assert "not collision(*)" in verdict.reason


def test_modification_guard_permits_added_safety_constraint() -> None:
    guard = IntegrityCriticalModificationGuard()
    before = GoalConstraint(
        safety_constraints=("not on_fire(*)",),
        integrity_critical=True,
    )
    after = GoalConstraint(
        safety_constraints=("not on_fire(*)", "not collision(*)"),
        integrity_critical=True,
    )
    verdict = guard.validate_modification(before=before, after=after)
    assert verdict.decision == GuardDecision.PERMIT


def test_knowledge_reward_balance_predicates() -> None:
    assert biases_toward_exploration(KnowledgeRewardBalance.KNOWLEDGE)
    assert not biases_toward_exploration(KnowledgeRewardBalance.REWARD)
    assert biases_against_exploration(KnowledgeRewardBalance.REWARD)
    assert not biases_against_exploration(KnowledgeRewardBalance.HYBRID)


def test_make_audit_record() -> None:
    verdict = GuardVerdict(decision=GuardDecision.PERMIT, reason="ok")
    record = make_audit_record(
        "RewardIntegrityGuard",
        "g-1",
        verdict,
        metadata={"source": "test", "operator": "alice"},
    )
    assert record.guard_name == "RewardIntegrityGuard"
    assert record.target == "g-1"
    assert record.verdict.permitted is True
    assert ("operator", "alice") in record.metadata
    assert ("source", "test") in record.metadata


def test_verdict_permitted_property() -> None:
    p = GuardVerdict(decision=GuardDecision.PERMIT)
    d = GuardVerdict(decision=GuardDecision.DENY)
    assert p.permitted is True
    assert d.permitted is False
