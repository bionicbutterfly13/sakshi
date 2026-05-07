"""Metacognitive control loop.

The meta-loop ships three primitives:

* ``MetaController`` runs the six-phase cycle.
* ``CanalizationMetrics`` reports stuck-loop signals as a typed struct.
* ``InterventionExecutor`` validates every control action against
  recent history and a host-supplied permission policy.
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
from sakshi.meta.intervention_executor import (
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_HISTORY_SIZE,
    AlwaysPermitPolicy,
    InterventionDecision,
    InterventionExecutor,
    InterventionOutcome,
    InterventionPermissionPolicy,
    InterventionRecord,
)

__all__ = [
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_HISTORY_SIZE",
    "HEALTHY_DEPTH_CEILING",
    "PATHOLOGICAL_DEPTH_FLOOR",
    "AlwaysPermitPolicy",
    "CanalizationMetrics",
    "CanalizationRisk",
    "CognitiveAssessor",
    "InterventionDecision",
    "InterventionExecutor",
    "InterventionOutcome",
    "InterventionPermissionPolicy",
    "InterventionRecord",
    "MetaController",
    "MetaCycleResult",
    "build_world_state_from_trace",
    "collect_goal_relevant_dimensions",
    "compute_gfe",
    "metrics_from_static_cycles",
]
