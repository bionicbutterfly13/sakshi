"""Tests for TRAP failure classification."""

from __future__ import annotations

from sakshi.interpret import TRAPDimension, TRAPRouter, classify_failure_mode
from sakshi.models import ControlActionType, FailureMode


def test_explicit_trap_marker_in_description() -> None:
    fm = FailureMode(
        name="x", description="this is a trap:reasoning failure"
    )
    assert classify_failure_mode(fm) == TRAPDimension.REASONING


def test_keyword_match_in_name() -> None:
    fm = FailureMode(name="empty_plan")
    assert classify_failure_mode(fm) == TRAPDimension.REASONING


def test_keyword_match_in_description() -> None:
    fm = FailureMode(name="x", description="sensor reading went stale")
    # Both 'sensor' (perception) and 'stale' (adaptation) are keywords;
    # iteration order over the enum picks transparency/reasoning first.
    classification = classify_failure_mode(fm)
    assert classification in (
        TRAPDimension.PERCEPTION,
        TRAPDimension.ADAPTATION,
    )


def test_override_wins() -> None:
    fm = FailureMode(name="empty_plan")
    assert (
        classify_failure_mode(fm, override=TRAPDimension.PERCEPTION)
        == TRAPDimension.PERCEPTION
    )


def test_unclassified_when_no_signal() -> None:
    fm = FailureMode(name="zorko", description="something")
    assert classify_failure_mode(fm) == TRAPDimension.UNCLASSIFIED


def test_router_default_routing() -> None:
    router = TRAPRouter()
    assert (
        router.recommend(TRAPDimension.REASONING)
        == ControlActionType.SWAP_MODULE
    )
    assert (
        router.recommend(TRAPDimension.PERCEPTION)
        == ControlActionType.STRENGTHEN_MODULE
    )
    assert (
        router.recommend(TRAPDimension.ADAPTATION)
        == ControlActionType.ADJUST_PRECISION
    )
    assert (
        router.recommend(TRAPDimension.TRANSPARENCY)
        == ControlActionType.SUPPRESS_MODULE
    )
    assert router.recommend(TRAPDimension.UNCLASSIFIED) is None


def test_router_custom_routing() -> None:
    router = TRAPRouter({TRAPDimension.REASONING: ControlActionType.REPLACE_MODULE})
    assert (
        router.recommend(TRAPDimension.REASONING)
        == ControlActionType.REPLACE_MODULE
    )
    # Unmodified entries fall back to the default mapping.
    assert (
        router.recommend(TRAPDimension.PERCEPTION)
        == ControlActionType.STRENGTHEN_MODULE
    )
