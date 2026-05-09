from __future__ import annotations

import pytest

from sakshi.goals import (
    AnomalyExplainer,
    BasinProfile,
    DomainRegistry,
    GoalGenerator,
    GoalGraph,
    GoalMonitor,
    GoalOutcomeClosureService,
    GoalOutcomeMemory,
    GoalValidator,
)
from sakshi.interpret import AnomalyEvent
from sakshi.models import (
    ActionExecutionResult,
    ActionExecutionStatus,
    Goal,
    GoalExecutionSummary,
    GoalOutcomeRecord,
    GoalPredicate,
    GoalStatus,
    WorldStateSnapshot,
)


def _goal(
    goal_id: str,
    predicate: str = "INVESTIGATE_ANOMALY",
    *,
    args: dict | None = None,
    goal_type: str = "achievement",
    status: GoalStatus = GoalStatus.ACTIVE,
) -> Goal:
    return Goal(
        id=goal_id,
        predicate=GoalPredicate(name=predicate, args=args or {}),
        goal_type=goal_type,  # type: ignore[arg-type]
        status=status,
    )


class FailingGoalStateStore:
    async def fetch_world_state(self, query: dict) -> WorldStateSnapshot:
        del query
        raise RuntimeError("state store offline")

    async def record_goal_outcome(self, record: GoalOutcomeRecord) -> None:
        del record


@pytest.mark.asyncio
async def test_goal_generator_validates_and_optionally_inserts_into_graph() -> None:
    domain = DomainRegistry()
    domain.add_predicate("INVESTIGATE_ANOMALY")
    validator = GoalValidator(domain)
    graph = GoalGraph()
    generator = GoalGenerator(validator=validator, graph=graph)

    event = AnomalyEvent(
        a_distance=1.2,
        current_activations={"attention": 0.9},
        baseline_mean={"attention": 0.1},
        threshold_used=0.5,
    )
    goal = await generator.generate_from_anomaly(event, add_to_graph=True)

    assert goal is not None
    assert goal.id == "anomaly-goal-0001"
    assert goal.priority == 2
    assert goal.predicate.args["basin"] == "attention"
    assert graph.get_node(goal.id).goal == goal


@pytest.mark.asyncio
async def test_goal_generator_deduplicates_canalization_events() -> None:
    domain = DomainRegistry()
    domain.add_predicate("CANALIZATION_BREAK")
    generator = GoalGenerator(validator=GoalValidator(domain))
    event = {
        "anomaly_type": "CANALIZATION_DETECTED",
        "pattern": "loop",
        "basin_id": "b1",
        "severity": 0.9,
    }

    first = await generator.generate_from_canalization_event(event)
    second = await generator.generate_from_canalization_event(event)

    assert first is not None
    assert first.predicate.name == "CANALIZATION_BREAK"
    assert second is None


@pytest.mark.asyncio
async def test_anomaly_explainer_uses_history_graph_and_basin_profile() -> None:
    graph = GoalGraph()
    graph.add_goal(
        _goal(
            "prior",
            args={"basin": "attention"},
            status=GoalStatus.ABANDONED,
        )
    )
    event = AnomalyEvent(
        a_distance=1.4,
        current_activations={"attention": 1.0, "memory": 0.2},
        baseline_mean={"attention": 0.1, "memory": 0.2},
    )
    history = [
        {
            "current_activations": {"attention": 0.8},
            "baseline_mean": {"attention": 0.1},
        }
    ]

    explanation = await AnomalyExplainer(
        goal_graph=graph,
        basin_profile_provider=lambda _: BasinProfile(
            stability=0.2,
            strength=0.8,
        ),
        anomaly_history=history,
    ).explain(event)

    assert explanation.anomaly_class == "attention"
    assert explanation.recurrence_count == 1
    assert explanation.prior_resolution == "abandoned"
    assert explanation.prior_goal_id == "prior"
    assert explanation.basin_stability == 0.2
    assert explanation.confidence > 0.5


def test_goal_monitor_validity_and_structured_history() -> None:
    monitor = GoalMonitor()
    memory = GoalOutcomeMemory()
    goal = _goal("g", "CLEAR")

    assert (
        monitor.check_validity(goal, WorldStateSnapshot(facts={"CLEAR": {}})).reason
        == "already_satisfied"
    )

    for _ in range(3):
        memory.record(
            GoalOutcomeRecord(
                goal_id="old",
                predicate_name="CLEAR",
                outcome_status=GoalStatus.ABANDONED,
            )
        )

    history_result = monitor.check_outcome_history(goal, memory)
    assert history_result is not None
    assert history_result.reason == "historically_futile"


@pytest.mark.asyncio
async def test_goal_monitor_fail_closed_store_error_marks_goal_invalid() -> None:
    monitor = GoalMonitor(fail_closed_on_store_error=True)
    goal = _goal("g", "CLEAR")

    result = await monitor.check_validity_with_store(
        goal,
        WorldStateSnapshot(facts={}),
        FailingGoalStateStore(),
    )

    assert result.goal_id == "g"
    assert result.is_valid is False
    assert result.reason == "state_store_unavailable"
    assert result.store_error == "state store offline"


@pytest.mark.asyncio
async def test_goal_outcome_closure_mutates_graph_and_records_outcome() -> None:
    graph = GoalGraph()
    memory = GoalOutcomeMemory()
    graph.add_goal(
        _goal(
            "g",
            "CLEAR",
            args={"target": "workspace"},
        )
    )
    closure = GoalOutcomeClosureService(graph=graph, outcome_memory=memory)

    records = await closure.close_from_summary(
        GoalExecutionSummary(
            focus_goal_id="g",
            cycle_id="cycle-1",
            plan_steps=["do_work"],
            action_results=[
                ActionExecutionResult(
                    status=ActionExecutionStatus.COMPLETED,
                    action_type="do_work",
                )
            ],
        )
    )

    assert len(records) == 1
    assert records[0].outcome_status == GoalStatus.ACHIEVED
    assert graph.get_node("g").goal.status == GoalStatus.ACHIEVED
    assert memory.list_records(goal_id="g") == records
    assert graph.get_node("g").goal.metadata["last_outcome"]["cycle_id"] == "cycle-1"


@pytest.mark.asyncio
async def test_goal_outcome_closure_ignores_mixed_completed_failed_actions() -> None:
    graph = GoalGraph()
    memory = GoalOutcomeMemory()
    graph.add_goal(_goal("g", "CLEAR"))
    closure = GoalOutcomeClosureService(graph=graph, outcome_memory=memory)

    records = await closure.close_from_summary(
        GoalExecutionSummary(
            focus_goal_id="g",
            cycle_id="cycle-1",
            plan_steps=["do_work", "verify_work"],
            action_results=[
                ActionExecutionResult(
                    status=ActionExecutionStatus.COMPLETED,
                    action_type="do_work",
                ),
                ActionExecutionResult(
                    status=ActionExecutionStatus.FAILED,
                    action_type="verify_work",
                    error="verification failed",
                ),
            ],
        )
    )

    assert records == []
    assert graph.get_node("g").goal.status == GoalStatus.ACTIVE
    assert memory.list_records(goal_id="g") == []
    assert "last_outcome" not in graph.get_node("g").goal.metadata


@pytest.mark.asyncio
async def test_goal_outcome_closure_ignores_mixed_deferred_completed_actions() -> None:
    graph = GoalGraph()
    memory = GoalOutcomeMemory()
    graph.add_goal(_goal("g", "CLEAR"))
    closure = GoalOutcomeClosureService(graph=graph, outcome_memory=memory)

    records = await closure.close_from_summary(
        GoalExecutionSummary(
            focus_goal_id="g",
            cycle_id="cycle-1",
            plan_steps=["do_work", "hand_off"],
            action_results=[
                ActionExecutionResult(
                    status=ActionExecutionStatus.COMPLETED,
                    action_type="do_work",
                ),
                ActionExecutionResult(
                    status=ActionExecutionStatus.DEFERRED,
                    action_type="hand_off",
                    data={"delegate_to": "operator"},
                ),
            ],
        )
    )

    assert records == []
    assert graph.get_node("g").goal.status == GoalStatus.ACTIVE
    assert memory.list_records(goal_id="g") == []
    assert "last_outcome" not in graph.get_node("g").goal.metadata
