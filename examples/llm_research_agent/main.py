"""End-to-end runner for the LLM research agent.

By default uses ``MockLLMClient`` so the demo runs offline. Pass
``--live`` to call Anthropic via ``AnthropicLLMClient`` — that path
requires ``pip install pysakshi[llm-examples]`` and a configured
``ANTHROPIC_API_KEY``.

Run from the repo root::

    python -m examples.llm_research_agent.main
    python -m examples.llm_research_agent.main --live
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from examples.llm_research_agent.adapters import (
    LoggingResearchEventBus,
    PermissiveResearchWriteGuard,
)
from examples.llm_research_agent.agent import ResearchAgent
from examples.llm_research_agent.llm_client import (
    AnthropicLLMClient,
    LLMClient,
    MockLLMClient,
)

DEFAULT_QUESTION = (
    "How should a small Python library decide when to commit to a 1.0 release?"
)


def make_mock_client() -> LLMClient:
    """Canned answers that exercise both the happy path and an anomaly.

    Keys are matched by prefix against the *actual* prompt the agent
    emits, so the leading text mirrors what ``agent.py`` builds.
    Subgoal 2's first reply is deliberately low-confidence so the
    reframe → recover branch fires; subgoals 1 and 3 land cleanly on
    the first try.
    """
    answer_prefix = (
        "Answer this subquestion concisely. End with a line of the form "
        "'Confidence: 0.X' where X reflects how sure you are.\n\n"
        "SUBQUESTION: "
    )
    return MockLLMClient(
        canned={
            "Decompose this research question": (
                "1. What concrete API stability commitments matter most at 1.0?\n"
                "2. How do downstream consumers signal readiness "
                "for a stable pin?\n"
                "3. What internal indicators (test coverage, deprecation "
                "runway) make 1.0 safe?\n"
                "Confidence: 0.9",
                0.9,
            ),
            answer_prefix + "What concrete API": (
                "Public protocol signatures, error types, and the names of any "
                "default policy classes hosts pin against in their adapter layer.\n"
                "Confidence: 0.85",
                0.85,
            ),
            answer_prefix + "How do downstream": (
                "Watch PyPI download trends and issue-tracker discussion volume.\n"
                "Confidence: 0.3",
                0.3,
            ),
            "The previous answer's confidence was low": (
                "Issue volume alone is noisy; surveying a handful of "
                "production adopters for breaking-change tolerance is "
                "more reliable.\n"
                "Confidence: 0.75",
                0.75,
            ),
            answer_prefix + "What internal": (
                "Coverage floor, mypy clean, no breaking changes for one "
                "full minor cycle, and at least one non-toy reference "
                "integration shipped.\n"
                "Confidence: 0.9",
                0.9,
            ),
            "Synthesize a 3-5 sentence final answer": (
                "A small Python library should commit to 1.0 only when (a) it "
                "publishes an explicit SemVer commitment naming its protocol "
                "signatures and default classes, (b) it has surveyed at least "
                "a few real adopters and they have non-trivial tolerance for "
                "breaking changes, and (c) it has held its API stable through "
                "one full minor-release cycle with full coverage and types "
                "clean. Otherwise it should ship more 0.x minors first.",
                0.9,
            ),
        }
    )


async def run(*, live: bool, question: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    client: LLMClient = AnthropicLLMClient() if live else make_mock_client()

    bus = LoggingResearchEventBus()
    write_guard = PermissiveResearchWriteGuard()
    agent = ResearchAgent(llm_client=client, event_bus=bus, write_guard=write_guard)

    report = await agent.research(question)

    print("=== research transcript ===")
    print(f"question: {report.question}")
    print(f"subgoals: {len(report.subgoals)}")
    for trace in report.traces:
        flag = ""
        if trace.anomaly is not None:
            flag = f" [anomaly={trace.anomaly.value}, reframed={trace.reframed}]"
        print(f"  - {trace.subgoal_id}: confidence={trace.answer.confidence:.2f}{flag}")

    print()
    print("--- synthesis ---")
    print(report.synthesis)
    print()
    print(f"published: {report.published}")
    anomaly_events = bus.events_of_type("examples.llm_research_agent.anomaly")
    cycle_events = bus.events_of_type("sakshi.cycle.complete")
    print(f"sakshi cycle.complete events: {len(cycle_events)}")
    print(f"research anomalies observed: {len(anomaly_events)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Anthropic instead of using the mock client",
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args()
    asyncio.run(run(live=args.live, question=args.question))


if __name__ == "__main__":
    main()
