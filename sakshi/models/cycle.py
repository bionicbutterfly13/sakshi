"""Cognitive cycle DTOs.

Phase enums, phase configuration, phase results, neuronal-packet state
snapshots, complete cycle traces, and metacognitive control actions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class OODAPhase(StrEnum):
    """OODA loop phases that cognitive cycle phases map onto."""

    OBSERVE = "OBSERVE"
    ORIENT = "ORIENT"
    DECIDE = "DECIDE"
    ACT = "ACT"


class NPState(StrEnum):
    """Neuronal Packet lifecycle states (Kavi et al. 2408.15982 §3.1)."""

    UNMANIFESTED = "Unmanifested"
    INACTIVE = "Inactive"
    ACTIVATED = "Activated"
    DOMINANT = "Dominant"
    DISSIPATED = "Dissipated"


class PriorType(StrEnum):
    """Evolutionary prior taxonomy (Kavi et al. 2408.15982 §2.3).

    B (Basal): universal across species, survival/threat. Longer baseline.
    L (Lineage-specific): species-characteristic.
    D (Dispositional): individual temperamental.
    λ (Learned): session/experience-acquired. Shorter baseline.
    """

    BASAL = "B"
    LINEAGE = "L"
    DISPOSITIONAL = "D"
    LEARNED = "λ"


class AnomalyType(StrEnum):
    """Anomaly classification for goal-driven autonomy."""

    BASIN_SHIFT = "BASIN_SHIFT"
    CANALIZATION_DETECTED = "CANALIZATION_DETECTED"


class ControlActionType(StrEnum):
    """Types of metacognitive control actions emitted by the meta-loop."""

    STRENGTHEN_MODULE = "STRENGTHEN_MODULE"
    SUPPRESS_MODULE = "SUPPRESS_MODULE"
    ADJUST_PRECISION = "ADJUST_PRECISION"
    SWAP_MODULE = "SWAP_MODULE"


class PhaseConfig(BaseModel):
    """Configuration for a single cognitive cycle phase slot."""

    phase_name: str
    ooda_phase: OODAPhase
    description: str = ""
    services: list[str] = Field(default_factory=list)


class PhaseResult(BaseModel):
    """Output recorded for a single cycle phase."""

    phase_name: str
    ooda_phase: OODAPhase
    output: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NPStateSnapshot(BaseModel):
    """Snapshot of the dominant thought-seed's NP state at INTEND.

    Captures which thought-seed won, its NP lifecycle state, and
    evolutionary prior type.
    """

    dominant_thoughtseed_id: str
    np_state: str = Field(
        description=("NP lifecycle state: Inactive | Activated | Dominant | Dissipated")
    )
    prior_type: str = Field(description="Evolutionary prior: B | L | D | λ")
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("np_state")
    @classmethod
    def validate_np_state(cls, v: str) -> str:
        valid = {
            "Unmanifested",
            "Inactive",
            "Activated",
            "Dominant",
            "Dissipated",
        }
        if v not in valid:
            raise ValueError(f"np_state must be one of {valid}, got {v!r}")
        return v

    @field_validator("prior_type")
    @classmethod
    def validate_prior_type(cls, v: str) -> str:
        valid = {"B", "L", "D", "λ"}
        if v not in valid:
            raise ValueError(f"prior_type must be one of {valid}, got {v!r}")
        return v


class CycleTrace(BaseModel):
    """Complete record of one cognitive cycle (all six phases)."""

    cycle_id: str
    phase_results: list[PhaseResult] = Field(default_factory=list)
    np_state_at_intend: NPStateSnapshot | None = None
    achieved_goals: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = None

    def get_phase_output(self, phase_name: str) -> dict[str, Any] | None:
        """Return the output for a specific phase, or None if not recorded."""
        for result in self.phase_results:
            if result.phase_name == phase_name:
                return result.output
        return None


class ControlAction(BaseModel):
    """A metacognitive control action emitted by the meta-loop.

    `precision_delta` (when set) carries a signed damping adjustment for
    ADJUST_PRECISION actions routed to a host's active-inference layer.
    Hosts typically clamp to a small range (e.g., [-0.3, +0.3]) at the
    consumer.
    """

    action_type: ControlActionType
    target: str = ""
    magnitude: float = 1.0
    rationale: str = ""
    precision_delta: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "AnomalyType",
    "ControlAction",
    "ControlActionType",
    "CycleTrace",
    "NPState",
    "NPStateSnapshot",
    "OODAPhase",
    "PhaseConfig",
    "PhaseResult",
    "PriorType",
]
