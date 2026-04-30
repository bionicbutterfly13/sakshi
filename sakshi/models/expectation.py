"""Cognitive expectation DTOs.

Formal pre / post-condition expectations around cycle phases plus
violation records. Pattern: "If X holds before PHASE, then Y holds
after PHASE; if Y does not hold, report a violation."
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExpectationSeverity(StrEnum):
    """Severity level for expectation violations."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CognitiveExpectation(BaseModel):
    """A formal expectation about cognitive phase behavior.

    The pre and post condition keys reference blackboard keys or phase
    output fields. An evaluator checks the relationship between the
    pre-phase and post-phase values.
    """

    expectation_id: str
    phase_name: str = Field(
        description=(
            "Phase this expectation guards: "
            "PERCEIVE | INTERPRET | EVAL | INTEND | PLAN | ACT"
        )
    )
    description: str = ""
    severity: ExpectationSeverity = ExpectationSeverity.WARNING

    pre_condition_key: str = Field(
        default="",
        description=("Blackboard key or phase output field to check BEFORE the phase"),
    )
    post_condition_key: str = Field(
        default="",
        description=("Blackboard key or phase output field to check AFTER the phase"),
    )

    relationship: str = Field(
        default="exists",
        description=(
            "Expected relationship between pre and post values: "
            "exists | changed | increased | decreased | equals"
        ),
    )

    expected_value: Any | None = None


class ExpectationViolation(BaseModel):
    """Record of a violated cognitive expectation."""

    expectation_id: str
    phase_name: str
    cycle_id: str
    severity: ExpectationSeverity
    description: str
    pre_value: Any | None = None
    post_value: Any | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "CognitiveExpectation",
    "ExpectationSeverity",
    "ExpectationViolation",
]
