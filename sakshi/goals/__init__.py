"""Goal-management core.

This package contains pure goal graph, validation, selection, transform,
and outcome-memory logic. Host-specific execution summaries, graph
persistence, basin hooks, and legacy goal-service synchronization belong
in adapters outside this package.
"""

from __future__ import annotations

from sakshi.goals.graph import (
    DEFAULT_PARENT_COUPLING,
    MAX_COUPLING_BASINS,
    GoalEdge,
    GoalGraph,
    GoalNode,
)
from sakshi.goals.outcome_memory import GoalOutcomeMemory
from sakshi.goals.selector import GoalSelector, ModSelectionCriteria
from sakshi.goals.transformer import GoalTransformer, TransformType
from sakshi.goals.validator import (
    DomainRegistry,
    GoalValidationResult,
    GoalValidator,
)

__all__ = [
    "DEFAULT_PARENT_COUPLING",
    "MAX_COUPLING_BASINS",
    "DomainRegistry",
    "GoalEdge",
    "GoalGraph",
    "GoalNode",
    "GoalOutcomeMemory",
    "GoalSelector",
    "GoalTransformer",
    "GoalValidationResult",
    "GoalValidator",
    "ModSelectionCriteria",
    "TransformType",
]
