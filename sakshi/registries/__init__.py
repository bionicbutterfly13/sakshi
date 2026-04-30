"""Sakshi registry classes.

The module registry tracks alternative implementations of each phase
with hot-swap support. The phase registry maps cycle phase names to
OODA phases and runs the cycle-completion callback chain.
"""

from __future__ import annotations

from sakshi.registries.module_registry import ModuleRegistry, RegisteredModule
from sakshi.registries.phase_registry import (
    DEFAULT_PHASE_REGISTRY,
    CycleCompleteCallback,
    PhaseRegistry,
    PhaseSlot,
)

__all__ = [
    "DEFAULT_PHASE_REGISTRY",
    "CycleCompleteCallback",
    "ModuleRegistry",
    "PhaseRegistry",
    "PhaseSlot",
    "RegisteredModule",
]
