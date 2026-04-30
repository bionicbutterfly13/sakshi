"""Goal transforms.

Transforms create new goal instances and never mutate the source goal.
They are useful when a host decides a goal is impossible or too vague
in its current shape and wants to retry with changed predicate scope.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from sakshi.models import Goal, GoalPredicate, GoalStatus, WorldStateSnapshot

logger = logging.getLogger(__name__)


class TransformType(StrEnum):
    """Supported goal-transform operations."""

    IDENTITY = "identity"
    GENERALIZE = "generalize"
    SPECIALIZE = "specialize"
    ABSTRACT = "abstract"
    CONCRETIZE = "concretize"


class GoalTransformer:
    """Apply predicate transforms to goals."""

    _SUFFIX_MAP = {
        TransformType.IDENTITY: "_id",
        TransformType.GENERALIZE: "_gen",
        TransformType.SPECIALIZE: "_spec",
        TransformType.ABSTRACT: "_abs",
        TransformType.CONCRETIZE: "_conc",
    }

    def _new_goal_id(self, source_id: str, transform_type: TransformType) -> str:
        suffix = self._SUFFIX_MAP.get(transform_type, "_tx")
        return f"{source_id}{suffix}"

    def _copy_goal(
        self,
        source: Goal,
        new_predicate: GoalPredicate,
        transform_type: TransformType,
    ) -> Goal:
        """Create a new active goal carrying source metadata forward."""
        metadata = dict(source.metadata)
        metadata["transform"] = transform_type.value
        metadata["source_goal_id"] = source.id
        return Goal(
            id=self._new_goal_id(source.id, transform_type),
            predicate=new_predicate,
            basin_name=source.basin_name,
            status=GoalStatus.ACTIVE,
            priority=source.priority,
            prior_type=source.prior_type,
            source=source.source,
            description=f"[{transform_type.value}] {source.description}",
            metadata=metadata,
            goal_type=source.goal_type,
            prior_preference_vector=source.prior_preference_vector,
            expected_efe=source.expected_efe,
        )

    def identity(self, goal: Goal) -> Goal:
        """Return an equivalent active copy of the goal."""
        predicate = GoalPredicate(
            name=goal.predicate.name,
            args=dict(goal.predicate.args),
            domain=goal.predicate.domain,
            expected_state=goal.predicate.expected_state,
        )
        result = self._copy_goal(goal, predicate, TransformType.IDENTITY)
        logger.debug("GoalTransformer.identity: %s -> %s", goal.id, result.id)
        return result

    def generalize(self, goal: Goal) -> Goal:
        """Broaden predicate scope by dropping the last argument."""
        args = dict(goal.predicate.args)
        if args:
            args.pop(list(args.keys())[-1])
        predicate = GoalPredicate(
            name=goal.predicate.name,
            args=args,
            domain=goal.predicate.domain,
            expected_state=goal.predicate.expected_state,
        )
        result = self._copy_goal(goal, predicate, TransformType.GENERALIZE)
        logger.debug("GoalTransformer.generalize: %s -> %s", goal.id, result.id)
        return result

    def specialize(self, goal: Goal, constraints: dict[str, Any]) -> Goal:
        """Narrow predicate scope by adding constraints."""
        predicate = GoalPredicate(
            name=goal.predicate.name,
            args={**goal.predicate.args, **constraints},
            domain=goal.predicate.domain,
            expected_state=goal.predicate.expected_state,
        )
        result = self._copy_goal(goal, predicate, TransformType.SPECIALIZE)
        logger.debug("GoalTransformer.specialize: %s -> %s", goal.id, result.id)
        return result

    def abstract(self, goal: Goal) -> Goal:
        """Remove concrete arguments, leaving the symbolic predicate."""
        predicate = GoalPredicate(
            name=goal.predicate.name,
            args={},
            domain=goal.predicate.domain,
            expected_state=goal.predicate.expected_state,
        )
        result = self._copy_goal(goal, predicate, TransformType.ABSTRACT)
        logger.debug("GoalTransformer.abstract: %s -> %s", goal.id, result.id)
        return result

    def concretize(
        self,
        goal: Goal,
        world_state: WorldStateSnapshot,
    ) -> Goal:
        """Bind a symbolic predicate to args from a world-state snapshot."""
        predicate_name = goal.predicate.name
        if world_state.contains(predicate_name):
            raw = world_state.facts[predicate_name]
            state_args = raw if isinstance(raw, dict) else {"value": raw}
        else:
            state_args = dict(goal.predicate.args)

        predicate = GoalPredicate(
            name=predicate_name,
            args=state_args,
            domain=goal.predicate.domain,
            expected_state=goal.predicate.expected_state,
        )
        result = self._copy_goal(goal, predicate, TransformType.CONCRETIZE)
        logger.debug("GoalTransformer.concretize: %s -> %s", goal.id, result.id)
        return result

    def apply(
        self,
        transform_type: TransformType,
        goal: Goal,
        *,
        constraints: dict[str, Any] | None = None,
        world_state: WorldStateSnapshot | None = None,
    ) -> Goal:
        """Apply a transform by enum value."""
        if transform_type == TransformType.IDENTITY:
            return self.identity(goal)
        if transform_type == TransformType.GENERALIZE:
            return self.generalize(goal)
        if transform_type == TransformType.SPECIALIZE:
            return self.specialize(goal, constraints or {})
        if transform_type == TransformType.ABSTRACT:
            return self.abstract(goal)
        if transform_type == TransformType.CONCRETIZE:
            return self.concretize(goal, world_state or WorldStateSnapshot())
        raise ValueError(f"Unknown TransformType: {transform_type}")


__all__ = ["GoalTransformer", "TransformType"]
