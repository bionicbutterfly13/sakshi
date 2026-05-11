"""Research agent: decompose, query, synthesize, watch for anomalies.

The host cognition is an LLM. Every step routes through Sakshi:

- DECOMPOSE creates one root ``Goal`` and N subgoals in a ``GoalGraph``.
- For each subgoal, a fresh ``PhaseRegistry`` cycle records the
  PERCEIVE → PLAN → ACT outputs.
- Low-confidence answers fire a typed ``AnomalyKind.LOW_CONFIDENCE``
  observation on the event bus; the agent re-queries the LLM with a
  reframed prompt once before accepting the best result.
- Synthesis is gated by ``WriteGuard.check`` — a host that wires a
  real safety policy here can veto the published research output.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum

from examples.llm_research_agent.llm_client import LLMAnswer, LLMClient
from sakshi.goals.graph import GoalGraph
from sakshi.models import Goal, GoalPredicate
from sakshi.protocols import EventBus, WriteGuard
from sakshi.registries import PhaseRegistry

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_MAX_SUBGOALS = 3


class AnomalyKind(StrEnum):
    """Anomalies the research agent can emit during a cycle."""

    LOW_CONFIDENCE = "low_confidence"
    EMPTY_DECOMPOSITION = "empty_decomposition"


@dataclass(frozen=True)
class ResearchTrace:
    """Per-subgoal trace: which subgoal, which LLM answer, and any anomaly."""

    subgoal_id: str
    subgoal_text: str
    answer: LLMAnswer
    anomaly: AnomalyKind | None
    reframed: bool


@dataclass
class ResearchReport:
    """End-of-session output the agent publishes through the WriteGuard."""

    question: str
    subgoals: list[str]
    traces: list[ResearchTrace] = field(default_factory=list)
    synthesis: str = ""
    published: bool = False


class ResearchAgent:
    """LLM-driven research agent wrapped by Sakshi.

    Constructor is dependency-injected: the LLM client, the Sakshi
    seams, and the goal graph are all supplied by the harness. The
    agent owns the cognition; Sakshi owns the observation.
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        event_bus: EventBus,
        write_guard: WriteGuard,
        goal_graph: GoalGraph | None = None,
        phase_registry: PhaseRegistry | None = None,
        system_prompt: str | None = None,
        max_subgoals: int = DEFAULT_MAX_SUBGOALS,
    ) -> None:
        self._llm = llm_client
        self._bus = event_bus
        self._write_guard = write_guard
        self._goals = goal_graph if goal_graph is not None else GoalGraph()
        self._phases = (
            phase_registry
            if phase_registry is not None
            else PhaseRegistry(event_bus=event_bus)
        )
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._max_subgoals = max_subgoals
        self._cycle_count = 0

    @property
    def goal_graph(self) -> GoalGraph:
        return self._goals

    async def research(self, question: str) -> ResearchReport:
        """Run the full decompose → query-per-subgoal → synthesize loop."""
        root_goal = Goal(
            id="research-root",
            predicate=GoalPredicate(name="ANSWER", args={"question": question}),
            description=question,
            priority=3,
        )
        self._goals.add_goal(root_goal)
        report = ResearchReport(question=question, subgoals=[])

        subgoals = await self._decompose(question)
        if not subgoals:
            await self._emit_anomaly(AnomalyKind.EMPTY_DECOMPOSITION, root_goal.id)
            self._goals.mark_abandoned(root_goal.id)
            return report

        for index, subgoal_text in enumerate(subgoals):
            subgoal_id = f"research-sub-{index + 1:02d}"
            child = Goal(
                id=subgoal_id,
                predicate=GoalPredicate(name="ANSWER", args={"sub": subgoal_text}),
                description=subgoal_text,
                priority=2,
            )
            self._goals.add_goal(child, parent_id=root_goal.id)
            report.subgoals.append(subgoal_text)

            trace = await self._answer_subgoal(subgoal_id, subgoal_text)
            report.traces.append(trace)

            if trace.answer.confidence >= LOW_CONFIDENCE_THRESHOLD:
                self._goals.mark_achieved(subgoal_id)
            else:
                self._goals.mark_abandoned(subgoal_id)

        report.synthesis = await self._synthesize(question, report.traces)
        report.published = await self._publish(report)
        if report.published:
            self._goals.mark_achieved(root_goal.id)
        else:
            self._goals.mark_abandoned(root_goal.id)
        return report

    async def _decompose(self, question: str) -> list[str]:
        await self._start_cycle()
        await self._phases.record_phase_output(
            "PERCEIVE", {"question": question, "confidence": 1.0}
        )
        prompt = (
            f"Decompose this research question into {self._max_subgoals} "
            f"distinct, concrete subquestions, one per line, numbered.\n\n"
            f"QUESTION: {question}"
        )
        answer = await self._llm.complete(system=self._system_prompt, user=prompt)
        subgoals = _parse_numbered_list(answer.text)[: self._max_subgoals]
        await self._phases.record_phase_output(
            "PLAN",
            {"subgoal_count": len(subgoals), "confidence": answer.confidence},
        )
        await self._phases.record_phase_output(
            "ACT", {"decomposed": True, "confidence": 1.0}
        )
        await self._phases.finalize_cycle()
        return subgoals

    async def _answer_subgoal(
        self, subgoal_id: str, subgoal_text: str
    ) -> ResearchTrace:
        await self._start_cycle()
        await self._phases.record_phase_output(
            "PERCEIVE", {"subgoal": subgoal_text, "confidence": 1.0}
        )

        prompt = (
            f"Answer this subquestion concisely. End with a line of the form "
            f"'Confidence: 0.X' where X reflects how sure you are.\n\n"
            f"SUBQUESTION: {subgoal_text}"
        )
        first_answer = await self._llm.complete(system=self._system_prompt, user=prompt)

        await self._phases.record_phase_output(
            "PLAN", {"strategy": "direct_query", "confidence": first_answer.confidence}
        )

        anomaly: AnomalyKind | None = None
        final_answer = first_answer
        reframed = False
        if first_answer.confidence < LOW_CONFIDENCE_THRESHOLD:
            anomaly = AnomalyKind.LOW_CONFIDENCE
            await self._emit_anomaly(
                anomaly, subgoal_id, confidence=first_answer.confidence
            )
            reframe_prompt = (
                "The previous answer's confidence was low. Reframe the "
                f"subquestion if it is ambiguous, then answer. End with "
                f"'Confidence: 0.X'.\n\nSUBQUESTION: {subgoal_text}"
            )
            second_answer = await self._llm.complete(
                system=self._system_prompt, user=reframe_prompt
            )
            reframed = True
            if second_answer.confidence > first_answer.confidence:
                final_answer = second_answer
            # ``anomaly`` stays set as a historical audit marker even if the
            # reframe recovered confidence above threshold — callers can read
            # ``answer.confidence`` to see whether recovery succeeded.

        await self._phases.record_phase_output(
            "ACT",
            {
                "answer_chars": len(final_answer.text),
                "confidence": final_answer.confidence,
                "reframed": reframed,
            },
        )
        await self._phases.finalize_cycle()
        return ResearchTrace(
            subgoal_id=subgoal_id,
            subgoal_text=subgoal_text,
            answer=final_answer,
            anomaly=anomaly,
            reframed=reframed,
        )

    async def _synthesize(self, question: str, traces: list[ResearchTrace]) -> str:
        await self._start_cycle()
        await self._phases.record_phase_output(
            "PERCEIVE", {"trace_count": len(traces), "confidence": 1.0}
        )
        bullet_lines: list[str] = []
        for trace in traces:
            first_line = (
                trace.answer.text.splitlines()[0] if trace.answer.text else "(empty)"
            )
            bullet_lines.append(f"- {trace.subgoal_text}: {first_line}")
        bullet_summary = "\n".join(bullet_lines)
        prompt = (
            "Synthesize a 3-5 sentence final answer to the original question, "
            "using the bullet findings below. Be specific, do not hedge "
            "unnecessarily.\n\n"
            f"QUESTION: {question}\n\nFINDINGS:\n{bullet_summary}"
        )
        answer = await self._llm.complete(
            system=self._system_prompt, user=prompt, max_tokens=600
        )
        await self._phases.record_phase_output(
            "PLAN", {"strategy": "synthesize", "confidence": answer.confidence}
        )
        await self._phases.record_phase_output(
            "ACT", {"synthesis_chars": len(answer.text), "confidence": 1.0}
        )
        await self._phases.finalize_cycle()
        return answer.text

    async def _publish(self, report: ResearchReport) -> bool:
        permit = await self._write_guard.check(
            "examples.llm_research_agent.publish",
            {
                "question": report.question,
                "subgoal_count": len(report.subgoals),
                "synthesis_chars": len(report.synthesis),
            },
        )
        return permit

    async def _emit_anomaly(
        self,
        kind: AnomalyKind,
        target_goal_id: str,
        *,
        confidence: float | None = None,
    ) -> None:
        payload: dict[str, str | float] = {
            "kind": kind.value,
            "target_goal_id": target_goal_id,
        }
        if confidence is not None:
            payload["confidence"] = confidence
        await self._bus.emit("examples.llm_research_agent.anomaly", payload)

    async def _start_cycle(self) -> None:
        self._cycle_count += 1
        await self._phases.start_cycle(cycle_id=f"research-{self._cycle_count:03d}")


def _parse_numbered_list(text: str) -> list[str]:
    """Pull subgoals out of a numbered LLM response.

    Single-line free-text replies are not a valid decomposition and
    return an empty list; the agent treats that as an empty
    decomposition anomaly.
    """
    items: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^(\d+)[.)]\s+(.+)$", line)
        if match:
            items.append(match.group(2).strip())
    if not items:
        candidates = [line.strip() for line in text.splitlines() if line.strip()]
        if len(candidates) < 2:
            return []
        items = candidates
    # filter out goals that are mostly identical
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        key = re.sub(r"[^a-z0-9]+", "", item.lower())[:32]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


DEFAULT_SYSTEM_PROMPT = (
    "You are a careful research assistant. When you do not know the answer to "
    "a question, say so with low confidence. When asked to decompose a "
    "question, emit a numbered list of distinct, concrete subquestions. "
    "Always end any answer that asks for confidence with a line of the form "
    "'Confidence: 0.X'."
)
