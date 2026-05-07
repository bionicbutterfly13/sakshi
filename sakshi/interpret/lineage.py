"""Goal-lineage auditor.

Goals do not stay still. ``GoalTransformer`` produces children that
generalize, specialize, abstract, or concretize their parents; the
metacognitive layer can chain transforms across many cycles. After a
long agent run, the goal currently being pursued may bear little
resemblance to the one the host originally posted.

The ``GoalLineageAuditor`` walks the transform chain (recorded as
``source_goal_id`` and ``transform`` keys in ``Goal.metadata``) and
reports a typed signal: how deep is the lineage, how many times did
it abstract or generalize away from the original, did it ever return
to the predicate name the host first registered. Hosts use the report
to decide whether the agent is still pursuing the assigned mission or
has drifted into something the operator should review.

This is a pre-INTEND gate in spirit, but the auditor itself never
intervenes — it returns a typed report. Acting on the report is the
host's call.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from sakshi.models.goal import Goal

METADATA_TRANSFORM_KEY = "transform"
METADATA_SOURCE_KEY = "source_goal_id"

DEFAULT_DEPTH_WARN_THRESHOLD = 3
DEFAULT_DEPTH_DRIFT_THRESHOLD = 5
WIDENING_TRANSFORMS: tuple[str, ...] = ("generalize", "abstract")


class LineageVerdict(StrEnum):
    """Three-band drift classification."""

    ALIGNED = "aligned"
    WARN = "warn"
    DRIFTED = "drifted"


@dataclass(frozen=True)
class LineageReport:
    """What the auditor says about one goal's chain back to its origin."""

    goal_id: str
    origin_goal_id: str
    depth: int
    widening_steps: int
    transform_chain: tuple[str, ...]
    predicate_changed: bool
    verdict: LineageVerdict


class GoalLineageAuditor:
    """Walks the transform chain on a single goal.

    Args:
        depth_warn_threshold: Lineage depth at which the verdict turns
            from ``ALIGNED`` to ``WARN``.
        depth_drift_threshold: Depth at which the verdict turns to
            ``DRIFTED``. Must be greater than ``depth_warn_threshold``.
        widening_transforms: Transform names that count as movement
            *away* from the original goal (default: ``generalize`` and
            ``abstract``). ``specialize`` and ``concretize`` are
            considered re-tightenings and do not count.
    """

    def __init__(
        self,
        *,
        depth_warn_threshold: int = DEFAULT_DEPTH_WARN_THRESHOLD,
        depth_drift_threshold: int = DEFAULT_DEPTH_DRIFT_THRESHOLD,
        widening_transforms: tuple[str, ...] = WIDENING_TRANSFORMS,
    ) -> None:
        if depth_warn_threshold < 1:
            raise ValueError("depth_warn_threshold must be at least 1")
        if depth_drift_threshold <= depth_warn_threshold:
            raise ValueError(
                "depth_drift_threshold must exceed depth_warn_threshold"
            )
        self._warn = depth_warn_threshold
        self._drift = depth_drift_threshold
        self._widening = set(widening_transforms)

    def audit(
        self,
        goal: Goal,
        goals_by_id: Mapping[str, Goal],
    ) -> LineageReport:
        """Walk the lineage and produce a typed report.

        ``goals_by_id`` is the host's lookup over the goal graph
        (typically ``GoalGraph.iter_goals()`` indexed by ``id``). The
        auditor never holds a reference to the graph itself.
        """
        chain: list[str] = []
        widening_steps = 0
        current: Goal = goal
        seen: set[str] = set()
        depth = 0

        while True:
            metadata = current.metadata or {}
            transform = metadata.get(METADATA_TRANSFORM_KEY)
            source_id = metadata.get(METADATA_SOURCE_KEY)
            if transform is None or source_id is None:
                break
            if source_id in seen:
                # Defensive: cyclic chain. Stop walking.
                break
            seen.add(source_id)
            chain.append(str(transform))
            if str(transform) in self._widening:
                widening_steps += 1
            parent = goals_by_id.get(str(source_id))
            depth += 1
            if parent is None:
                # Lineage broken (parent garbage-collected); use
                # source_id as the recorded origin.
                return LineageReport(
                    goal_id=goal.id,
                    origin_goal_id=str(source_id),
                    depth=depth,
                    widening_steps=widening_steps,
                    transform_chain=tuple(chain),
                    predicate_changed=True,
                    verdict=self._verdict(depth),
                )
            current = parent

        origin_predicate = current.predicate.name
        predicate_changed = origin_predicate != goal.predicate.name
        return LineageReport(
            goal_id=goal.id,
            origin_goal_id=current.id,
            depth=depth,
            widening_steps=widening_steps,
            transform_chain=tuple(chain),
            predicate_changed=predicate_changed,
            verdict=self._verdict(depth),
        )

    def _verdict(self, depth: int) -> LineageVerdict:
        if depth >= self._drift:
            return LineageVerdict.DRIFTED
        if depth >= self._warn:
            return LineageVerdict.WARN
        return LineageVerdict.ALIGNED


__all__ = [
    "DEFAULT_DEPTH_DRIFT_THRESHOLD",
    "DEFAULT_DEPTH_WARN_THRESHOLD",
    "WIDENING_TRANSFORMS",
    "GoalLineageAuditor",
    "LineageReport",
    "LineageVerdict",
]
