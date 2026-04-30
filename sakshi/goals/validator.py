"""Goal structural validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sakshi.models import Goal, WorldStateSnapshot

logger = logging.getLogger(__name__)


class DomainRegistry:
    """Registry of valid predicates and required predicate arguments."""

    def __init__(self) -> None:
        self.predicates: dict[str, list[str]] = {}

    def add_predicate(
        self,
        name: str,
        required_args: list[str] | None = None,
    ) -> None:
        """Register a valid predicate name and optional required args."""
        self.predicates[name] = required_args if required_args is not None else []
        logger.debug(
            "DomainRegistry: registered predicate %r (required_args=%s)",
            name,
            self.predicates[name],
        )

    def is_known(self, predicate_name: str) -> bool:
        """True if the predicate name is registered."""
        return predicate_name in self.predicates

    def required_args_for(self, predicate_name: str) -> list[str]:
        """Return required args for a predicate, or an empty list."""
        return list(self.predicates.get(predicate_name, []))


@dataclass(frozen=True)
class GoalValidationResult:
    """Result of a structural goal validation check."""

    is_valid: bool
    reason: str
    goal_id: str = ""


class GoalValidator:
    """Validate goals before insertion into a graph.

    This validator checks predicate membership and required argument
    presence. It deliberately does not inspect runtime world state;
    world-state validity belongs to monitoring logic behind a host's
    `GoalStateStore`.
    """

    def __init__(self, domain: DomainRegistry) -> None:
        self._domain = domain

    @property
    def domain(self) -> DomainRegistry:
        """The domain registry backing this validator."""
        return self._domain

    def validate(
        self,
        goal: Goal,
        world_state: WorldStateSnapshot | None = None,
    ) -> GoalValidationResult:
        """Validate a goal against the domain registry.

        `world_state` is accepted for API symmetry with monitors and
        future host adapters, but structural validation does not use it.
        """
        del world_state

        predicate_name = goal.predicate.name
        if not self._domain.is_known(predicate_name):
            logger.debug(
                "GoalValidator: rejected goal %s, unknown predicate %r",
                goal.id,
                predicate_name,
            )
            return GoalValidationResult(
                is_valid=False,
                reason=f"unknown predicate {predicate_name!r}",
                goal_id=goal.id,
            )

        required = self._domain.required_args_for(predicate_name)
        goal_args = goal.predicate.args or {}
        missing = [arg for arg in required if arg not in goal_args]
        if missing:
            logger.debug(
                "GoalValidator: rejected goal %s, missing args %s for %r",
                goal.id,
                missing,
                predicate_name,
            )
            return GoalValidationResult(
                is_valid=False,
                reason=(
                    f"missing required args {missing} for predicate {predicate_name!r}"
                ),
                goal_id=goal.id,
            )

        return GoalValidationResult(
            is_valid=True,
            reason="valid",
            goal_id=goal.id,
        )


__all__ = ["DomainRegistry", "GoalValidationResult", "GoalValidator"]
