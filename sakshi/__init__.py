"""Sakshi: a metacognitive runtime for Python agents."""

from __future__ import annotations

from sakshi.errors import (
    AnomalyEscalationError,
    GoalValidationError,
    PhaseTransitionError,
    PlanSoundnessError,
    SakshiError,
    WorldStateUnavailableError,
)
from sakshi.protocols import (
    AlwaysPermitWriteGuard,
    BasinHook,
    Clock,
    EventBus,
    GoalStateStore,
    NoOpBasinHook,
    NoOpEventBus,
    WriteGuard,
)
from sakshi.registries import PhaseRegistry

__version__ = "0.2.0"

__all__ = [
    "AlwaysPermitWriteGuard",
    "AnomalyEscalationError",
    "BasinHook",
    "Clock",
    "EventBus",
    "GoalStateStore",
    "GoalValidationError",
    "NoOpBasinHook",
    "NoOpEventBus",
    "PhaseRegistry",
    "PhaseTransitionError",
    "PlanSoundnessError",
    "SakshiError",
    "WorldStateUnavailableError",
    "WriteGuard",
    "__version__",
]
