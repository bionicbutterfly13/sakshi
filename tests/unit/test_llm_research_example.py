"""Tests for the llm_research_agent example.

These run entirely against ``MockLLMClient`` so no network, no API
key, and no ``anthropic`` install is required. They pin the agent's
Sakshi seam contracts, not the LLM's output.
"""

from __future__ import annotations

import pytest

from examples.llm_research_agent import (
    AnomalyKind,
    LoggingResearchEventBus,
    MockLLMClient,
    PermissiveResearchWriteGuard,
    ResearchAgent,
)
from examples.llm_research_agent.llm_client import _extract_confidence
from examples.llm_research_agent.main import make_mock_client


def test_extract_confidence_finds_trailing_marker() -> None:
    text = "answer body\nmore body\nConfidence: 0.83\n"
    assert _extract_confidence(text) == pytest.approx(0.83)


def test_extract_confidence_falls_back_to_neutral() -> None:
    assert _extract_confidence("answer with no marker") == 0.5


def test_extract_confidence_clamps_out_of_range_values() -> None:
    assert _extract_confidence("Confidence: -0.4") == 0.0
    assert _extract_confidence("Confidence: 1.7") == 1.0


@pytest.mark.asyncio
async def test_mock_client_falls_back_on_unknown_prompt() -> None:
    client = MockLLMClient(canned={"hello": ("hi back\nConfidence: 0.9", 0.9)})
    miss = await client.complete(system="", user="nothing matches this")
    assert miss.cache_hit is False
    assert miss.confidence == 0.1


@pytest.mark.asyncio
async def test_research_run_decomposes_and_recovers_from_anomaly() -> None:
    bus = LoggingResearchEventBus()
    guard = PermissiveResearchWriteGuard()
    agent = ResearchAgent(
        llm_client=make_mock_client(),
        event_bus=bus,
        write_guard=guard,
    )

    report = await agent.research(
        "How should a small Python library decide when to commit to a 1.0 release?"
    )

    assert len(report.subgoals) == 3
    assert len(report.traces) == 3
    assert report.published is True
    assert any(trace.anomaly == AnomalyKind.LOW_CONFIDENCE for trace in report.traces)
    assert any(trace.reframed for trace in report.traces)

    # WriteGuard fired exactly once on publish.
    assert len(guard.checks) == 1
    origin, payload = guard.checks[0]
    assert origin == "examples.llm_research_agent.publish"
    assert payload["subgoal_count"] == 3

    # 1 decompose + 3 subgoal + 1 synthesis = 5 cycle.complete events.
    cycle_events = bus.events_of_type("sakshi.cycle.complete")
    assert len(cycle_events) == 5

    # Exactly one anomaly observed (sub-02 fires once before reframing).
    anomaly_events = bus.events_of_type("examples.llm_research_agent.anomaly")
    assert len(anomaly_events) == 1
    assert anomaly_events[0]["kind"] == AnomalyKind.LOW_CONFIDENCE.value


@pytest.mark.asyncio
async def test_research_goal_graph_records_full_decomposition() -> None:
    bus = LoggingResearchEventBus()
    guard = PermissiveResearchWriteGuard()
    agent = ResearchAgent(
        llm_client=make_mock_client(),
        event_bus=bus,
        write_guard=guard,
    )

    report = await agent.research(
        "How should a small Python library decide when to commit to a 1.0 release?"
    )
    del report

    goals = agent.goal_graph.iter_goals()
    assert {goal.id for goal in goals} == {
        "research-root",
        "research-sub-01",
        "research-sub-02",
        "research-sub-03",
    }
    root = agent.goal_graph.get_node("research-root").goal
    assert root.status.name == "ACHIEVED"


@pytest.mark.asyncio
async def test_research_aborts_when_decomposition_is_empty() -> None:
    """If the LLM yields no usable subgoals, the root goal must be abandoned."""
    empty_client = MockLLMClient(canned={})
    bus = LoggingResearchEventBus()
    guard = PermissiveResearchWriteGuard()
    agent = ResearchAgent(llm_client=empty_client, event_bus=bus, write_guard=guard)

    report = await agent.research("ambiguous question")

    assert report.subgoals == []
    assert report.published is False
    anomalies = bus.events_of_type("examples.llm_research_agent.anomaly")
    assert any(a["kind"] == AnomalyKind.EMPTY_DECOMPOSITION.value for a in anomalies)
