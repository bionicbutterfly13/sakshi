"""Operational failure-to-recovery hinting for agent loops.

Classifies runtime error strings into operational ``FailureType`` values and
emits typed ``RecoveryAction`` hints. Distinct from — and complementary to —
the cognitive TRAP failure taxonomy in ``sakshi.interpret.trap``; see
``sakshi.recovery.hinting`` for the full relationship.
"""

from __future__ import annotations

from sakshi.recovery.hinting import (
    RECOVERY_STRATEGIES,
    FailureType,
    RecoveryAction,
    RecoveryStrategy,
    StrategyHinter,
    get_strategies_for_failure,
    hint_for_empty_results,
    hint_for_parse_error,
    hint_for_timeout,
    wrap_with_resilience,
)

__all__ = [
    "RECOVERY_STRATEGIES",
    "FailureType",
    "RecoveryAction",
    "RecoveryStrategy",
    "StrategyHinter",
    "get_strategies_for_failure",
    "hint_for_empty_results",
    "hint_for_parse_error",
    "hint_for_timeout",
    "wrap_with_resilience",
]
