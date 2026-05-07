"""Defensive guards.

Two typed validation seams the meta-layer uses to defend against
classic failure modes:

* ``RewardIntegrityGuard`` — a goal achievement claim only counts if
  the host can show *exogenous evidence* that the world actually
  changed. The guard rejects unsupported claims, blocking the
  pattern where an agent silently records "goal achieved" without
  the world having moved.
* ``ModificationIntegrityGuard`` — when a self-modifying agent wants
  to drop or relax a `GoalConstraint`, the guard refuses if the
  constraint is flagged ``integrity_critical=True``.

Both guards are protocols with default reference implementations.
Hosts plug their own implementations when they have richer evidence
or modification-policy logic.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from sakshi.plans.constraint import GoalConstraint


class GuardDecision(StrEnum):
    """Result of one guard check."""

    PERMIT = "permit"
    DENY = "deny"


@dataclass(frozen=True)
class GuardVerdict:
    """Typed verdict returned by every guard."""

    decision: GuardDecision
    reason: str = ""
    evidence_count: int = 0
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def permitted(self) -> bool:
        return self.decision == GuardDecision.PERMIT


@runtime_checkable
class RewardIntegrityGuard(Protocol):
    """Validate a goal-achievement claim against exogenous evidence."""

    def validate_achievement(
        self,
        *,
        goal_id: str,
        evidence_keys: Iterable[str],
    ) -> GuardVerdict: ...


class EvidenceRequiringRewardIntegrityGuard:
    """Default: require at least one evidence key to permit achievement.

    The host accumulates an evidence set per goal (sensor readings
    that confirm the post-condition, completed tool calls, observed
    state-change events) and passes the keys to ``validate_achievement``.
    The default guard permits when at least ``min_evidence`` keys are
    present.

    Hosts wanting richer logic (signature verification, redundant
    confirmations, time-window checks) supply a custom implementation
    of the protocol.
    """

    def __init__(self, *, min_evidence: int = 1) -> None:
        if min_evidence < 1:
            raise ValueError("min_evidence must be at least 1")
        self._min_evidence = min_evidence

    def validate_achievement(
        self,
        *,
        goal_id: str,
        evidence_keys: Iterable[str],
    ) -> GuardVerdict:
        keys = tuple(evidence_keys)
        if len(keys) >= self._min_evidence:
            return GuardVerdict(
                decision=GuardDecision.PERMIT,
                reason=(
                    f"goal {goal_id!r}: {len(keys)} exogenous evidence "
                    f"key(s) >= required {self._min_evidence}"
                ),
                evidence_count=len(keys),
            )
        return GuardVerdict(
            decision=GuardDecision.DENY,
            reason=(
                f"goal {goal_id!r}: only {len(keys)} exogenous evidence "
                f"key(s); refusing to record achievement without at "
                f"least {self._min_evidence}"
            ),
            evidence_count=len(keys),
        )


@runtime_checkable
class ModificationIntegrityGuard(Protocol):
    """Validate a proposed plan/goal rewrite against existing constraints."""

    def validate_modification(
        self,
        *,
        before: GoalConstraint,
        after: GoalConstraint,
    ) -> GuardVerdict: ...


class IntegrityCriticalModificationGuard:
    """Default: refuse to drop or relax constraints flagged critical.

    Specifically:

    * If ``before.integrity_critical`` is True and ``after.integrity_critical``
      becomes False, deny — the host is trying to demote a critical
      constraint.
    * If ``before.integrity_critical`` is True and any safety constraint
      from ``before.safety_constraints`` is missing from
      ``after.safety_constraints``, deny.

    All other modifications are permitted. Hosts wanting tighter
    rules (require an audit signature, require a quorum, require
    operator approval) supply their own protocol implementation.
    """

    def validate_modification(
        self,
        *,
        before: GoalConstraint,
        after: GoalConstraint,
    ) -> GuardVerdict:
        if not before.integrity_critical:
            return GuardVerdict(
                decision=GuardDecision.PERMIT,
                reason="constraint not flagged integrity_critical",
            )
        if not after.integrity_critical:
            return GuardVerdict(
                decision=GuardDecision.DENY,
                reason=(
                    "modification would demote integrity_critical "
                    "constraint to non-critical"
                ),
            )
        before_set = set(before.safety_constraints)
        after_set = set(after.safety_constraints)
        dropped = before_set - after_set
        if dropped:
            return GuardVerdict(
                decision=GuardDecision.DENY,
                reason=(
                    "modification would drop safety constraint(s) "
                    f"{sorted(dropped)} from integrity_critical "
                    "constraint"
                ),
            )
        return GuardVerdict(
            decision=GuardDecision.PERMIT,
            reason=(
                "modification preserves all safety constraints on "
                "integrity_critical constraint"
            ),
        )


class KnowledgeRewardBalance(StrEnum):
    """Host-declared preference between learning and reward.

    * ``KNOWLEDGE`` — prefer information-gathering goals; tolerate
      lower immediate reward.
    * ``REWARD`` — prefer reward-maximizing goals; tolerate lower
      information gain.
    * ``HYBRID`` — accept either; let the host's selector decide.
    """

    KNOWLEDGE = "knowledge"
    REWARD = "reward"
    HYBRID = "hybrid"


def biases_against_exploration(balance: KnowledgeRewardBalance) -> bool:
    """Return whether this preference biases away from exploration.

    Convenience predicate hosts use when deciding whether to suppress
    a curiosity-motivated goal because the agent's budget is
    exhausted and it should be exploiting.
    """
    return balance == KnowledgeRewardBalance.REWARD


def biases_toward_exploration(
    balance: KnowledgeRewardBalance,
) -> bool:
    """Return whether this preference biases toward exploration."""
    return balance == KnowledgeRewardBalance.KNOWLEDGE


@dataclass(frozen=True)
class GuardAuditRecord:
    """One immutable record of a guard decision.

    Hosts that want a unified audit log across both guards can
    construct these from any ``GuardVerdict`` and stream them through
    their own event bus or storage.
    """

    guard_name: str
    target: str
    verdict: GuardVerdict
    metadata: tuple[tuple[str, str], ...] = ()


def make_audit_record(
    guard_name: str,
    target: str,
    verdict: GuardVerdict,
    metadata: dict[str, Any] | None = None,
) -> GuardAuditRecord:
    """Build a frozen audit record from a guard verdict."""
    metadata_tuple: tuple[tuple[str, str], ...] = ()
    if metadata:
        metadata_tuple = tuple(
            (str(k), str(v)) for k, v in sorted(metadata.items())
        )
    return GuardAuditRecord(
        guard_name=guard_name,
        target=target,
        verdict=verdict,
        metadata=metadata_tuple,
    )


__all__ = [
    "EvidenceRequiringRewardIntegrityGuard",
    "GuardAuditRecord",
    "GuardDecision",
    "GuardVerdict",
    "IntegrityCriticalModificationGuard",
    "KnowledgeRewardBalance",
    "ModificationIntegrityGuard",
    "RewardIntegrityGuard",
    "biases_against_exploration",
    "biases_toward_exploration",
    "make_audit_record",
]
