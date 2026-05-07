"""Cognitive expectation DTOs.

Formal pre / post-condition expectations around cycle phases plus
violation records. Pattern: "If X holds before PHASE, then Y holds
after PHASE; if Y does not hold, report a violation."

In addition to the per-phase ``CognitiveExpectation``, modules can
register a five-property ``ExpectationProfile`` that declares the
contract Sakshi watches for: latency bound, output schema, calibration
range, side-effects footprint, and admissible failure modes. This is
the primary typed-monitoring surface — every module says what it
should do; Sakshi reports when it doesn't.
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


class FailureMode(BaseModel):
    """One named failure mode a module declares as admissible."""

    name: str
    severity: ExpectationSeverity = ExpectationSeverity.WARNING
    description: str = ""


class ExpectationProfile(BaseModel):
    """Five-property contract a module registers with Sakshi.

    The five fields are the typed-monitoring surface: every module that
    participates in a cycle declares what it is supposed to do, and
    Sakshi watches the running module against that declaration.

    Attributes:
        module_name: Identifier for the module the profile guards.
        runtime_bound_seconds: Maximum acceptable wall-clock time for
            the module's primary entry point. Violations are warnings
            unless the module also declares the failure mode
            ``timeout`` as critical.
        output_schema: Description of the shape the module is expected
            to return. Accepts a JSON-schema-like dict, a Python type
            name (string), or a fully-qualified class path. Sakshi
            does not enforce the schema — it stores it so observers
            can validate against it.
        confidence_range: Inclusive [low, high] bounds on the module's
            self-reported confidence. Used by the calibration tracker
            to detect drift outside the declared band.
        side_effects_contract: Tuple of strings naming the modules,
            blackboard keys, or external services this module is
            allowed to mutate. Anything outside the contract is a
            scope violation.
        failure_modes: Tuple of ``FailureMode`` records describing the
            anticipated failure shapes. Modules that fail in
            undeclared ways trigger an UNDECLARED_FAILURE violation.
    """

    module_name: str
    runtime_bound_seconds: float = Field(
        default=2.0,
        ge=0.0,
        description="Maximum acceptable wall-clock time for the module call.",
    )
    output_schema: dict[str, Any] | str = Field(
        default_factory=dict,
        description="JSON-schema-like dict, type name, or class path.",
    )
    confidence_range: tuple[float, float] = Field(
        default=(0.0, 1.0),
        description="Inclusive [low, high] bounds on self-reported confidence.",
    )
    side_effects_contract: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Module / blackboard / service names this module may mutate.",
    )
    failure_modes: tuple[FailureMode, ...] = Field(
        default_factory=tuple,
        description="Admissible failure shapes the module declares up front.",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        low, high = self.confidence_range
        if not 0.0 <= low <= high <= 1.0:
            raise ValueError(
                f"confidence_range must be 0.0 <= low <= high <= 1.0, "
                f"got ({low!r}, {high!r})"
            )

    def confidence_in_band(self, confidence: float) -> bool:
        """Return whether ``confidence`` falls inside the declared band."""
        low, high = self.confidence_range
        return low <= confidence <= high

    def is_declared_failure(self, name: str) -> bool:
        """Return whether ``name`` matches a declared failure mode."""
        return any(mode.name == name for mode in self.failure_modes)

    def has_side_effect(self, target: str) -> bool:
        """Return whether ``target`` is inside the declared side-effects contract."""
        return target in self.side_effects_contract


__all__ = [
    "CognitiveExpectation",
    "ExpectationProfile",
    "ExpectationSeverity",
    "ExpectationViolation",
    "FailureMode",
]
