"""Tests for operational failure-to-recovery hinting (``sakshi.recovery``)."""

from __future__ import annotations

import pytest

from sakshi.recovery import (
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


class TestFailureTypeClassification:
    """Tests for error message classification."""

    def test_classify_timeout(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("Operation timed out") == FailureType.TIMEOUT
        assert hinter.classify_error("TIMEOUT after 30s") == FailureType.TIMEOUT

    def test_classify_empty_results(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("No results found") == FailureType.EMPTY_RESULTS
        assert hinter.classify_error("Empty response") == FailureType.EMPTY_RESULTS
        assert hinter.classify_error("Entity not found") == FailureType.EMPTY_RESULTS

    def test_classify_parse_error(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("JSON parsing failed") == FailureType.PARSE_ERROR
        assert hinter.classify_error("Invalid format") == FailureType.PARSE_ERROR

    def test_classify_rate_limit(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("Rate limit exceeded") == FailureType.RATE_LIMIT
        assert hinter.classify_error("HTTP 429") == FailureType.RATE_LIMIT

    def test_classify_connection_error(self) -> None:
        hinter = StrategyHinter()
        assert (
            hinter.classify_error("Connection refused") == FailureType.CONNECTION_ERROR
        )
        assert hinter.classify_error("Network error") == FailureType.CONNECTION_ERROR

    def test_classify_bridge_failure(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("MCP bridge error") == FailureType.BRIDGE_FAILURE
        assert (
            hinter.classify_error("Bridge connection failed")
            == FailureType.BRIDGE_FAILURE
        )

    def test_classify_unknown_defaults_to_tool_error(self) -> None:
        hinter = StrategyHinter()
        assert hinter.classify_error("Some random error") == FailureType.TOOL_ERROR


class TestStrategyHinter:
    """Tests for hint generation and host-owned attempt state."""

    def test_get_hint_for_timeout(self) -> None:
        hinter = StrategyHinter()
        hint = hinter.get_hint(FailureType.TIMEOUT, task_id="test-1")
        assert "RECOVERY_HINT:" in hint
        assert "timed out" in hint.lower() or "timeout" in hint.lower()

    def test_get_hint_for_empty_results_suggests_broaden(self) -> None:
        hinter = StrategyHinter()
        hint = hinter.get_hint(FailureType.EMPTY_RESULTS, task_id="test-search")
        assert "RECOVERY_HINT:" in hint
        assert "BROADEN_QUERY" in hint or "broaden" in hint.lower()

    def test_get_hint_with_context_enrichment(self) -> None:
        hinter = StrategyHinter()
        hint = hinter.get_hint(
            FailureType.EMPTY_RESULTS,
            context={"query": "specific technical term"},
            task_id="test-context",
        )
        assert "specific technical term" in hint
        assert "related concepts" in hint.lower()

    def test_attempt_tracking_reaches_later_strategy(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-escalation"

        assert "RETRY_PROMOTED" in hinter.get_hint(FailureType.TIMEOUT, task_id=task_id)
        assert "RETRY_PROMOTED" in hinter.get_hint(FailureType.TIMEOUT, task_id=task_id)
        assert "REDUCE_SCOPE" in hinter.get_hint(FailureType.TIMEOUT, task_id=task_id)

    def test_reset_attempts(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-reset"

        hinter.get_hint(FailureType.EMPTY_RESULTS, task_id=task_id)
        assert "FALLBACK_TOOL" in hinter.get_hint(
            FailureType.EMPTY_RESULTS, task_id=task_id
        )

        hinter.reset_attempts(task_id)

        assert "BROADEN_QUERY" in hinter.get_hint(
            FailureType.EMPTY_RESULTS, task_id=task_id
        )

    def test_get_hint_from_error_string(self) -> None:
        hinter = StrategyHinter()
        hint = hinter.get_hint(
            "Operation timed out after 30 seconds",
            task_id="test-str",
        )
        assert "RECOVERY_HINT:" in hint
        assert "timeout" in hint.lower() or "RETRY" in hint

    def test_all_strategies_exhausted(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-exhausted"

        hint = ""
        for _ in range(10):
            hint = hinter.get_hint(FailureType.PARSE_ERROR, task_id=task_id)

        assert "exhausted" in hint.lower()
        assert "host" in hint.lower()

    def test_task_state_is_bounded_and_evicts_oldest(self) -> None:
        hinter = StrategyHinter(max_tracked_tasks=2)

        hinter.get_hint(FailureType.EMPTY_RESULTS, task_id="oldest")
        hinter.get_hint(FailureType.EMPTY_RESULTS, task_id="newer")
        hinter.get_hint(FailureType.EMPTY_RESULTS, task_id="newest")

        hint = hinter.get_hint(FailureType.EMPTY_RESULTS, task_id="oldest")
        assert "BROADEN_QUERY" in hint

    def test_rejects_invalid_task_bound(self) -> None:
        with pytest.raises(ValueError, match="max_tracked_tasks"):
            StrategyHinter(max_tracked_tasks=0)


class TestGetStrategyAction:
    """Tests for non-consuming action inspection."""

    def test_get_action_does_not_consume_attempt(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-action"

        first = hinter.get_strategy_action(FailureType.TIMEOUT, task_id=task_id)
        second = hinter.get_strategy_action(FailureType.TIMEOUT, task_id=task_id)

        assert first == RecoveryAction.RETRY_PROMOTED
        assert second == RecoveryAction.RETRY_PROMOTED

    def test_action_advances_after_strategy_budget(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-action-advance"

        hinter.get_hint(FailureType.EMPTY_RESULTS, task_id=task_id)

        action = hinter.get_strategy_action(
            FailureType.EMPTY_RESULTS,
            task_id=task_id,
        )
        assert action == RecoveryAction.FALLBACK_TOOL

    def test_action_escalates_after_all_strategies(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-action-exhaust"

        for _ in range(10):
            hinter.get_hint(FailureType.MODEL_ERROR, task_id=task_id)

        action = hinter.get_strategy_action(FailureType.MODEL_ERROR, task_id=task_id)
        assert action == RecoveryAction.ESCALATE


class TestWrapWithResilience:
    """Tests for appending hints to failure observations."""

    def test_wrap_error_observation(self) -> None:
        observation = "Error: Connection failed to database"
        wrapped = wrap_with_resilience(observation, task_id="test-wrap")
        assert "Error: Connection failed" in wrapped
        assert "RECOVERY_HINT:" in wrapped

    def test_wrap_success_observation_unchanged(self) -> None:
        observation = "Successfully retrieved 5 results"
        wrapped = wrap_with_resilience(observation, task_id="test-success")
        assert wrapped == observation
        assert "RECOVERY_HINT" not in wrapped

    def test_wrap_uses_host_hinter_state(self) -> None:
        hinter = StrategyHinter()
        observation = "Search returned empty results"

        first = wrap_with_resilience(
            observation,
            task_id="test-empty",
            hinter=hinter,
        )
        second = wrap_with_resilience(
            observation,
            task_id="test-empty",
            hinter=hinter,
        )

        assert "BROADEN_QUERY" in first
        assert "FALLBACK_TOOL" in second


class TestConvenienceFunctions:
    """Tests for convenience hint functions."""

    def test_hint_for_timeout(self) -> None:
        assert "RECOVERY_HINT:" in hint_for_timeout(task_id="test-conv-timeout")

    def test_hint_for_empty_results(self) -> None:
        assert "RECOVERY_HINT:" in hint_for_empty_results(task_id="test-conv-empty")

    def test_hint_for_parse_error(self) -> None:
        assert "RECOVERY_HINT:" in hint_for_parse_error(task_id="test-conv-parse")

    def test_convenience_functions_accept_host_hinter(self) -> None:
        hinter = StrategyHinter()
        task_id = "test-conv-state"

        first = hint_for_empty_results(task_id=task_id, hinter=hinter)
        second = hint_for_empty_results(task_id=task_id, hinter=hinter)

        assert "BROADEN_QUERY" in first
        assert "FALLBACK_TOOL" in second

    def test_convenience_functions_are_stateless_without_hinter(self) -> None:
        task_id = "test-conv-stateless"

        first = hint_for_empty_results(task_id=task_id)
        second = hint_for_empty_results(task_id=task_id)

        assert "BROADEN_QUERY" in first
        assert "BROADEN_QUERY" in second


class TestRecoveryStrategyRegistry:
    """Tests for immutable defaults and instance-local customization."""

    def test_get_strategies_sorted_by_priority(self) -> None:
        strategies = get_strategies_for_failure(FailureType.TIMEOUT)
        assert len(strategies) >= 2
        assert strategies == sorted(
            strategies,
            key=lambda strategy: strategy.priority,
            reverse=True,
        )

    def test_default_registry_is_immutable(self) -> None:
        with pytest.raises(TypeError):
            RECOVERY_STRATEGIES[FailureType.TIMEOUT] = ()  # type: ignore[index]

    def test_register_custom_strategy_on_one_instance(self) -> None:
        custom = RecoveryStrategy(
            failure_type=FailureType.TOOL_ERROR,
            action=RecoveryAction.SKIP_AND_LOG,
            hint_template="Custom: Skip this tool and continue.",
            priority=100,
        )
        customized = StrategyHinter()
        untouched = StrategyHinter()

        customized.register_strategy(custom)

        assert customized.get_strategies(FailureType.TOOL_ERROR)[0] == custom
        assert untouched.get_strategies(FailureType.TOOL_ERROR)[0] != custom
        assert get_strategies_for_failure(FailureType.TOOL_ERROR)[0] != custom

    def test_late_registration_has_independent_attempt_budget(self) -> None:
        hinter = StrategyHinter()
        task_id = "late-registration"
        hinter.get_hint(FailureType.TOOL_ERROR, task_id=task_id)
        custom = RecoveryStrategy(
            failure_type=FailureType.TOOL_ERROR,
            action=RecoveryAction.ESCALATE,
            hint_template="Escalate this tool failure.",
            priority=100,
            max_attempts=1,
        )

        hinter.register_strategy(custom)

        assert (
            hinter.get_strategy_action(FailureType.TOOL_ERROR, task_id=task_id)
            == RecoveryAction.ESCALATE
        )
        assert "ESCALATE" in hinter.get_hint(
            FailureType.TOOL_ERROR,
            task_id=task_id,
        )

    def test_all_failure_types_have_strategies(self) -> None:
        for failure_type in FailureType:
            strategies = get_strategies_for_failure(failure_type)
            assert strategies, f"No strategies for {failure_type.value}"

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"max_attempts": 0}, "max_attempts"),
            ({"cooldown_seconds": -1.0}, "cooldown_seconds"),
        ],
    )
    def test_strategy_rejects_invalid_bounds(
        self,
        kwargs: dict[str, int | float],
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            RecoveryStrategy(
                failure_type=FailureType.TOOL_ERROR,
                action=RecoveryAction.SKIP_AND_LOG,
                hint_template="Skip.",
                **kwargs,
            )

    def test_strategy_metadata_is_immutable(self) -> None:
        strategy = RecoveryStrategy(
            failure_type=FailureType.TOOL_ERROR,
            action=RecoveryAction.FALLBACK_TOOL,
            hint_template="Use another tool.",
            metadata={"fallback_tool": "local"},
        )

        with pytest.raises(TypeError):
            strategy.metadata["fallback_tool"] = "remote"  # type: ignore[index]
