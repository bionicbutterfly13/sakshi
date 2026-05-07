"""Metacognitive control loop.

The meta-loop ships five primitives:

* ``MetaController`` runs the six-phase cycle.
* ``MetaSchedulingPolicy`` decides whether to run the meta-cycle on
  this iteration.
* ``DeliberationGate`` decides between routine and deliberative
  reasoning paths.
* ``CanalizationMetrics`` reports stuck-loop signals as a typed
  struct.
* ``InterventionExecutor`` validates every control action against
  recent history and a host-supplied permission policy; the
  ``InterventionType`` taxonomy labels the *pattern* of an
  intervention orthogonally to its mechanism.
"""

from __future__ import annotations

from sakshi.meta.canalization import (
    HEALTHY_DEPTH_CEILING,
    PATHOLOGICAL_DEPTH_FLOOR,
    CanalizationMetrics,
    CanalizationRisk,
    metrics_from_static_cycles,
)
from sakshi.meta.controller import (
    CognitiveAssessor,
    MetaController,
    MetaCycleResult,
    build_world_state_from_trace,
    collect_goal_relevant_dimensions,
    compute_gfe,
)
from sakshi.meta.deliberation import (
    DEFAULT_BUDGET_FLOOR,
    DEFAULT_CONFIDENCE_FLOOR,
    DEFAULT_FAILURE_CEILING,
    DeliberationDecision,
    DeliberationGate,
    DeliberationPath,
)
from sakshi.meta.intervention_executor import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_HISTORY_SIZE,
    AlwaysPermitPolicy,
    InterventionDecision,
    InterventionExecutor,
    InterventionOutcome,
    InterventionPermissionPolicy,
    InterventionRecord,
    InterventionType,
)
from sakshi.meta.scheduling import (
    EveryCyclePolicy,
    MetaSchedulingPolicy,
    OnAnomalyPolicy,
    SchedulingDecision,
    ThrottledByLoadPolicy,
)

__all__ = [
    "DEFAULT_BUDGET_FLOOR",
    "DEFAULT_CONFIDENCE_FLOOR",
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_FAILURE_CEILING",
    "DEFAULT_HISTORY_SIZE",
    "HEALTHY_DEPTH_CEILING",
    "PATHOLOGICAL_DEPTH_FLOOR",
    "AlwaysPermitPolicy",
    "CanalizationMetrics",
    "CanalizationRisk",
    "CognitiveAssessor",
    "DeliberationDecision",
    "DeliberationGate",
    "DeliberationPath",
    "EveryCyclePolicy",
    "InterventionDecision",
    "InterventionExecutor",
    "InterventionOutcome",
    "InterventionPermissionPolicy",
    "InterventionRecord",
    "InterventionType",
    "MetaController",
    "MetaCycleResult",
    "MetaSchedulingPolicy",
    "OnAnomalyPolicy",
    "SchedulingDecision",
    "ThrottledByLoadPolicy",
    "build_world_state_from_trace",
    "collect_goal_relevant_dimensions",
    "compute_gfe",
    "metrics_from_static_cycles",
]
