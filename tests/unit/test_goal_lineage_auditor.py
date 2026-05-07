"""Tests for GoalLineageAuditor."""

from __future__ import annotations

import pytest

from sakshi.goals.transformer import GoalTransformer
from sakshi.interpret import GoalLineageAuditor, LineageVerdict
from sakshi.models import Goal, GoalPredicate


def _root() -> Goal:
    return Goal(
        id="g-root",
        predicate=GoalPredicate(name="ON", args={"x": "A", "y": "B"}),
    )


def test_aligned_root_goal_has_zero_depth() -> None:
    goal = _root()
    auditor = GoalLineageAuditor()
    report = auditor.audit(goal, {goal.id: goal})
    assert report.depth == 0
    assert report.origin_goal_id == goal.id
    assert report.transform_chain == ()
    assert report.predicate_changed is False
    assert report.verdict == LineageVerdict.ALIGNED


def test_short_lineage_stays_aligned() -> None:
    transformer = GoalTransformer()
    root = _root()
    child = transformer.specialize(root, {"surface": "table"})
    by_id = {root.id: root, child.id: child}
    auditor = GoalLineageAuditor()
    report = auditor.audit(child, by_id)
    assert report.depth == 1
    assert report.origin_goal_id == root.id
    assert report.transform_chain == ("specialize",)
    assert report.verdict == LineageVerdict.ALIGNED


def test_repeated_widening_triggers_drift() -> None:
    transformer = GoalTransformer()
    root = _root()
    g1 = transformer.generalize(root)
    g2 = transformer.generalize(g1)
    g3 = transformer.abstract(g2)
    g4 = transformer.abstract(g3)
    g5 = transformer.abstract(g4)
    by_id = {g.id: g for g in (root, g1, g2, g3, g4, g5)}
    auditor = GoalLineageAuditor()
    report = auditor.audit(g5, by_id)
    assert report.depth == 5
    assert report.widening_steps == 5
    assert report.verdict == LineageVerdict.DRIFTED
    assert report.origin_goal_id == root.id
    assert report.predicate_changed is False  # name is preserved across transforms


def test_warn_band_between_thresholds() -> None:
    transformer = GoalTransformer()
    root = _root()
    g1 = transformer.generalize(root)
    g2 = transformer.generalize(g1)
    g3 = transformer.generalize(g2)
    by_id = {g.id: g for g in (root, g1, g2, g3)}
    auditor = GoalLineageAuditor(depth_warn_threshold=3, depth_drift_threshold=5)
    report = auditor.audit(g3, by_id)
    assert report.depth == 3
    assert report.verdict == LineageVerdict.WARN


def test_broken_lineage_returns_recorded_origin() -> None:
    transformer = GoalTransformer()
    root = _root()
    child = transformer.generalize(root)
    # Parent garbage-collected; child's metadata still claims root as source.
    by_id = {child.id: child}
    auditor = GoalLineageAuditor()
    report = auditor.audit(child, by_id)
    assert report.origin_goal_id == root.id
    assert report.predicate_changed is True


def test_invalid_thresholds_rejected() -> None:
    with pytest.raises(ValueError):
        GoalLineageAuditor(depth_warn_threshold=0)
    with pytest.raises(ValueError):
        GoalLineageAuditor(depth_warn_threshold=5, depth_drift_threshold=5)
