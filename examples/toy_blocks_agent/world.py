"""A minimal blocks-world domain.

Three blocks (A, B, C) start on a table. The agent can `pickup` a block
that has nothing on top of it, and `putdown` a held block onto another
clear block or onto the table. The world is fully observable and
deterministic; this is the simplest domain that still exercises a real
plan/act/observe loop and demonstrates each Sakshi seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TABLE = "table"
Block = str  # e.g. "A", "B", "C"
Surface = Block | Literal["table"]


class InvalidActionError(Exception):
    """Raised when an action is impossible in the current world state."""


@dataclass(frozen=True)
class PickupAction:
    block: Block

    @property
    def name(self) -> str:
        return f"pickup({self.block})"


@dataclass(frozen=True)
class PutdownAction:
    block: Block
    target: Surface

    @property
    def name(self) -> str:
        return f"putdown({self.block}, {self.target})"


Action = PickupAction | PutdownAction


@dataclass
class BlocksWorld:
    """Block positions: ``on[block] = surface``. Held block tracked separately."""

    on: dict[Block, Surface] = field(
        default_factory=lambda: {"A": TABLE, "B": TABLE, "C": TABLE}
    )
    held: Block | None = None

    def clear(self, surface: Surface) -> bool:
        """True if nothing is on ``surface``. The table is always clear."""
        if surface == TABLE:
            return True
        return all(self.on[b] != surface for b in self.on)

    def stack_above(self, block: Block) -> Surface:
        """Return whichever surface ``block`` sits on, or 'held' if held."""
        if self.held == block:
            return "held"
        return self.on[block]

    def apply(self, action: Action) -> None:
        if isinstance(action, PickupAction):
            if self.held is not None:
                raise InvalidActionError(
                    f"cannot pickup({action.block}) while holding {self.held!r}"
                )
            if action.block not in self.on:
                raise InvalidActionError(f"unknown block {action.block!r}")
            if not self.clear(action.block):
                raise InvalidActionError(
                    f"cannot pickup({action.block}): another block is on top"
                )
            self.held = action.block
            del self.on[action.block]
            return

        if self.held != action.block:
            raise InvalidActionError(
                f"cannot putdown({action.block}): block is not held"
            )
        if action.target != TABLE and not self.clear(action.target):
            raise InvalidActionError(
                f"cannot putdown on {action.target!r}: target is not clear"
            )
        if action.target == action.block:
            raise InvalidActionError("cannot putdown a block on itself")
        self.on[action.block] = action.target
        self.held = None

    def snapshot_facts(self) -> dict[str, str]:
        """Predicate-style facts useful for Sakshi WorldStateSnapshot."""
        facts: dict[str, str] = {f"ON({b},{s})": "true" for b, s in self.on.items()}
        if self.held is not None:
            facts[f"HELD({self.held})"] = "true"
        return facts


def block_stack(world: BlocksWorld, top: Block) -> list[Block]:
    """Return the stack from ``top`` down to the table."""
    chain: list[Block] = [top]
    surface = world.on.get(top, TABLE)
    while surface != TABLE:
        if not isinstance(surface, str) or surface == TABLE:
            break
        chain.append(surface)
        surface = world.on.get(surface, TABLE)
    return chain
