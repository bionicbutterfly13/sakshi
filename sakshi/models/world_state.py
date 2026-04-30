"""World-state DTO.

A lightweight snapshot of the current world state, used by the goal
validator and goal monitor (and returned through the
`GoalStateStore.fetch_world_state` protocol).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorldStateSnapshot(BaseModel):
    """Lightweight snapshot of the current world state.

    Maps predicate name → args dict (one entry per active predicate
    instance).

    Example:
        ``WorldStateSnapshot(facts={"CLEAR": {}})``
    """

    facts: dict[str, Any] = Field(default_factory=dict)

    def contains(self, predicate_name: str) -> bool:
        """True if predicate is currently true in the world state."""
        return predicate_name in self.facts


__all__ = ["WorldStateSnapshot"]
