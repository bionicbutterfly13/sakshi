"""Cycle history buffer.

Rolling in-memory buffer of past `CycleTrace` snapshots with backward
lookup. The fixed-size + prune-half-on-full pattern is inspired by
MIDCA's CogTrace design (trace.py).

Useful for metacognitive pattern analysis across past cycles without
querying a host's persistence layer.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from sakshi.models.cycle import CycleTrace

logger = logging.getLogger(__name__)


class CycleHistory:
    """Rolling buffer of `CycleTrace` snapshots.

    - Fixed `max_size` (default 100).
    - When full, prunes the oldest 50% before adding.
    - Backward lookup via `get_n_prev_cycle(n)`.

    Thread / coroutine safety is not provided: cycles are sequential
    (one cycle finalizes before the next starts).
    """

    def __init__(self, max_size: int = 100) -> None:
        self.max_size = max_size
        self._buffer: list[CycleTrace] = []

    def __len__(self) -> int:
        return len(self._buffer)

    def add(self, trace: CycleTrace) -> None:
        """Add a finalized trace to the history.

        If the buffer is at capacity, prunes the oldest half first.
        """
        if len(self._buffer) >= self.max_size:
            prune_count = self.max_size // 2
            self._buffer = self._buffer[prune_count:]
            logger.debug(
                "CycleHistory: pruned %d oldest traces (remaining=%d)",
                prune_count,
                len(self._buffer),
            )
        self._buffer.append(trace)

    def get_n_prev_cycle(self, n: int) -> CycleTrace | None:
        """Return the Nth previous cycle trace.

        Args:
            n: 0 = most recent, 1 = previous, etc.

        Returns:
            The trace, or None if `n` is out of range.
        """
        if n < 0 or n >= len(self._buffer):
            return None
        return self._buffer[-(n + 1)]

    def get_phase_output_across_cycles(
        self,
        phase_name: str,
        n_cycles: int,
    ) -> list[dict[str, Any]]:
        """Return phase outputs from the most recent N cycles.

        Skips cycles that did not record the requested phase. Results
        are ordered most-recent-first.
        """
        results: list[dict[str, Any]] = []
        for trace in reversed(self._buffer):
            if len(results) >= n_cycles:
                break
            output = trace.get_phase_output(phase_name)
            if output is not None:
                results.append(output)
        return results

    def search_cycles(
        self,
        predicate: Callable[[CycleTrace], bool],
    ) -> list[CycleTrace]:
        """Filter cycle history by a predicate function.

        Returns the matching traces in oldest-first order.
        """
        return [trace for trace in self._buffer if predicate(trace)]

    def get_latest(self) -> CycleTrace | None:
        """Return the most recent trace, or None if empty."""
        return self._buffer[-1] if self._buffer else None


__all__ = ["CycleHistory"]
