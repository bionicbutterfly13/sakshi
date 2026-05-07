"""Goal-constraint DTO.

A lightweight reification of the three predicate sets that bound goal
feasibility — initial state, safety constraints, goal conditions —
plus a fourth flag that marks a constraint as integrity-critical.

Integrity-critical constraints cannot be silently dropped by a
self-modifying agent. The downstream modification-integrity guard (in
the defensive guards layer) reads ``integrity_critical`` to decide
whether a proposed plan or goal rewrite that removes the constraint
should be permitted. Hosts that do not run a modification guard can
still rely on the flag as a reviewability signal in audit logs.

This module deliberately avoids LTL synthesis or solver dependencies.
Predicates are typed as plain strings so hosts can plug in whatever
predicate language their planner already understands.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GoalConstraint:
    """Bounds on a goal's feasibility.

    Attributes:
        initial_state: Predicates that must hold in the initial state
            for the goal to be considered well-posed.
        safety_constraints: Predicates that must remain true throughout
            execution. Violation should trigger a soundness-check
            failure or a meta-cycle intervention.
        goal_conditions: Predicates that, when all satisfied, mean the
            goal is achieved.
        integrity_critical: When ``True``, a self-modifying agent's
            modification guard MUST refuse to drop or relax this
            constraint. Hosts that lack a modification guard can use
            the flag as an explicit audit signal.
    """

    initial_state: tuple[str, ...] = ()
    safety_constraints: tuple[str, ...] = ()
    goal_conditions: tuple[str, ...] = ()
    integrity_critical: bool = False
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


__all__ = ["GoalConstraint"]
