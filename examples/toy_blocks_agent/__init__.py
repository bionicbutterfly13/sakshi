"""Toy blocks-world agent wired through Sakshi's Witness seams.

A self-contained reference integration showing how a host wires its own
cognition (`agent.py`), world model (`world.py`), and protocol adapters
(`adapters.py`) into a Sakshi `PhaseRegistry` + `MetaController`. No
LLM, no network, no persistence backend — only stdlib plus Sakshi.
"""

from examples.toy_blocks_agent.adapters import (
    InMemoryEventBus,
    InMemoryGoalStateStore,
    LoggingWriteGuard,
)
from examples.toy_blocks_agent.agent import AgentCycleReport, BlocksAgent
from examples.toy_blocks_agent.world import (
    BlocksWorld,
    InvalidActionError,
    PickupAction,
    PutdownAction,
    block_stack,
)

__all__ = [
    "AgentCycleReport",
    "BlocksAgent",
    "BlocksWorld",
    "InMemoryEventBus",
    "InMemoryGoalStateStore",
    "InvalidActionError",
    "LoggingWriteGuard",
    "PickupAction",
    "PutdownAction",
    "block_stack",
]
