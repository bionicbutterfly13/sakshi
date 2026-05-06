from __future__ import annotations

from sakshi.goals import (
    DomainRegistry,
    GoalGraph,
    GoalOutcomeMemory,
    GoalSelector,
    GoalTransformer,
    GoalValidator,
    TransformType,
)
from sakshi.models import (
    Goal,
    GoalOutcomeRecord,
    GoalPlan,
    GoalPredicate,
    GoalStatus,
    WorldStateSnapshot,
)


def _goal(
    goal_id: str,
    predicate: str = "CLEAR",
    *,
    args: dict | None = None,
    priority: int = 1,
    basin_name: str = "",
) -> Goal:
    return Goal(
        id=goal_id,
        predicate=GoalPredicate(name=predicate, args=args or {}),
        priority=priority,
        basin_name=basin_name,
    )


def test_goal_graph_frontier_stack_plan_and_coupling() -> None:
    graph = GoalGraph()
    root = _goal("root", basin_name="root-basin", priority=3)
    child = _goal("child", basin_name="child-basin", priority=2)

    graph.add_goal(root)
    graph.add_goal(child, parent_id="root", coupling_strength=0.6)

    assert [goal.id for goal in graph.get_active_frontier()] == ["root"]
    assert graph.to_coupling_matrix() == {("root-basin", "child-basin"): 0.6}

    graph.push_current_goal("root")
    graph.set_plan("root", GoalPlan(goal_id="root", steps=["sense", "act"]))
    graph.mark_achieved("root")

    assert graph.current_goal_stack_ids == []
    assert graph.get_plan("root").steps == ["sense", "act"]
    assert [goal.id for goal in graph.get_active_frontier()] == ["child"]

    graph.delegate_goal("child", "human")
    assert graph.get_node("child").delegate_to == "human"
    assert graph.get_active_frontier() == []


def test_goal_graph_iter_goals_and_status_filter() -> None:
    graph = GoalGraph()
    a = _goal("a")
    b = _goal("b")
    c = _goal("c")

    graph.add_goal(a)
    graph.add_goal(b)
    graph.add_goal(c)
    graph.mark_achieved("a")
    graph.mark_abandoned("b")
    graph.delegate_goal("c", "human")

    assert [g.id for g in graph.iter_goals()] == ["a", "b", "c"]

    terminal = graph.get_goals_by_status(
        {GoalStatus.ACHIEVED, GoalStatus.ABANDONED, GoalStatus.DELEGATED}
    )
    assert {g.id for g in terminal} == {"a", "b", "c"}

    achieved_only = graph.get_goals_by_status({GoalStatus.ACHIEVED})
    assert [g.id for g in achieved_only] == ["a"]

    assert graph.get_goals_by_status(set()) == []


def test_goal_selector_orders_by_mod_selection_score() -> None:
    low = _goal("low", priority=1)
    high = _goal("high", priority=3)
    avoid = Goal(
        id="avoid",
        predicate=GoalPredicate(name="AVOID"),
        goal_type="avoidance",
        priority=1,
    )

    ordered = GoalSelector().select(
        [low, high, avoid],
        performance_map={"low": 0.2, "high": 0.6, "avoid": 0.8},
        limiting_factor_map={"low": 1.0, "high": 1.0, "avoid": 1.0},
    )

    assert [goal.id for goal in ordered] == ["avoid", "high", "low"]


def test_goal_validator_checks_predicate_and_required_args() -> None:
    domain = DomainRegistry()
    domain.add_predicate("ON", required_args=["object", "surface"])
    validator = GoalValidator(domain)

    unknown = validator.validate(_goal("g1", "MISSING"))
    incomplete = validator.validate(_goal("g2", "ON", args={"object": "A"}))
    valid = validator.validate(
        _goal("g3", "ON", args={"object": "A", "surface": "table"})
    )

    assert unknown.is_valid is False
    assert "unknown predicate" in unknown.reason
    assert incomplete.is_valid is False
    assert "missing required args" in incomplete.reason
    assert valid.is_valid is True


def test_goal_transformer_returns_new_active_goals_without_mutating_source() -> None:
    source = Goal(
        id="g",
        predicate=GoalPredicate(name="ON", args={"object": "A", "surface": "table"}),
        status=GoalStatus.ABANDONED,
        description="put A on table",
        metadata={"trace": "source"},
    )
    transformer = GoalTransformer()

    generalized = transformer.generalize(source)
    specialized = transformer.specialize(source, {"color": "red"})
    abstracted = transformer.abstract(source)
    concretized = transformer.apply(
        TransformType.CONCRETIZE,
        source,
        world_state=WorldStateSnapshot(
            facts={"ON": {"object": "B", "surface": "shelf"}}
        ),
    )

    assert source.status == GoalStatus.ABANDONED
    assert generalized.id == "g_gen"
    assert generalized.status == GoalStatus.ACTIVE
    assert generalized.predicate.args == {"object": "A"}
    assert specialized.predicate.args["color"] == "red"
    assert abstracted.predicate.args == {}
    assert concretized.predicate.args == {"object": "B", "surface": "shelf"}
    assert concretized.metadata["source_goal_id"] == "g"


def test_goal_outcome_memory_filters_records() -> None:
    memory = GoalOutcomeMemory()
    achieved = GoalOutcomeRecord(
        goal_id="g1",
        instruction_id="i1",
        predicate_name="CLEAR",
        outcome_status=GoalStatus.ACHIEVED,
    )
    abandoned = GoalOutcomeRecord(
        goal_id="g2",
        instruction_id="i1",
        predicate_name="ON",
        outcome_status=GoalStatus.ABANDONED,
    )

    memory.record(achieved)
    memory.record(abandoned)

    assert memory.list_records(goal_id="g1") == [achieved]
    assert memory.list_records(
        instruction_id="i1",
        outcome_status=GoalStatus.ABANDONED,
    ) == [abandoned]

    memory.clear()
    assert memory.list_records() == []
