"""Instruction ingest service.

Turns free-form host instructions into graph-backed goals with stable
lineage metadata and short-window deduplication.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from sakshi.goals import GoalGraph
from sakshi.models import Goal, GoalPredicate

logger = logging.getLogger(__name__)


class InstructionIngestRequest(BaseModel):
    """Request payload for canonical instruction ingest."""

    text: str = ""
    source: str = "user_request"
    priority: int = 2
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstructionIngestResult(BaseModel):
    """Structured result for instruction ingest."""

    accepted: bool
    reason: str
    instruction_id: str | None = None
    goal_id: str | None = None
    source: str | None = None
    validation_errors: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class _DedupRecord:
    instruction_id: str
    goal_id: str
    created_at: datetime


class InstructionIngestService:
    """Canonical instruction ingress for Sakshi goals."""

    def __init__(
        self,
        *,
        goal_graph: GoalGraph,
        dedup_window: timedelta = timedelta(minutes=5),
    ) -> None:
        self._goal_graph = goal_graph
        self._dedup_window = dedup_window
        self._recent_by_signature: dict[str, _DedupRecord] = {}

    async def ingest_instruction(
        self,
        request: InstructionIngestRequest,
    ) -> InstructionIngestResult:
        """Validate, deduplicate, and insert a goal into the graph."""
        errors = self._validate(request)
        if errors:
            return InstructionIngestResult(
                accepted=False,
                reason="validation_failed",
                validation_errors=errors,
                source=request.source,
            )

        signature = self._signature(request)
        dedup_hit = self._check_dedup(signature)
        if dedup_hit is not None:
            return InstructionIngestResult(
                accepted=False,
                reason="duplicate_instruction",
                instruction_id=dedup_hit.instruction_id,
                goal_id=dedup_hit.goal_id,
                source=request.source,
            )

        goal_id = uuid4().hex
        instruction_id = uuid4().hex
        goal = Goal(
            id=goal_id,
            predicate=GoalPredicate(
                name="FOLLOW_INSTRUCTION",
                args={
                    "instruction_text": request.text.strip(),
                    "instruction_source": request.source,
                },
            ),
            priority=request.priority,
            source=f"{request.source}_instruction",
            prior_type="D",
            description=request.text.strip(),
            metadata={
                "instruction_id": instruction_id,
                "instruction_source": request.source,
                **request.metadata,
            },
        )

        self._goal_graph.add_goal(goal)
        self._recent_by_signature[signature] = _DedupRecord(
            instruction_id=instruction_id,
            goal_id=goal_id,
            created_at=datetime.now(UTC),
        )
        logger.info("InstructionIngestService: created goal %s", goal_id)

        return InstructionIngestResult(
            accepted=True,
            reason="created",
            instruction_id=instruction_id,
            goal_id=goal_id,
            source=request.source,
        )

    def _validate(self, request: InstructionIngestRequest) -> list[str]:
        errors: list[str] = []
        if not request.text or not request.text.strip():
            errors.append("text must be non-empty")
        if request.priority < 1 or request.priority > 3:
            errors.append("priority must be between 1 and 3")
        if not request.source or not str(request.source).strip():
            errors.append("source must be non-empty")
        return errors

    def _signature(self, request: InstructionIngestRequest) -> str:
        normalized = f"{request.source.strip().lower()}::{request.text.strip().lower()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _check_dedup(self, signature: str) -> _DedupRecord | None:
        existing = self._recent_by_signature.get(signature)
        if existing is None:
            return None
        if self._dedup_window <= timedelta(seconds=0):
            return None
        if datetime.now(UTC) - existing.created_at <= self._dedup_window:
            return existing
        return None


__all__ = [
    "InstructionIngestRequest",
    "InstructionIngestResult",
    "InstructionIngestService",
]
