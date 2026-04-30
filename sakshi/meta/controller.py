"""Metacognitive controller.

Implements a package-native MONITOR -> ASSESS -> CONTROL loop over
Sakshi DTOs. Runtime execution of returned control actions belongs to
the host adapter.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sakshi.goals import GoalGenerator, GoalGraph, GoalMonitor, GoalTransformer
from sakshi.interpret import AnomalyPersistenceTracker
from sakshi.models import (
    ControlAction,
    ControlActionType,
    CycleTrace,
    Goal,
    WorldStateSnapshot,
)
from sakshi.protocols import EventBus, WriteGuard

logger = logging.getLogger(__name__)

OPACITY_HIGH_THRESHOLD = 0.7
OPACITY_MOD_LOW = 0.4
OPACITY_MOD_HIGH = 0.7
EFE_GOOD_THRESHOLD = 0.4
GFE_GOOD_THRESHOLD = 0.5
ANOMALY_HIGH_THRESHOLD = 0.5

AssessorCallable = Callable[
    [dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]
]
AnomalyFrequencyProvider = Callable[[], float]


@dataclass
class MetaCycleResult:
    """Result of one metacognitive cycle."""

    actions: list[ControlAction] = field(default_factory=list)
    assessment: dict[str, Any] = field(default_factory=dict)
    monitoring_data: dict[str, Any] = field(default_factory=dict)


class CognitiveAssessor:
    """Default Sakshi assessor for monitoring metrics."""

    async def assess(self, monitoring_data: dict[str, Any]) -> dict[str, Any]:
        """Assess cognitive performance from monitoring metrics."""
        efe_proxy = float(monitoring_data.get("efe_proxy", 0.0))
        achieved_goal_count = int(monitoring_data.get("achieved_goal_count", 0))
        anomaly_frequency = float(monitoring_data.get("anomaly_frequency", 0.0))
        goal_relevant_anomaly_frequency = float(
            monitoring_data.get("goal_relevant_anomaly_frequency", anomaly_frequency)
        )
        gfe = float(monitoring_data.get("gfe", 0.0))
        opacity_level = float(monitoring_data.get("opacity_level", 0.0))
        phase_count = int(monitoring_data.get("phase_count", 0))

        notes: list[str] = []
        efe_ok = efe_proxy >= EFE_GOOD_THRESHOLD
        goals_ok = achieved_goal_count > 0
        anomaly_ok = goal_relevant_anomaly_frequency < ANOMALY_HIGH_THRESHOLD
        gfe_ok = gfe >= GFE_GOOD_THRESHOLD

        if not efe_ok:
            notes.append(f"Low EFE proxy ({efe_proxy:.3f})")
        if not goals_ok:
            notes.append("No goals achieved this cycle")
        if not anomaly_ok:
            notes.append(
                f"High goal-relevant anomaly frequency "
                f"({goal_relevant_anomaly_frequency:.3f})"
            )
        if not gfe_ok:
            notes.append(f"Low GFE ({gfe:.3f})")
        if opacity_level > OPACITY_HIGH_THRESHOLD:
            notes.append(f"High opacity ({opacity_level:.3f})")

        return {
            "performance_ok": (efe_ok or goals_ok) and anomaly_ok,
            "efe_proxy": efe_proxy,
            "achieved_goal_count": achieved_goal_count,
            "anomaly_frequency": anomaly_frequency,
            "goal_relevant_anomaly_frequency": goal_relevant_anomaly_frequency,
            "goal_relevant_anomaly_dims": list(
                monitoring_data.get("goal_relevant_anomaly_dims", [])
            ),
            "gfe": gfe,
            "opacity_level": opacity_level,
            "phase_count": phase_count,
            "assessment_notes": notes,
        }


class MetaController:
    """Package-native metacognitive controller."""

    def __init__(
        self,
        *,
        assessor: CognitiveAssessor | AssessorCallable | None = None,
        goal_graph: GoalGraph | None = None,
        goal_monitor: GoalMonitor | None = None,
        goal_transformer: GoalTransformer | None = None,
        goal_generator: GoalGenerator | None = None,
        anomaly_tracker: AnomalyPersistenceTracker | None = None,
        event_bus: EventBus | None = None,
        write_guard: WriteGuard | None = None,
        anomaly_frequency_provider: AnomalyFrequencyProvider | None = None,
        meta_control_event_type: str = "sakshi.meta.control",
    ) -> None:
        self._assessor = assessor or CognitiveAssessor()
        self._goal_graph = goal_graph
        self._goal_monitor = goal_monitor or GoalMonitor()
        self._goal_transformer = goal_transformer or GoalTransformer()
        self._goal_generator = goal_generator
        self._anomaly_tracker = anomaly_tracker or AnomalyPersistenceTracker()
        self._event_bus = event_bus
        self._write_guard = write_guard
        self._anomaly_frequency_provider = anomaly_frequency_provider
        self._meta_control_event_type = meta_control_event_type
        self._plan_failure_counts: dict[str, int] = {}

    async def run_meta_cycle(
        self,
        cycle_trace: CycleTrace,
        *,
        opacity_level: float = 0.0,
        plan_failure_goal_ids: Iterable[str] = (),
    ) -> MetaCycleResult:
        """Execute MONITOR -> ASSESS -> CONTROL."""
        monitoring_data = await self._monitor(cycle_trace, opacity_level=opacity_level)
        self._run_goal_monitor(cycle_trace)
        self._run_goal_transformer(plan_failure_goal_ids)
        await self._run_anomaly_escalation(
            monitoring_data,
            achieved_goal_ids=set(cycle_trace.achieved_goals or []),
        )
        assessment = await self._assess(monitoring_data)
        actions = self._generate_control_actions(assessment)
        await self._publish_meta_control(cycle_trace.cycle_id, actions)
        return MetaCycleResult(
            actions=actions,
            assessment=assessment,
            monitoring_data=monitoring_data,
        )

    async def _monitor(
        self,
        cycle_trace: CycleTrace,
        *,
        opacity_level: float,
    ) -> dict[str, Any]:
        phase_results = cycle_trace.phase_results or []
        efe_values: list[float] = []
        for result in phase_results:
            efe = result.output.get("efe_proxy") or result.output.get("confidence")
            if efe is not None:
                try:
                    efe_values.append(float(efe))
                except (TypeError, ValueError):
                    pass

        anomaly_frequency = (
            float(self._anomaly_frequency_provider())
            if self._anomaly_frequency_provider is not None
            else 0.0
        )

        active_goals = (
            self._goal_graph.get_active_frontier()
            if self._goal_graph is not None
            else []
        )
        relevant_dims = collect_goal_relevant_dimensions(active_goals)

        return {
            "phase_count": len(phase_results),
            "efe_proxy": sum(efe_values) / len(efe_values) if efe_values else 0.0,
            "achieved_goal_count": len(cycle_trace.achieved_goals or []),
            "anomaly_frequency": anomaly_frequency,
            "goal_relevant_anomaly_frequency": anomaly_frequency,
            "goal_relevant_anomaly_dims": sorted(relevant_dims),
            "gfe": compute_gfe(efe_values),
            "opacity_level": opacity_level,
        }

    def _run_goal_monitor(self, cycle_trace: CycleTrace) -> None:
        if self._goal_graph is None:
            return
        world_state = build_world_state_from_trace(cycle_trace)
        for goal in list(self._goal_graph.get_active_frontier()):
            result = self._goal_monitor.check_validity(goal, world_state)
            if result.is_valid:
                continue
            if result.reason == "already_satisfied":
                self._goal_graph.mark_achieved(goal.id)
            elif result.reason == "no_longer_relevant":
                self._goal_graph.mark_abandoned(goal.id)

    def _run_goal_transformer(
        self,
        plan_failure_goal_ids: Iterable[str],
    ) -> None:
        if self._goal_graph is None:
            return
        failed_ids = set(plan_failure_goal_ids)
        if not failed_ids:
            return

        for goal in list(self._goal_graph.get_active_frontier()):
            if goal.id not in failed_ids:
                continue
            self._plan_failure_counts[goal.id] = (
                self._plan_failure_counts.get(goal.id, 0) + 1
            )
            failure_count = self._plan_failure_counts[goal.id]
            if failure_count >= 3:
                self._goal_graph.mark_abandoned(goal.id)
                continue

            transformed = (
                self._goal_transformer.generalize(goal)
                if failure_count == 1
                else self._goal_transformer.abstract(goal)
            )
            self._goal_graph.add_goal(transformed)
            self._goal_graph.mark_abandoned(goal.id)

    async def _run_anomaly_escalation(
        self,
        monitoring_data: Mapping[str, Any],
        achieved_goal_ids: set[str],
    ) -> None:
        if self._goal_graph is None:
            return

        for goal_id in achieved_goal_ids:
            self._anomaly_tracker.record_success(goal_id)

        if float(monitoring_data.get("anomaly_frequency", 0.0)) <= 0.0:
            return

        for goal in self._goal_graph.get_active_frontier():
            escalation = self._anomaly_tracker.record_anomaly(goal.id)
            if escalation.current_level != "MUTATE_GOAL":
                continue
            if self._goal_generator is None:
                continue
            if self._write_guard is not None:
                permitted = await self._write_guard.check(
                    "sakshi_anomaly_escalation",
                    {
                        "goal_id": goal.id,
                        "anomaly_count": escalation.anomaly_count,
                    },
                )
                if not permitted:
                    continue
            await self._goal_generator.mutate_goal(
                goal.id,
                escalation.anomaly_count,
                add_to_graph=True,
            )

    async def _assess(self, monitoring_data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(self._assessor, CognitiveAssessor):
            return await self._assessor.assess(monitoring_data)
        result = self._assessor(monitoring_data)
        if hasattr(result, "__await__"):
            return await result  # type: ignore[no-any-return]
        return result

    def _generate_control_actions(
        self,
        assessment: Mapping[str, Any],
    ) -> list[ControlAction]:
        actions: list[ControlAction] = []
        opacity = float(assessment.get("opacity_level", 0.0))
        performance_ok = bool(assessment.get("performance_ok", True))

        if opacity > OPACITY_HIGH_THRESHOLD:
            actions.append(
                ControlAction(
                    action_type=ControlActionType.SUPPRESS_MODULE,
                    target="metacognition",
                    magnitude=opacity,
                    rationale=f"High metacognitive opacity ({opacity:.3f}).",
                )
            )
        elif OPACITY_MOD_LOW <= opacity < OPACITY_MOD_HIGH:
            precision_delta = float(opacity - 0.55)
            actions.append(
                ControlAction(
                    action_type=ControlActionType.ADJUST_PRECISION,
                    target="attention_gate",
                    magnitude=opacity,
                    precision_delta=precision_delta,
                    rationale=f"Moderate opacity ({opacity:.3f}); adjust precision.",
                )
            )

        if not performance_ok and opacity <= OPACITY_HIGH_THRESHOLD:
            efe_proxy = float(assessment.get("efe_proxy", 0.0))
            actions.append(
                ControlAction(
                    action_type=ControlActionType.STRENGTHEN_MODULE,
                    target="cognitive_cycle",
                    magnitude=1.0 - efe_proxy,
                    rationale=(
                        f"Poor cognitive performance (efe_proxy={efe_proxy:.3f})."
                    ),
                )
            )
        return actions

    async def _publish_meta_control(
        self,
        cycle_id: str,
        actions: list[ControlAction],
    ) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.emit(
            self._meta_control_event_type,
            {
                "cycle_id": cycle_id,
                "actions": [action.model_dump(mode="json") for action in actions],
            },
        )


def build_world_state_from_trace(cycle_trace: CycleTrace) -> WorldStateSnapshot:
    """Build a world-state snapshot from PERCEIVE-style phase output."""
    for phase_result in cycle_trace.phase_results or []:
        output = phase_result.output
        basins = output.get("basins") or output.get("active_basins") or []
        if not basins:
            continue
        basin_list = basins if isinstance(basins, list) else list(basins.keys())
        return WorldStateSnapshot(facts={str(basin): {} for basin in basin_list})
    return WorldStateSnapshot()


def collect_goal_relevant_dimensions(active_goals: Iterable[Goal]) -> set[str]:
    """Collect string dimensions named by active goals."""
    relevant: set[str] = set()
    for goal in active_goals:
        if goal.basin_name:
            relevant.add(goal.basin_name)
        for value in (goal.predicate.args or {}).values():
            if isinstance(value, str) and value:
                relevant.add(value)
    return relevant


def compute_gfe(efe_values: list[float]) -> float:
    """Compute package-local GFE proxy from per-phase EFE values."""
    if not efe_values:
        return 0.0
    return float(min(1.0, max(0.0, sum(efe_values) / len(efe_values))))


__all__ = [
    "CognitiveAssessor",
    "MetaController",
    "MetaCycleResult",
    "build_world_state_from_trace",
    "collect_goal_relevant_dimensions",
    "compute_gfe",
]
