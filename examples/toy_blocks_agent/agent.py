"""Host cognition: a 3-phase PERCEIVE → PLAN → ACT loop.

The agent is the *host* in Witness-pattern terminology — it owns the
planner, the world model, and the action executor. Sakshi sits beside
it, observing each phase output through the typed seams.

The planner is intentionally trivial: it walks the desired stack from
the top down and emits at most one move per cycle. That keeps cycles
small and makes the metacognitive trace easy to read.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from examples.toy_blocks_agent.world import (
    TABLE,
    Action,
    Block,
    BlocksWorld,
    InvalidActionError,
    PickupAction,
    PutdownAction,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentCycleReport:
    """What the agent produced in one cycle. Becomes Sakshi phase outputs."""

    cycle_id: str
    perceived_facts: dict[str, str]
    planned_action: Action | None
    acted: bool
    error: str | None


class BlocksAgent:
    """Plan-to-stack agent.

    Given a desired stack (e.g. ``["A", "B", "C"]`` meaning A on B on C
    on table), the agent inspects the world, picks one move that gets
    closer to the goal, and executes it. If the stack is already in
    place the agent reports a no-op cycle.
    """

    def __init__(self, world: BlocksWorld, target_stack: list[Block]) -> None:
        if len(set(target_stack)) != len(target_stack):
            raise ValueError("target_stack must list distinct blocks")
        self._world = world
        self._target_stack = list(target_stack)
        self._cycle_count = 0

    @property
    def target_stack(self) -> list[Block]:
        return list(self._target_stack)

    @property
    def world(self) -> BlocksWorld:
        return self._world

    @property
    def is_goal_reached(self) -> bool:
        return self._next_required_move() is None

    def run_cycle(self) -> AgentCycleReport:
        self._cycle_count += 1
        cycle_id = f"toy-{self._cycle_count:03d}"

        perceived = self._world.snapshot_facts()
        action = self._next_required_move()

        if action is None:
            return AgentCycleReport(
                cycle_id=cycle_id,
                perceived_facts=perceived,
                planned_action=None,
                acted=False,
                error=None,
            )

        try:
            self._world.apply(action)
        except InvalidActionError as exc:
            return AgentCycleReport(
                cycle_id=cycle_id,
                perceived_facts=perceived,
                planned_action=action,
                acted=False,
                error=str(exc),
            )

        return AgentCycleReport(
            cycle_id=cycle_id,
            perceived_facts=perceived,
            planned_action=action,
            acted=True,
            error=None,
        )

    def _next_required_move(self) -> Action | None:
        """Greedy planner: fix the deepest wrong placement first.

        Walks the target stack bottom-up. The first block whose actual
        support differs from the target gets the next move. If the
        agent is holding the right block, put it down; otherwise pick
        it up (after clearing whatever sits on top of it).
        """
        for i, block in enumerate(reversed(self._target_stack)):
            desired_support = (
                TABLE if i == 0 else list(reversed(self._target_stack))[i - 1]
            )
            actual_support = self._world.stack_above(block)
            if actual_support == desired_support:
                continue
            return self._move_block_to(block, desired_support)
        return None

    def _move_block_to(self, block: Block, desired_support: Any) -> Action:
        if self._world.held == block:
            return PutdownAction(block=block, target=desired_support)
        if self._world.held is not None:
            return PutdownAction(block=self._world.held, target=TABLE)
        blocker = self._block_on_top_of(block)
        if blocker is not None:
            return PickupAction(block=blocker)
        return PickupAction(block=block)

    def _block_on_top_of(self, block: Block) -> Block | None:
        for candidate, support in self._world.on.items():
            if support == block:
                return candidate
        return None
