"""Goal-management core.

This package contains pure goal graph, validation, selection, transform,
and outcome-memory logic. Host-specific execution summaries, graph
persistence, basin hooks, and legacy goal-service synchronization belong
in adapters outside this package.
"""

from __future__ import annotations

from sakshi.goals.explainer import (
    AnomalyExplainer,
    AnomalyExplanation,
    BasinProfile,
    find_most_shifted_key,
)
from sakshi.goals.generator import GoalGenerator, severity_to_priority
from sakshi.goals.graph import (
    DEFAULT_PARENT_COUPLING,
    MAX_COUPLING_BASINS,
    GoalEdge,
    GoalGraph,
    GoalNode,
)
from sakshi.goals.monitor import GoalMonitor, GoalMonitorResult
from sakshi.goals.motivation import (
    DEFAULT_AUDITOR_WINDOW,
    RISK_TYPES,
    MotivationAuditor,
)
from sakshi.goals.outcome_closure import GoalOutcomeClosureService
from sakshi.goals.outcome_memory import GoalOutcomeMemory
from sakshi.goals.rebel import (
    AcceptingRebelHook,
    RebelDecision,
    RebelHook,
    RebelVerdict,
)
from sakshi.goals.selector import GoalSelector, ModSelectionCriteria
from sakshi.goals.transformer import GoalTransformer, TransformType
from sakshi.goals.validator import (
    DomainRegistry,
    GoalValidationResult,
    GoalValidator,
)

__all__ = [
    "DEFAULT_AUDITOR_WINDOW",
    "DEFAULT_PARENT_COUPLING",
    "MAX_COUPLING_BASINS",
    "RISK_TYPES",
    "AcceptingRebelHook",
    "DomainRegistry",
    "GoalEdge",
    "AnomalyExplainer",
    "AnomalyExplanation",
    "BasinProfile",
    "GoalGraph",
    "GoalGenerator",
    "GoalNode",
    "GoalMonitor",
    "GoalMonitorResult",
    "GoalOutcomeClosureService",
    "GoalOutcomeMemory",
    "GoalSelector",
    "GoalTransformer",
    "GoalValidationResult",
    "GoalValidator",
    "ModSelectionCriteria",
    "MotivationAuditor",
    "RebelDecision",
    "RebelHook",
    "RebelVerdict",
    "TransformType",
    "find_most_shifted_key",
    "severity_to_priority",
]
