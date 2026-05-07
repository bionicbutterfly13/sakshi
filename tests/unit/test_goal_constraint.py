"""Tests for GoalConstraint."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sakshi.plans import GoalConstraint


def test_default_constraint_is_empty_and_not_critical() -> None:
    c = GoalConstraint()
    assert c.initial_state == ()
    assert c.safety_constraints == ()
    assert c.goal_conditions == ()
    assert c.integrity_critical is False


def test_constraint_carries_all_four_fields() -> None:
    c = GoalConstraint(
        initial_state=("at(robot, lab)",),
        safety_constraints=("not on_fire(*)",),
        goal_conditions=("on(A, B)",),
        integrity_critical=True,
        description="block-stacking with fire-safety guard",
    )
    assert c.initial_state == ("at(robot, lab)",)
    assert c.safety_constraints == ("not on_fire(*)",)
    assert c.goal_conditions == ("on(A, B)",)
    assert c.integrity_critical is True


def test_constraint_is_frozen() -> None:
    c = GoalConstraint()
    with pytest.raises(FrozenInstanceError):
        c.integrity_critical = True  # type: ignore[misc]


def test_integrity_critical_flag_visible_to_consumers() -> None:
    """Phase A → Phase F handshake: a downstream guard inspects the flag."""
    c_critical = GoalConstraint(integrity_critical=True)
    c_normal = GoalConstraint(integrity_critical=False)

    def stub_modification_guard(constraint: GoalConstraint) -> bool:
        """Toy stand-in for ModificationIntegrityGuard."""
        return not constraint.integrity_critical

    assert stub_modification_guard(c_normal) is True
    assert stub_modification_guard(c_critical) is False
