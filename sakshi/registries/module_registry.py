"""Module registry.

Maps cycle phases to lists of alternative implementations and tracks
which one is currently active. Hot-swap support enables a metacognitive
control action to replace a failing implementation without modifying
the registry itself.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RegisteredModule:
    """A module registered as an alternative for a cycle phase."""

    name: str
    priority: int  # lower is higher priority (1 is the default / primary)
    metadata: dict[str, Any] = field(default_factory=dict)


class ModuleRegistry:
    """Map phases to alternative module implementations with hot-swap.

    Each phase can have multiple registered modules. One is active at
    any time (initially the highest priority). A swap call changes the
    active module without modifying the registry.
    """

    def __init__(self) -> None:
        self._modules: dict[str, list[RegisteredModule]] = defaultdict(list)
        self._active_overrides: dict[str, str] = {}
        self._swap_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def register(
        self,
        phase_name: str,
        module_name: str,
        priority: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a module as an alternative for a phase.

        Args:
            phase_name: Cycle phase name.
            module_name: Unique name of the module / service.
            priority: Lower is higher priority (1 = default / primary).
            metadata: Optional metadata about the module.
        """
        module = RegisteredModule(
            name=module_name,
            priority=priority,
            metadata=metadata or {},
        )
        self._modules[phase_name].append(module)
        self._modules[phase_name].sort(key=lambda m: m.priority)
        logger.debug(
            "ModuleRegistry: registered %s for phase %s (priority=%d)",
            module_name,
            phase_name,
            priority,
        )

    def get_modules_for_phase(
        self, phase_name: str
    ) -> list[RegisteredModule]:
        """Return all registered modules for a phase, sorted by priority."""
        return list(self._modules.get(phase_name, []))

    def get_active_module(
        self, phase_name: str
    ) -> RegisteredModule | None:
        """Return the currently active module for a phase.

        Returns the swap override if one exists; otherwise returns the
        highest-priority registered module. Returns None if the phase
        has no registered modules.
        """
        modules = self._modules.get(phase_name, [])
        if not modules:
            return None

        override_name = self._active_overrides.get(phase_name)
        if override_name:
            for mod in modules:
                if mod.name == override_name:
                    return mod

        return modules[0]

    def swap_module(
        self, phase_name: str, target_module_name: str
    ) -> bool:
        """Swap the active module for a phase.

        Args:
            phase_name: Phase to swap module for.
            target_module_name: Name of the module to activate.

        Returns:
            True if the swap succeeded, False if the module was not found.
        """
        modules = self._modules.get(phase_name, [])
        if not modules:
            logger.warning(
                "ModuleRegistry: swap failed, no modules for phase %s",
                phase_name,
            )
            return False

        target = next(
            (m for m in modules if m.name == target_module_name),
            None,
        )
        if target is None:
            logger.warning(
                "ModuleRegistry: swap failed, module %s not found "
                "for phase %s",
                target_module_name,
                phase_name,
            )
            return False

        previous = self.get_active_module(phase_name)
        self._active_overrides[phase_name] = target_module_name

        self._swap_history[phase_name].append(
            {
                "from": previous.name if previous else None,
                "to": target_module_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            "ModuleRegistry: swapped %s -> %s for phase %s",
            previous.name if previous else "none",
            target_module_name,
            phase_name,
        )
        return True

    def restore_default(self, phase_name: str) -> None:
        """Restore the default (highest-priority) module for a phase.

        Removes any swap override, reverting to priority-based selection.
        """
        if phase_name in self._active_overrides:
            del self._active_overrides[phase_name]
            logger.debug(
                "ModuleRegistry: restored default module for phase %s",
                phase_name,
            )

    def get_swap_history(self, phase_name: str) -> list[dict[str, Any]]:
        """Return the swap history for a phase."""
        return list(self._swap_history.get(phase_name, []))


__all__ = ["ModuleRegistry", "RegisteredModule"]
