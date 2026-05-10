"""Hierarchical goal graph.

Pure in-memory partial ordering for goals with parent-child dependency
edges, active-frontier lookup, plan attachment, delegation state, and
basin-coupling export.

The graph intentionally performs no host side effects. Hosts that
maintain attractor basins should call their `BasinHook` implementation
from the adapter layer when a goal is achieved or abandoned.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sakshi.models import Goal, GoalPlan, GoalStatus

logger = logging.getLogger(__name__)

MAX_COUPLING_BASINS = 10
DEFAULT_PARENT_COUPLING = 0.8


@dataclass
class GoalNode:
    """A node in a hierarchical goal graph."""

    goal: Goal
    parent: GoalNode | None = None
    children: list[GoalNode] = field(default_factory=list)
    plan: GoalPlan | None = None
    delegate_to: str | None = None

    @property
    def is_blocked(self) -> bool:
        """True if this node's parent is not achieved yet."""
        if self.parent is None:
            return False
        return self.parent.goal.status != GoalStatus.ACHIEVED

    @property
    def is_active(self) -> bool:
        """True if this goal can currently be pursued."""
        return self.goal.status == GoalStatus.ACTIVE and not self.is_blocked


@dataclass(frozen=True)
class GoalEdge:
    """A directed dependency edge between two goals."""

    parent_id: str
    child_id: str
    coupling_strength: float = DEFAULT_PARENT_COUPLING


class GoalGraph:
    """Partial ordering of goals with a current-goal stack.

    Root goals have no prerequisites. Child goals are blocked until
    their parent has status `ACHIEVED`. No implicit cycle repair is
    attempted: callers must add parents before children.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GoalNode] = {}
        self._edges: list[GoalEdge] = []
        self._current_goal_stack: list[str] = []

    @property
    def goal_count(self) -> int:
        """Total number of goals in the graph."""
        return len(self._nodes)

    @property
    def current_goal_stack_ids(self) -> list[str]:
        """Current goal stack as a list of goal IDs; top is the last item."""
        return list(self._current_goal_stack)

    def add_goal(
        self,
        goal: Goal,
        parent_id: str | None = None,
        coupling_strength: float = DEFAULT_PARENT_COUPLING,
    ) -> GoalNode:
        """Add a goal to the graph.

        Args:
            goal: Goal to add.
            parent_id: Optional parent goal ID. If provided, the parent
                must already exist.
            coupling_strength: Strength for the parent-child coupling edge.

        Raises:
            ValueError: If a goal with the same ID already exists.
            KeyError: If `parent_id` is provided but not found.
        """
        if goal.id in self._nodes:
            raise ValueError(f"Goal {goal.id!r} already exists in the graph.")

        if parent_id is None:
            node = GoalNode(goal=goal, parent=None)
            self._nodes[goal.id] = node
            logger.debug("GoalGraph: added root goal %s", goal.id)
            return node

        parent_node = self.get_node(parent_id)
        node = GoalNode(goal=goal, parent=parent_node)
        self._nodes[goal.id] = node
        parent_node.children.append(node)
        self._edges.append(
            GoalEdge(
                parent_id=parent_id,
                child_id=goal.id,
                coupling_strength=coupling_strength,
            )
        )
        logger.debug(
            "GoalGraph: added child %s -> parent %s (coupling=%.2f)",
            goal.id,
            parent_id,
            coupling_strength,
        )
        return node

    def get_node(self, goal_id: str) -> GoalNode:
        """Return the `GoalNode` for a goal ID."""
        if goal_id not in self._nodes:
            raise KeyError(f"Goal {goal_id!r} not found in the graph.")
        return self._nodes[goal_id]

    def mark_achieved(self, goal_id: str) -> None:
        """Mark a goal as achieved and remove it from continuation state."""
        node = self.get_node(goal_id)
        node.goal.status = GoalStatus.ACHIEVED
        self._remove_from_current_goal_stack(goal_id)
        logger.info("GoalGraph: goal achieved: %s", goal_id)

    def mark_abandoned(self, goal_id: str) -> None:
        """Mark a goal as abandoned and remove it from continuation state."""
        node = self.get_node(goal_id)
        node.goal.status = GoalStatus.ABANDONED
        self._remove_from_current_goal_stack(goal_id)
        logger.info("GoalGraph: goal abandoned: %s", goal_id)

    def delegate_goal(self, goal_id: str, delegate_to: str) -> None:
        """Delegate a goal and remove it from the active frontier."""
        node = self.get_node(goal_id)
        node.goal.status = GoalStatus.DELEGATED
        node.delegate_to = delegate_to
        self._remove_from_current_goal_stack(goal_id)
        logger.info("GoalGraph: goal delegated: %s -> %s", goal_id, delegate_to)

    def get_active_frontier(self) -> list[Goal]:
        """Return active goals whose prerequisites are satisfied."""
        return [node.goal for node in self._nodes.values() if node.is_active]

    def iter_goals(self) -> list[Goal]:
        """Return every goal currently in the graph (any status).

        Order is insertion-stable. Hosts that need to scan terminal goals
        for persistence should prefer :meth:`get_goals_by_status` instead
        of pulling this and filtering — the explicit filter form keeps
        intent visible in caller code.
        """
        return [node.goal for node in self._nodes.values()]

    def get_goals_by_status(self, statuses: set[GoalStatus]) -> list[Goal]:
        """Return goals whose status is in ``statuses``.

        Args:
            statuses: Set of :class:`GoalStatus` values to match. Empty
                set returns an empty list.

        Returns:
            Matching goals in insertion order. Empty list if no matches
            or ``statuses`` is empty.
        """
        if not statuses:
            return []
        return [
            node.goal for node in self._nodes.values() if node.goal.status in statuses
        ]

    def to_coupling_matrix(self) -> dict[tuple[str, str], float]:
        """Export active parent-child basin edges as a coupling matrix.

        Only active goals with non-empty `basin_name` values are included,
        capped to `MAX_COUPLING_BASINS` by descending goal priority.
        """
        active_nodes = [
            node
            for node in self._nodes.values()
            if node.goal.status == GoalStatus.ACTIVE
        ]
        active_nodes.sort(key=lambda node: node.goal.priority, reverse=True)
        active_nodes = active_nodes[:MAX_COUPLING_BASINS]
        active_basins = {
            node.goal.basin_name for node in active_nodes if node.goal.basin_name
        }

        matrix: dict[tuple[str, str], float] = {}
        for edge in self._edges:
            parent_node = self._nodes.get(edge.parent_id)
            child_node = self._nodes.get(edge.child_id)
            if parent_node is None or child_node is None:
                continue
            parent_basin = parent_node.goal.basin_name
            child_basin = child_node.goal.basin_name
            if (
                parent_basin
                and child_basin
                and parent_basin in active_basins
                and child_basin in active_basins
            ):
                matrix[(parent_basin, child_basin)] = edge.coupling_strength
        return matrix

    def set_plan(self, goal_id: str, plan: GoalPlan) -> None:
        """Attach a plan to a goal node."""
        node = self.get_node(goal_id)
        node.plan = plan
        logger.debug(
            "GoalGraph: plan set for goal %s (%d steps)",
            goal_id,
            len(plan.steps),
        )

    def get_plan(self, goal_id: str) -> GoalPlan | None:
        """Return the plan attached to a goal, if present."""
        return self.get_node(goal_id).plan

    def push_current_goal(self, goal_id: str) -> None:
        """Push a goal ID onto the current-goal stack."""
        self.get_node(goal_id)
        self._current_goal_stack.append(goal_id)
        logger.debug(
            "GoalGraph: pushed %s to current goal stack (depth=%d)",
            goal_id,
            len(self._current_goal_stack),
        )

    def pop_current_goal(self) -> str | None:
        """Pop the current-goal stack, returning None if it is empty."""
        if not self._current_goal_stack:
            return None
        goal_id = self._current_goal_stack.pop()
        logger.debug("GoalGraph: popped %s from current goal stack", goal_id)
        return goal_id

    def peek_current_goal(self) -> str | None:
        """Return the top current-goal ID without removing it."""
        if not self._current_goal_stack:
            return None
        return self._current_goal_stack[-1]

    def as_dict(self) -> dict[str, Any]:
        """Return a lightweight serializable view useful for debugging."""
        return {
            "goals": {
                goal_id: {
                    "status": node.goal.status.value,
                    "parent_id": node.parent.goal.id if node.parent else None,
                    "children": [child.goal.id for child in node.children],
                    "delegate_to": node.delegate_to,
                }
                for goal_id, node in self._nodes.items()
            },
            "edges": [edge.__dict__ for edge in self._edges],
            "current_goal_stack_ids": self.current_goal_stack_ids,
        }

    def _remove_from_current_goal_stack(self, goal_id: str) -> None:
        """Remove all occurrences of `goal_id` from continuation state."""
        if goal_id not in self._current_goal_stack:
            return
        self._current_goal_stack = [
            current_id
            for current_id in self._current_goal_stack
            if current_id != goal_id
        ]


__all__ = [
    "DEFAULT_PARENT_COUPLING",
    "MAX_COUPLING_BASINS",
    "GoalEdge",
    "GoalGraph",
    "GoalNode",
]
