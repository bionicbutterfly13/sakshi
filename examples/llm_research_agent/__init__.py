"""LLM-driven research agent wired through Sakshi's Witness seams.

A bigger sibling of ``toy_blocks_agent``: instead of a toy planner,
the host's cognition is an LLM that decomposes a research question
into subgoals, answers each one, and synthesizes a final report.
Sakshi observes every step — including confidence anomalies — through
its standard ``GoalGraph`` + ``PhaseRegistry`` + ``WriteGuard`` seams.

The ``llm_client`` module defines a small ``LLMClient`` protocol so
tests can run with a deterministic ``MockLLMClient`` while production
use calls the Anthropic SDK via ``AnthropicLLMClient``.
"""

from examples.llm_research_agent.adapters import (
    LoggingResearchEventBus,
    PermissiveResearchWriteGuard,
    ResearchStateStore,
)
from examples.llm_research_agent.agent import (
    AnomalyKind,
    ResearchAgent,
    ResearchReport,
    ResearchTrace,
)
from examples.llm_research_agent.llm_client import (
    AnthropicLLMClient,
    LLMAnswer,
    LLMClient,
    MockLLMClient,
)

__all__ = [
    "AnomalyKind",
    "AnthropicLLMClient",
    "LLMAnswer",
    "LLMClient",
    "LoggingResearchEventBus",
    "MockLLMClient",
    "PermissiveResearchWriteGuard",
    "ResearchAgent",
    "ResearchReport",
    "ResearchStateStore",
    "ResearchTrace",
]
