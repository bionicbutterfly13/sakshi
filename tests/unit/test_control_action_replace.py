"""Tests for the REPLACE_MODULE control action and the absence of removed entries."""

from __future__ import annotations

from sakshi.models import ControlAction, ControlActionType


def test_control_action_type_members() -> None:
    assert {member.value for member in ControlActionType} == {
        "STRENGTHEN_MODULE",
        "SUPPRESS_MODULE",
        "ADJUST_PRECISION",
        "SWAP_MODULE",
        "REPLACE_MODULE",
    }


def test_replace_module_action_constructable() -> None:
    action = ControlAction(
        action_type=ControlActionType.REPLACE_MODULE,
        target="planner",
        magnitude=1.0,
        rationale="planner unsuitable for current goal class",
    )
    assert action.action_type == ControlActionType.REPLACE_MODULE
    assert action.target == "planner"


def test_removed_entries_absent() -> None:
    """Guards against re-introducing the externally-imported draft enum entries."""
    names = {member.name for member in ControlActionType}
    assert "TRIGGER_ULTRATHINK" not in names
    assert "TRIGGER_VIGILANCE_FREE_ZONE" not in names
