"""Expectation-based cognitive anomaly detection."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sakshi.models.expectation import (
    CognitiveExpectation,
    ExpectationViolation,
)

logger = logging.getLogger(__name__)


class ExpectationEvaluator:
    """Evaluate registered expectations against phase pre/post state."""

    def __init__(self) -> None:
        self._expectations: dict[str, list[CognitiveExpectation]] = defaultdict(list)

    def register(self, expectation: CognitiveExpectation) -> None:
        """Register an expectation for a phase."""
        self._expectations[expectation.phase_name].append(expectation)
        logger.debug(
            "registered expectation %s phase=%s",
            expectation.expectation_id,
            expectation.phase_name,
        )

    def get_expectations_for_phase(self, phase_name: str) -> list[CognitiveExpectation]:
        """Return expectations registered for a phase."""
        return list(self._expectations.get(phase_name, []))

    async def evaluate_phase(
        self,
        phase_name: str,
        cycle_id: str,
        pre_state: dict[str, Any],
        post_state: dict[str, Any],
    ) -> list[ExpectationViolation]:
        """Evaluate all expectations for a phase."""
        violations: list[ExpectationViolation] = []
        for expectation in self._expectations.get(phase_name, []):
            violation = self._check_expectation(
                expectation,
                cycle_id,
                pre_state,
                post_state,
            )
            if violation is not None:
                violations.append(violation)
                logger.debug(
                    "expectation violated id=%s phase=%s cycle=%s severity=%s",
                    expectation.expectation_id,
                    phase_name,
                    cycle_id,
                    violation.severity,
                )
        return violations

    def _check_expectation(
        self,
        expectation: CognitiveExpectation,
        cycle_id: str,
        pre_state: dict[str, Any],
        post_state: dict[str, Any],
    ) -> ExpectationViolation | None:
        pre_value = (
            pre_state.get(expectation.pre_condition_key)
            if expectation.pre_condition_key
            else None
        )
        post_value = (
            post_state.get(expectation.post_condition_key)
            if expectation.post_condition_key
            else None
        )

        violated, description = self._evaluate_relationship(
            expectation,
            pre_value,
            post_value,
        )
        if not violated:
            return None

        return ExpectationViolation(
            expectation_id=expectation.expectation_id,
            phase_name=expectation.phase_name,
            cycle_id=cycle_id,
            severity=expectation.severity,
            description=description or expectation.description,
            pre_value=pre_value,
            post_value=post_value,
        )

    def _evaluate_relationship(
        self,
        expectation: CognitiveExpectation,
        pre_value: Any,
        post_value: Any,
    ) -> tuple[bool, str]:
        relationship = expectation.relationship

        if relationship == "exists":
            if post_value is None:
                return True, (
                    f"Expected {expectation.post_condition_key!r} to exist "
                    f"after {expectation.phase_name}, but it was None"
                )
            return False, ""

        if relationship == "changed":
            if pre_value == post_value:
                return True, (
                    f"Expected {expectation.post_condition_key!r} to change "
                    f"during {expectation.phase_name}, but it remained "
                    f"{post_value!r}"
                )
            return False, ""

        if relationship in {"increased", "decreased"}:
            return self._evaluate_numeric_relationship(
                expectation,
                pre_value,
                post_value,
                relationship,
            )

        if relationship == "equals" and post_value != expectation.expected_value:
            return True, (
                f"Expected {expectation.post_condition_key!r} to equal "
                f"{expectation.expected_value!r} after "
                f"{expectation.phase_name}, but got {post_value!r}"
            )

        return False, ""

    def _evaluate_numeric_relationship(
        self,
        expectation: CognitiveExpectation,
        pre_value: Any,
        post_value: Any,
        relationship: str,
    ) -> tuple[bool, str]:
        try:
            if (
                post_value is None
                or pre_value is None
                or (
                    relationship == "increased"
                    and float(post_value) <= float(pre_value)
                )
                or (
                    relationship == "decreased"
                    and float(post_value) >= float(pre_value)
                )
            ):
                return True, (
                    f"Expected {expectation.post_condition_key!r} to "
                    f"{relationship} during {expectation.phase_name}: "
                    f"pre={pre_value}, post={post_value}"
                )
        except (TypeError, ValueError):
            return True, (
                f"Cannot compare {expectation.post_condition_key!r} for "
                f"{relationship}: pre={pre_value!r}, post={post_value!r}"
            )
        return False, ""
