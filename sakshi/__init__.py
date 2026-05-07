"""Sakshi: a metacognitive runtime for Python agents."""

from __future__ import annotations

from sakshi.cycle import (
    LastNPruner,
    SinceAnomalyPruner,
    TracePruner,
    WhereExpectationFiredPruner,
)
from sakshi.errors import (
    AnomalyEscalationError,
    GoalValidationError,
    PhaseTransitionError,
    PlanSoundnessError,
    SakshiError,
    WorldStateUnavailableError,
)
from sakshi.models import (
    AnomalySourceType,
    DiscrepancyResolution,
    GoalEvent,
    GoalEventType,
    GoalMode,
    GoalOperation,
    GoalOperationEvent,
    ProjectionTransparency,
    ReasoningTransparency,
    ResolutionLevel,
    StatusTransparency,
    TransparencyLevel,
)
from sakshi.plans import Action, GoalConstraint, TaskDecomposer
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

__version__ = "0.4.0a0"

__all__ = [
    "Action",
    "AlwaysPermitWriteGuard",
    "AnomalyEscalationError",
    "AnomalySourceType",
    "BasinHook",
    "Clock",
    "DiscrepancyResolution",
    "EventBus",
    "GoalConstraint",
    "GoalEvent",
    "GoalEventType",
    "GoalMode",
    "GoalOperation",
    "GoalOperationEvent",
    "GoalStateStore",
    "GoalValidationError",
    "LastNPruner",
    "NoOpBasinHook",
    "NoOpEventBus",
    "PhaseRegistry",
    "PhaseTransitionError",
    "PlanSoundnessError",
    "ProjectionTransparency",
    "ReasoningTransparency",
    "ResolutionLevel",
    "SakshiError",
    "SinceAnomalyPruner",
    "StatusTransparency",
    "TaskDecomposer",
    "TracePruner",
    "TransparencyLevel",
    "WhereExpectationFiredPruner",
    "WorldStateUnavailableError",
    "WriteGuard",
    "__version__",
]
