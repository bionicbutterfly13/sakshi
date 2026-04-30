"""Phase registry.

Maps the six cognitive cycle phases (PERCEIVE, INTERPRET, EVAL, INTEND,
PLAN, ACT) to OODA phases, records phase outputs into a `CycleTrace`,
and fires registered callbacks when a cycle finalizes.

Hosts populate `services` per phase to advertise which concrete
implementations they wire up. The default registry leaves `services`
empty so the package itself ships no host-specific names.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sakshi.errors import PhaseTransitionError
from sakshi.models.cycle import (
    CycleTrace,
    NPStateSnapshot,
    OODAPhase,
    PhaseConfig,
    PhaseResult,
)
from sakshi.protocols import EventBus

logger = logging.getLogger(__name__)


@dataclass
class PhaseSlot:
    """OODA mapping plus optional service names for one cycle phase."""

    ooda_phase: OODAPhase
    description: str = ""
    services: list[str] = field(default_factory=list)


# Default phase-to-OODA mapping. `services` is intentionally empty so
# the package ships no host-specific names; hosts populate per phase.
DEFAULT_PHASE_REGISTRY: dict[str, PhaseSlot] = {
    "PERCEIVE": PhaseSlot(
        ooda_phase=OODAPhase.OBSERVE,
        description="Sense environment state",
    ),
    "INTERPRET": PhaseSlot(
        ooda_phase=OODAPhase.ORIENT,
        description="Anomaly detection and knowledge integration",
    ),
    "EVAL": PhaseSlot(
        ooda_phase=OODAPhase.ORIENT,
        description="Goal divergence from current state",
    ),
    "INTEND": PhaseSlot(
        ooda_phase=OODAPhase.DECIDE,
        description="Candidate selection and goal commitment",
    ),
    "PLAN": PhaseSlot(
        ooda_phase=OODAPhase.DECIDE,
        description="Policy selection and tool-chain planning",
    ),
    "ACT": PhaseSlot(
        ooda_phase=OODAPhase.ACT,
        description="Execute the committed plan",
    ),
}


CycleCompleteCallback = Callable[[CycleTrace], Awaitable[None]]


class PhaseRegistry:
    """Registry that drives a cognitive cycle through its phases.

    Usage:

        registry = PhaseRegistry(event_bus=bus)
        registry.on_cycle_complete(my_persistence_callback)

        await registry.start_cycle(cycle_id="cycle-001")
        await registry.record_phase_output("PERCEIVE", perception_result)
        await registry.record_phase_output("INTERPRET", interpret_result)
        await registry.record_phase_output("EVAL", eval_result)
        await registry.record_phase_output(
            "INTEND", intend_result, np_snapshot=np_snapshot
        )
        await registry.record_phase_output("PLAN", plan_result)
        await registry.record_phase_output("ACT", act_result)
        trace = await registry.finalize_cycle()

    Args:
        event_bus: An object satisfying `sakshi.protocols.EventBus`.
            Used to publish a cycle-complete event.
        phase_config: Optional override for the default phase mapping.
        cycle_complete_event_type: String event type the registry emits
            when a cycle finalizes. Hosts can override to align with
            their bus's event-name conventions.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        phase_config: dict[str, PhaseSlot] | None = None,
        cycle_complete_event_type: str = "sakshi.cycle.complete",
    ) -> None:
        self._event_bus = event_bus
        self._phases: dict[str, PhaseSlot] = (
            phase_config if phase_config is not None
            else dict(DEFAULT_PHASE_REGISTRY)
        )
        self._cycle_complete_event_type = cycle_complete_event_type
        self._current_trace: CycleTrace | None = None
        self._last_completed_trace: CycleTrace | None = None
        self._callbacks: list[CycleCompleteCallback] = []
        self._active_cycle_id: str | None = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def list_phases(self) -> list[str]:
        """Return ordered list of registered phase names."""
        return list(self._phases.keys())

    def get_phase_config(self, phase_name: str) -> PhaseConfig:
        """Return `PhaseConfig` for a phase.

        Raises:
            KeyError: If the phase name is not registered.
        """
        if phase_name not in self._phases:
            raise KeyError(
                f"Unknown phase: {phase_name!r}. "
                f"Registered phases: {list(self._phases.keys())}"
            )
        slot = self._phases[phase_name]
        return PhaseConfig(
            phase_name=phase_name,
            ooda_phase=slot.ooda_phase,
            description=slot.description,
            services=slot.services,
        )

    def on_cycle_complete(
        self, callback: CycleCompleteCallback
    ) -> None:
        """Register a callback to fire when `finalize_cycle()` is called."""
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Cycle lifecycle
    # ------------------------------------------------------------------

    async def start_cycle(self, cycle_id: str) -> None:
        """Begin a new cycle, resetting the current trace."""
        self._active_cycle_id = cycle_id
        self._current_trace = CycleTrace(
            cycle_id=cycle_id,
            started_at=datetime.now(timezone.utc),
        )
        logger.debug("cycle started: %s", cycle_id)

    async def record_phase_output(
        self,
        phase_name: str,
        output: dict[str, Any],
        *,
        np_snapshot: NPStateSnapshot | None = None,
    ) -> None:
        """Record the output of a completed phase.

        At INTEND, `np_snapshot` may carry the dominant thought-seed's
        NP state and prior type.
        """
        if self._current_trace is None:
            raise PhaseTransitionError(
                "No active cycle. Call start_cycle() before "
                "record_phase_output()."
            )

        config = self.get_phase_config(phase_name)

        result = PhaseResult(
            phase_name=phase_name,
            ooda_phase=config.ooda_phase,
            output=output,
        )
        self._current_trace.phase_results.append(result)

        if phase_name == "INTEND" and np_snapshot is not None:
            self._current_trace.np_state_at_intend = np_snapshot
            logger.debug(
                "NPStateSnapshot captured at INTEND: ts=%s np=%s prior=%s",
                np_snapshot.dominant_thoughtseed_id,
                np_snapshot.np_state,
                np_snapshot.prior_type,
            )

    async def finalize_cycle(self) -> CycleTrace:
        """Close the current cycle and fire all registered callbacks.

        Raises:
            PhaseTransitionError: If no cycle is active.

        Returns:
            The finalized `CycleTrace`.
        """
        if self._current_trace is None:
            raise PhaseTransitionError(
                "No active cycle to finalize. Call start_cycle() first."
            )

        self._current_trace.finalized_at = datetime.now(timezone.utc)
        trace = self._current_trace
        self._last_completed_trace = trace
        self._current_trace = None
        self._active_cycle_id = None

        logger.debug(
            "cycle finalized: %s (phases=%d)",
            trace.cycle_id,
            len(trace.phase_results),
        )

        for callback in self._callbacks:
            try:
                await callback(trace)
            except Exception as exc:
                logger.error(
                    "cycle callback failed: %s -- %s",
                    getattr(callback, "__name__", repr(callback)),
                    exc,
                    exc_info=True,
                )

        await self._publish_cycle_complete(trace)

        return trace

    async def _publish_cycle_complete(self, trace: CycleTrace) -> None:
        """Publish the cycle-complete event on the configured bus."""
        try:
            await self._event_bus.emit(
                self._cycle_complete_event_type,
                {
                    "cycle_id": trace.cycle_id,
                    "phase_count": len(trace.phase_results),
                    "achieved_goal_ids": list(trace.achieved_goals),
                },
            )
        except Exception as exc:
            logger.warning(
                "failed to publish %s: %s",
                self._cycle_complete_event_type,
                exc,
            )

    def get_current_trace(self) -> CycleTrace | None:
        """Return the in-progress trace, or None if no cycle is active."""
        return self._current_trace

    def get_last_completed_trace(self) -> CycleTrace | None:
        """Return the most recently finalized trace, or None."""
        return self._last_completed_trace


__all__ = [
    "DEFAULT_PHASE_REGISTRY",
    "CycleCompleteCallback",
    "PhaseRegistry",
    "PhaseSlot",
]
