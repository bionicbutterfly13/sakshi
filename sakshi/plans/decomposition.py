"""Task-decomposition seam.

Sakshi treats a plan step as a string by default ([models/goal.py]
``GoalPlan.steps``). Hosts that want hierarchical-task-network style
planning, tool-call decomposition, or any other structured expansion
plug a concrete ``TaskDecomposer`` into the planning phase. The
package itself never imports a planner — the protocol exists so hosts
can swap planners without changing the meta-cycle.

``Action`` is the DTO the protocol returns: the smallest schedulable
unit a host wants to execute, with whatever arguments and metadata
the host's executor expects.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Action(BaseModel):
    """A single schedulable step produced by a task decomposer.

    The shape is intentionally narrow — name, arguments, optional
    metadata — because hosts already maintain richer action records
    elsewhere (their own executor, observability stack, etc.). This
    DTO is the package-internal join row.
    """

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class TaskDecomposer(Protocol):
    """Expand a high-level task into a flat list of executable actions.

    Implementations may consult ``world_state`` to pick a decomposition
    appropriate for the current state, or ignore it entirely for
    domain-independent expansions. The protocol is sync because most
    real planners are CPU-bound; hosts that want async planners can
    define their own protocol and adapter.
    """

    def decompose(
        self,
        task: str,
        world_state: dict[str, Any] | None = None,
    ) -> list[Action]: ...


__all__ = ["Action", "TaskDecomposer"]
