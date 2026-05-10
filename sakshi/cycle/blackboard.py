"""Cognitive blackboard runtime.

Async-safe mutable shared state for inter-phase communication within
a single cognitive cycle. Phases can write intermediate outputs and
subsequent phases can read them in real time, unlike `CycleTrace`
which is a write-once audit log.

The lock-per-key model is inspired by MIDCA-style memory designs
(Cox / Raja).
"""

from __future__ import annotations

import asyncio
import copy
import logging
from contextlib import AsyncExitStack
from typing import Any

from sakshi.models.blackboard import BlackboardKey, BlackboardSnapshot

logger = logging.getLogger(__name__)


class CognitiveBlackboard:
    """Async-safe mutable blackboard for inter-phase state sharing.

    Each `BlackboardKey` gets its own `asyncio.Lock` so phases that
    write to different keys do not block each other.

    Lifecycle:
        1. `clear()` at start of cycle.
        2. `set()` / `get()` during phase execution.
        3. `snapshot()` at finalize.
    """

    def __init__(self) -> None:
        self._data: dict[BlackboardKey, Any] = {}
        self._locks: dict[BlackboardKey, asyncio.Lock] = {
            key: asyncio.Lock() for key in BlackboardKey
        }

    def _get_lock(self, key: BlackboardKey) -> asyncio.Lock:
        """Return the lock for a given key, creating it if missing."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def set(self, key: BlackboardKey, value: Any) -> None:
        """Set a value on the blackboard (async-safe per key)."""
        lock = self._get_lock(key)
        async with lock:
            self._data[key] = value

    async def get(self, key: BlackboardKey) -> Any | None:
        """Return a value from the blackboard, or None if unset."""
        lock = self._get_lock(key)
        async with lock:
            return self._data.get(key)

    async def get_or_default(self, key: BlackboardKey, default: Any) -> Any:
        """Return a value from the blackboard, or `default` if unset."""
        lock = self._get_lock(key)
        async with lock:
            return self._data.get(key, default)

    async def clear(self) -> None:
        """Clear all data from the blackboard.

        Holds every per-key lock simultaneously while clearing so a
        concurrent ``set()`` cannot interleave a write between the
        last lock release and ``self._data.clear()``. Locks are taken
        in a deterministic key-value order; no other method on this
        class acquires more than one lock at a time, so the
        multi-lock acquisition cannot deadlock against single-lock
        callers.
        """
        ordered_locks = [
            self._locks[key]
            for key in sorted(self._locks.keys(), key=lambda k: k.value)
        ]
        async with AsyncExitStack() as stack:
            for lock in ordered_locks:
                await stack.enter_async_context(lock)
            self._data.clear()

    async def keys(self) -> list[BlackboardKey]:
        """Return a list of currently set keys."""
        return list(self._data.keys())

    async def snapshot(self, cycle_id: str = "") -> BlackboardSnapshot:
        """Create an immutable snapshot of current blackboard state.

        Returns a deep copy so mutations after the snapshot do not
        affect it. If a value is not deep-copyable, the snapshot stores
        the live reference and emits a warning — callers should treat
        such snapshots as best-effort, not isolation-safe.
        """
        data_copy: dict[str, Any] = {}
        for key, value in self._data.items():
            try:
                data_copy[key.value] = copy.deepcopy(value)
            except Exception as exc:
                logger.warning(
                    "CognitiveBlackboard.snapshot: deepcopy failed for "
                    "key=%s type=%s; falling back to live reference: %s",
                    key.value,
                    type(value).__name__,
                    exc,
                )
                data_copy[key.value] = value
        return BlackboardSnapshot(data=data_copy, cycle_id=cycle_id)


__all__ = ["CognitiveBlackboard"]
