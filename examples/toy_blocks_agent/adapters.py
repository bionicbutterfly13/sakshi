"""Reference host adapters that satisfy Sakshi's public protocols.

These are real implementations, not stubs. They are intentionally small —
the smallest thing a host can write to make Sakshi's seams useful in a
local example — so a reader can scan them in under a minute.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sakshi.models import GoalOutcomeRecord, WorldStateSnapshot

logger = logging.getLogger(__name__)


@dataclass
class InMemoryEventBus:
    """Async pub/sub bus backed by an in-process list.

    Satisfies ``sakshi.protocols.EventBus``. Every emitted event is kept
    in ``events`` so a host can read or assert on the cycle's audit
    trail after the run.
    """

    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        snapshot = dict(payload)
        self.events.append((event_type, snapshot))
        logger.debug("event: %s %s", event_type, snapshot)


@dataclass
class InMemoryGoalStateStore:
    """World-state persistence backed by an in-process dict.

    Satisfies ``sakshi.protocols.GoalStateStore``. Hosts that persist
    state in Neo4j, Postgres, or a vector store will replace this with
    an adapter to their store; the wire shape is identical.
    """

    facts: dict[str, Any] = field(default_factory=dict)
    outcomes: list[GoalOutcomeRecord] = field(default_factory=list)

    async def fetch_world_state(self, query: Mapping[str, Any]) -> WorldStateSnapshot:
        del query  # this toy store ignores query filters
        return WorldStateSnapshot(facts=dict(self.facts))

    async def record_goal_outcome(self, record: GoalOutcomeRecord) -> None:
        self.outcomes.append(record)


@dataclass
class LoggingWriteGuard:
    """Permissive ``WriteGuard`` that logs every checked write.

    Real production hosts replace this with a policy that consults their
    safety state. ``LoggingWriteGuard`` exists so a reader can see the
    seam fire and trace every Sakshi-originated write attempt during
    integration work.
    """

    checks: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    permit: bool = True

    async def check(self, source_origin: str, payload: Mapping[str, Any]) -> bool:
        snapshot = dict(payload)
        self.checks.append((source_origin, snapshot))
        logger.debug(
            "write-guard check: origin=%s permit=%s payload=%s",
            source_origin,
            self.permit,
            snapshot,
        )
        return self.permit
