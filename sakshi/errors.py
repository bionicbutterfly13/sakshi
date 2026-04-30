"""Sakshi error hierarchy.

Every Sakshi-raised exception inherits from `SakshiError` so callers
can catch the package's surface with one except clause.
"""

from __future__ import annotations


class SakshiError(Exception):
    """Base class for all Sakshi-raised exceptions."""


class GoalValidationError(SakshiError):
    """A goal failed validation against the current world state or schema."""


class PlanSoundnessError(SakshiError):
    """A plan failed soundness verification before execution."""


class AnomalyEscalationError(SakshiError):
    """An anomaly persisted beyond the configured escalation threshold."""


class PhaseTransitionError(SakshiError):
    """A cognitive cycle phase transition was attempted in an invalid state."""


class WorldStateUnavailableError(SakshiError):
    """The configured `GoalStateStore` could not return a world-state snapshot."""


__all__ = [
    "AnomalyEscalationError",
    "GoalValidationError",
    "PhaseTransitionError",
    "PlanSoundnessError",
    "SakshiError",
    "WorldStateUnavailableError",
]
