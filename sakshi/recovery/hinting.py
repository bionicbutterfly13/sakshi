"""Operational failure-to-recovery hinting.

Classifies concrete runtime error strings into operational ``FailureType``
values and emits typed ``RecoveryAction`` recommendations. The host owns each
``StrategyHinter`` instance and therefore owns attempt tracking, custom strategy
registration, and lifecycle.

This layer is distinct from ``sakshi.interpret.trap``: TRAP classifies declared
cognitive failure modes, while recovery recommends what an agent loop can do
with a runtime failure in hand.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

logger = logging.getLogger(__name__)


class FailureType(StrEnum):
    """Categories of recoverable operational failures."""

    TIMEOUT = "timeout"
    EMPTY_RESULTS = "empty_results"
    PARSE_ERROR = "parse_error"
    RATE_LIMIT = "rate_limit"
    CONNECTION_ERROR = "connection_error"
    TOOL_ERROR = "tool_error"
    MODEL_ERROR = "model_error"
    BRIDGE_FAILURE = "bridge_failure"


class RecoveryAction(StrEnum):
    """Recovery actions a host agent loop can consider."""

    RETRY_SAME = "retry_same"
    RETRY_PROMOTED = "retry_promoted"
    BROADEN_QUERY = "broaden_query"
    FALLBACK_TOOL = "fallback_tool"
    INCREASE_BUDGET = "increase_budget"
    REDUCE_SCOPE = "reduce_scope"
    LOCAL_ONLY = "local_only"
    SKIP_AND_LOG = "skip_and_log"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RecoveryStrategy:
    """A bounded recovery strategy for one operational failure type."""

    failure_type: FailureType
    action: RecoveryAction
    hint_template: str
    priority: int = 0
    max_attempts: int = 2
    cooldown_seconds: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


_DEFAULT_STRATEGIES: dict[FailureType, tuple[RecoveryStrategy, ...]] = {
    FailureType.TIMEOUT: (
        RecoveryStrategy(
            failure_type=FailureType.TIMEOUT,
            action=RecoveryAction.RETRY_PROMOTED,
            hint_template="Previous attempt timed out. Retrying with enhanced model.",
            priority=10,
            max_attempts=2,
            cooldown_seconds=2.0,
        ),
        RecoveryStrategy(
            failure_type=FailureType.TIMEOUT,
            action=RecoveryAction.REDUCE_SCOPE,
            hint_template=(
                "Timeout occurred. Try a more specific, smaller task or use "
                "a simpler tool."
            ),
            priority=5,
        ),
    ),
    FailureType.EMPTY_RESULTS: (
        RecoveryStrategy(
            failure_type=FailureType.EMPTY_RESULTS,
            action=RecoveryAction.BROADEN_QUERY,
            hint_template="No results found. Broadening search to related concepts.",
            priority=10,
            max_attempts=1,
        ),
        RecoveryStrategy(
            failure_type=FailureType.EMPTY_RESULTS,
            action=RecoveryAction.FALLBACK_TOOL,
            hint_template=(
                "Semantic search returned no results. Try a broader conceptual lookup."
            ),
            priority=5,
            metadata={"fallback_tool": "conceptual_lookup"},
        ),
    ),
    FailureType.PARSE_ERROR: (
        RecoveryStrategy(
            failure_type=FailureType.PARSE_ERROR,
            action=RecoveryAction.RETRY_SAME,
            hint_template=(
                "Output format was invalid. Retry with an explicit format request."
            ),
            priority=10,
            max_attempts=2,
        ),
        RecoveryStrategy(
            failure_type=FailureType.PARSE_ERROR,
            action=RecoveryAction.RETRY_PROMOTED,
            hint_template="Parsing still fails. Consider a more capable model.",
            priority=5,
        ),
    ),
    FailureType.RATE_LIMIT: (
        RecoveryStrategy(
            failure_type=FailureType.RATE_LIMIT,
            action=RecoveryAction.RETRY_SAME,
            hint_template="Rate limited. Wait before retrying.",
            priority=10,
            cooldown_seconds=5.0,
            max_attempts=3,
        ),
    ),
    FailureType.CONNECTION_ERROR: (
        RecoveryStrategy(
            failure_type=FailureType.CONNECTION_ERROR,
            action=RecoveryAction.RETRY_SAME,
            hint_template="Connection failed. Retry with backoff.",
            priority=10,
            cooldown_seconds=2.0,
            max_attempts=3,
        ),
    ),
    FailureType.TOOL_ERROR: (
        RecoveryStrategy(
            failure_type=FailureType.TOOL_ERROR,
            action=RecoveryAction.FALLBACK_TOOL,
            hint_template="Tool execution failed. Consider an alternative approach.",
            priority=10,
        ),
        RecoveryStrategy(
            failure_type=FailureType.TOOL_ERROR,
            action=RecoveryAction.SKIP_AND_LOG,
            hint_template="Tool unavailable. Continue without this data source.",
            priority=5,
        ),
    ),
    FailureType.MODEL_ERROR: (
        RecoveryStrategy(
            failure_type=FailureType.MODEL_ERROR,
            action=RecoveryAction.RETRY_PROMOTED,
            hint_template="Model error occurred. Consider a fallback model.",
            priority=10,
        ),
    ),
    FailureType.BRIDGE_FAILURE: (
        RecoveryStrategy(
            failure_type=FailureType.BRIDGE_FAILURE,
            action=RecoveryAction.LOCAL_ONLY,
            hint_template=(
                "Tool bridge is unstable. Fall back to local reasoning or tools."
            ),
            priority=10,
        ),
    ),
}

RECOVERY_STRATEGIES: Mapping[FailureType, tuple[RecoveryStrategy, ...]] = (
    MappingProxyType(_DEFAULT_STRATEGIES)
)


def get_strategies_for_failure(
    failure_type: FailureType,
    strategies: Mapping[FailureType, Sequence[RecoveryStrategy]] | None = None,
) -> list[RecoveryStrategy]:
    """Return strategies for a failure type, highest priority first."""
    source = RECOVERY_STRATEGIES if strategies is None else strategies
    return sorted(
        source.get(failure_type, ()), key=lambda item: item.priority, reverse=True
    )


class StrategyHinter:
    """Generate recovery hints with host-owned strategy and attempt state."""

    def __init__(
        self,
        strategies: Mapping[FailureType, Sequence[RecoveryStrategy]] | None = None,
    ) -> None:
        source = RECOVERY_STRATEGIES if strategies is None else strategies
        self._strategies = {
            failure_type: list(items) for failure_type, items in source.items()
        }
        self._attempt_counts: dict[tuple[str, FailureType, int], int] = {}

    def register_strategy(self, strategy: RecoveryStrategy) -> None:
        """Register a strategy on this hinter instance."""
        self._strategies.setdefault(strategy.failure_type, []).append(strategy)
        logger.info(
            "Registered recovery strategy: %s for %s",
            strategy.action.value,
            strategy.failure_type.value,
        )

    def get_strategies(self, failure_type: FailureType) -> list[RecoveryStrategy]:
        """Return this instance's strategies in priority order."""
        return get_strategies_for_failure(failure_type, self._strategies)

    def classify_error(self, error_msg: str) -> FailureType:
        """Classify an error message into a ``FailureType``."""
        error_upper = error_msg.upper()

        if "TIMEOUT" in error_upper or "TIMED OUT" in error_upper:
            return FailureType.TIMEOUT
        if (
            "EMPTY" in error_upper
            or "NO RESULTS" in error_upper
            or "NOT FOUND" in error_upper
        ):
            return FailureType.EMPTY_RESULTS
        if "JSON" in error_upper or "PARSE" in error_upper or "FORMAT" in error_upper:
            return FailureType.PARSE_ERROR
        if "RATE" in error_upper or "429" in error_upper or "LIMIT" in error_upper:
            return FailureType.RATE_LIMIT
        if "BRIDGE" in error_upper or "MCP" in error_upper:
            return FailureType.BRIDGE_FAILURE
        if (
            "CONNECTION" in error_upper
            or "NETWORK" in error_upper
            or "SOCKET" in error_upper
        ):
            return FailureType.CONNECTION_ERROR
        if "MODEL" in error_upper or "LLM" in error_upper:
            return FailureType.MODEL_ERROR
        return FailureType.TOOL_ERROR

    def get_hint(
        self,
        error_or_type: str | FailureType,
        context: Mapping[str, Any] | None = None,
        task_id: str = "default",
    ) -> str:
        """Return the next recovery hint for a task and failure."""
        failure_type = (
            self.classify_error(error_or_type)
            if isinstance(error_or_type, str)
            else error_or_type
        )

        for strategy in self.get_strategies(failure_type):
            attempt_key = (task_id, failure_type, id(strategy))
            attempts = self._attempt_counts.get(attempt_key, 0)
            if attempts >= strategy.max_attempts:
                continue

            self._attempt_counts[attempt_key] = attempts + 1
            hint = strategy.hint_template
            if context:
                hint = self._enrich_hint(hint, context, strategy)

            logger.info(
                "StrategyHinter: %s -> %s (attempt %d/%d)",
                failure_type.value,
                strategy.action.value,
                attempts + 1,
                strategy.max_attempts,
            )
            return f"RECOVERY_HINT: {hint} Strategy: {strategy.action.value.upper()}"

        logger.warning("StrategyHinter: no more strategies for %s", failure_type.value)
        return "RECOVERY_HINT: All recovery strategies exhausted. Escalate to the host."

    def _enrich_hint(
        self,
        hint: str,
        context: Mapping[str, Any],
        strategy: RecoveryStrategy,
    ) -> str:
        enrichments: list[str] = []

        if strategy.action == RecoveryAction.BROADEN_QUERY and "query" in context:
            enrichments.append(f"Original query: '{context['query']}'")
            enrichments.append("Try removing specific terms or using related concepts.")

        if (
            strategy.action == RecoveryAction.FALLBACK_TOOL
            and "fallback_tool" in strategy.metadata
        ):
            enrichments.append(f"Suggested tool: {strategy.metadata['fallback_tool']}")

        return f"{hint} {' '.join(enrichments)}" if enrichments else hint

    def reset_attempts(self, task_id: str = "default") -> None:
        """Reset all attempt counts associated with one host task."""
        keys_to_remove = [key for key in self._attempt_counts if key[0] == task_id]
        for key in keys_to_remove:
            del self._attempt_counts[key]

    def get_strategy_action(
        self,
        failure_type: FailureType,
        task_id: str = "default",
    ) -> RecoveryAction:
        """Return the next action without consuming an attempt."""
        for strategy in self.get_strategies(failure_type):
            attempt_key = (task_id, failure_type, id(strategy))
            if self._attempt_counts.get(attempt_key, 0) < strategy.max_attempts:
                return strategy.action
        return RecoveryAction.ESCALATE


_ERROR_PATTERNS: tuple[str, ...] = (
    "error",
    "failed",
    "timeout",
    "exception",
    "not found",
    "empty",
)


def wrap_with_resilience(
    observation: Any,
    task_id: str = "default",
    *,
    hinter: StrategyHinter | None = None,
) -> Any:
    """Append a recovery hint when a tool observation looks like a failure."""
    obs_str = str(observation)
    if not any(pattern in obs_str.lower() for pattern in _ERROR_PATTERNS):
        return observation

    active_hinter = StrategyHinter() if hinter is None else hinter
    hint = active_hinter.get_hint(obs_str, task_id=task_id)
    return f"{obs_str}\n\n{hint}"


def hint_for_timeout(
    context: Mapping[str, Any] | None = None,
    task_id: str = "default",
    *,
    hinter: StrategyHinter | None = None,
) -> str:
    """Return a timeout recovery hint."""
    active_hinter = StrategyHinter() if hinter is None else hinter
    return active_hinter.get_hint(FailureType.TIMEOUT, context, task_id)


def hint_for_empty_results(
    context: Mapping[str, Any] | None = None,
    task_id: str = "default",
    *,
    hinter: StrategyHinter | None = None,
) -> str:
    """Return an empty-results recovery hint."""
    active_hinter = StrategyHinter() if hinter is None else hinter
    return active_hinter.get_hint(FailureType.EMPTY_RESULTS, context, task_id)


def hint_for_parse_error(
    context: Mapping[str, Any] | None = None,
    task_id: str = "default",
    *,
    hinter: StrategyHinter | None = None,
) -> str:
    """Return a parse-error recovery hint."""
    active_hinter = StrategyHinter() if hinter is None else hinter
    return active_hinter.get_hint(FailureType.PARSE_ERROR, context, task_id)


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
