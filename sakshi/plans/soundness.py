"""Plan soundness verification.

Validates plan steps against preconditions, ordering constraints, and
resource capacities before a host commits execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SOUNDNESS_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class PlanConstraint:
    """Structured constraint attached to one plan step."""

    step_id: str
    preconditions: list[str] = field(default_factory=list)
    resource_requirements: dict[str, float] = field(default_factory=dict)
    must_follow: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SoundnessCheckResult:
    """Result of a plan soundness check."""

    is_sound: bool
    violations: list[str] = field(default_factory=list)
    blocked_steps: list[str] = field(default_factory=list)
    confidence: float = 1.0


class PlanSoundnessVerifier:
    """Validate plan steps against world state and resource constraints."""

    def verify(
        self,
        plan_steps: list[dict[str, Any]],
        world_state: dict[str, Any] | None = None,
        available_resources: dict[str, float] | None = None,
    ) -> SoundnessCheckResult:
        """Validate a plan and return a `SoundnessCheckResult`."""
        if not plan_steps:
            return SoundnessCheckResult(is_sound=True, confidence=1.0)

        violations: list[str] = []
        blocked_steps: list[str] = []
        world_state = world_state or {}
        resources = dict(available_resources or {})
        seen_steps: list[str] = []
        resource_usage: dict[str, float] = {}

        for index, step in enumerate(plan_steps):
            step_id = str(step.get("step_id", step.get("action", f"step_{index}")))

            for precondition in step.get("preconditions", []):
                if not world_state.get(precondition, False):
                    violations.append(
                        f"Step {step_id!r}: precondition {precondition!r} not satisfied"
                    )
                    blocked_steps.append(step_id)

            must_follow = step.get("must_follow")
            if must_follow and must_follow not in seen_steps:
                violations.append(
                    f"Step {step_id!r}: ordering violated; "
                    f"requires {must_follow!r} first"
                )
                blocked_steps.append(step_id)

            if must_follow == step_id:
                violations.append(f"Step {step_id!r}: circular ordering constraint")
                blocked_steps.append(step_id)

            for resource, amount in step.get("resources", {}).items():
                amount = float(amount)
                resource_usage[resource] = resource_usage.get(resource, 0.0) + amount
                if resources and resource in resources:
                    if resource_usage[resource] > resources[resource]:
                        violations.append(
                            f"Step {step_id!r}: resource {resource!r} exceeds "
                            f"capacity ({resource_usage[resource]:.2f} > "
                            f"{resources[resource]:.2f})"
                        )
                        blocked_steps.append(step_id)

            seen_steps.append(step_id)

        unique_blocked = sorted(set(blocked_steps))
        confidence = max(0.0, 1.0 - (len(unique_blocked) / max(len(plan_steps), 1)))

        if violations:
            logger.warning(
                "PlanSoundnessVerifier: %d violation(s) in %d-step plan: %s",
                len(violations),
                len(plan_steps),
                "; ".join(violations[:3]),
            )

        return SoundnessCheckResult(
            is_sound=not violations,
            violations=violations,
            blocked_steps=unique_blocked,
            confidence=confidence,
        )


__all__ = [
    "SOUNDNESS_CONFIDENCE_THRESHOLD",
    "PlanConstraint",
    "PlanSoundnessVerifier",
    "SoundnessCheckResult",
]
