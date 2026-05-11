"""Sakshi seam adapters scoped to the research session.

These are intentionally minimal — the package's deny-by-default
``DenyByDefaultWriteGuard`` is the right *production* choice for a
publish gate, but the example uses a logging-permissive guard so a
reader can see the seam fire end-to-end. A real host swaps this for
its own safety policy.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LoggingResearchEventBus:
    """Async event bus that captures the full research transcript."""

    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        snapshot = dict(payload)
        self.events.append((event_type, snapshot))
        logger.debug("event: %s %s", event_type, snapshot)

    def events_of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [payload for et, payload in self.events if et == event_type]


@dataclass
class PermissiveResearchWriteGuard:
    """WriteGuard that permits writes but records every check.

    Production hosts replace this with a real safety policy. The
    ``checks`` list lets tests assert that the publish seam fired.
    """

    checks: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    permit: bool = True

    async def check(self, source_origin: str, payload: Mapping[str, Any]) -> bool:
        self.checks.append((source_origin, dict(payload)))
        return self.permit


@dataclass
class ResearchStateStore:
    """In-memory store for published research reports."""

    published: list[dict[str, Any]] = field(default_factory=list)

    async def publish(self, payload: Mapping[str, Any]) -> None:
        self.published.append(dict(payload))
