"""Public protocols defining the Sakshi seam.

Hosts supply concrete implementations of these protocols; Sakshi's
pure-core modules accept them by parameter so the package itself never
depends on a specific runtime, persistence layer, web framework, or
LLM SDK.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sakshi.models.goal import GoalOutcomeRecord
    from sakshi.models.world_state import WorldStateSnapshot


@runtime_checkable
class EventBus(Protocol):
    """Async pub/sub seam for emitting cycle and goal events.

    A host wraps its own bus implementation in an adapter that
    satisfies this protocol.
    """

    async def emit(self, event_type: str, payload: Mapping[str, Any]) -> None: ...


@runtime_checkable
class Clock(Protocol):
    """Time source.

    Allows tests and deterministic replays to substitute a fake clock.
    """

    def now(self) -> datetime: ...


@runtime_checkable
class GoalStateStore(Protocol):
    """Goal-related world-state persistence and retrieval seam.

    Hosts that persist world state in a graph database, vector store,
    or any other backend wrap that backend in an adapter implementing
    this protocol. Sakshi never imports a specific persistence layer.
    """

    async def fetch_world_state(
        self, query: Mapping[str, Any]
    ) -> WorldStateSnapshot: ...

    async def record_goal_outcome(self, record: GoalOutcomeRecord) -> None: ...


@runtime_checkable
class BasinHook(Protocol):
    """Optional hook for hosts that maintain an attractor-basin field.

    Sakshi calls these on goal lifecycle transitions. Hosts that do not
    use a basin field supply a no-op implementation; see
    `NoOpBasinHook` for the package default.
    """

    async def on_goal_achieved(self, goal_id: str) -> None: ...

    async def on_goal_abandoned(self, goal_id: str) -> None: ...


@runtime_checkable
class WriteGuard(Protocol):
    """Pre-write safety check seam.

    Hosts can route Sakshi-originated writes through their own write-
    safety policy. Returns True if the write is permitted, False
    otherwise.
    """

    async def check(self, source_origin: str, payload: Mapping[str, Any]) -> bool: ...


class NoOpBasinHook:
    """Default `BasinHook` that does nothing.

    Use this when the host does not maintain an attractor-basin field.
    """

    async def on_goal_achieved(self, goal_id: str) -> None:
        return None

    async def on_goal_abandoned(self, goal_id: str) -> None:
        return None


class NoOpEventBus:
    """Default `EventBus` that drops emitted events."""

    async def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        return None


class AlwaysPermitWriteGuard:
    """Default `WriteGuard` that permits every write.

    Use this only in tests or in hosts where Sakshi-originated writes
    do not require external safety review.
    """

    async def check(self, source_origin: str, payload: Mapping[str, Any]) -> bool:
        return True


__all__ = [
    "AlwaysPermitWriteGuard",
    "BasinHook",
    "Clock",
    "EventBus",
    "GoalStateStore",
    "NoOpBasinHook",
    "NoOpEventBus",
    "WriteGuard",
]
