"""Tests for the TaskDecomposer protocol and Action DTO."""

from __future__ import annotations

from typing import Any

from sakshi.plans import Action, TaskDecomposer


def test_action_minimal() -> None:
    a = Action(name="pick_up")
    assert a.name == "pick_up"
    assert a.args == {}
    assert a.description == ""


def test_action_round_trip() -> None:
    original = Action(
        name="move",
        args={"from": "A", "to": "B"},
        description="move arm",
        metadata={"tool": "left_arm"},
    )
    rebuilt = Action.model_validate(original.model_dump())
    assert rebuilt == original


def test_decomposer_protocol_runtime_check() -> None:
    class FixedDecomposer:
        def decompose(
            self,
            task: str,
            world_state: dict[str, Any] | None = None,
        ) -> list[Action]:
            del world_state
            return [Action(name=f"step_for_{task}")]

    decomposer: TaskDecomposer = FixedDecomposer()
    assert isinstance(decomposer, TaskDecomposer)
    actions = decomposer.decompose("build_house")
    assert len(actions) == 1
    assert actions[0].name == "step_for_build_house"


def test_non_decomposer_object_fails_protocol_check() -> None:
    class NotADecomposer:
        def something_else(self) -> None:
            return None

    assert not isinstance(NotADecomposer(), TaskDecomposer)
