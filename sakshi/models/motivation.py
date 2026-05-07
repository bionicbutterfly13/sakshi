"""Motivation typing.

Sakshi does not generate intrinsic motivations on its own — the host
does. What Sakshi provides is the *typed surface* hosts use to:

* tag every goal with the motivation that produced it (audit trail),
* declare a creativity envelope that bounds what kinds of novel goals
  the host's motivation system is allowed to propose,
* expose aggregate metrics that let an operator spot a single drive
  dominating or motivation drifting,
* run an immutable log of motivation events.

The Witness-pattern stance: Sakshi observes the host's motivation
record, validates against host-declared envelopes, and reports —
never generates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MotivationType(StrEnum):
    """Coarse taxonomy of motivation sources.

    Hosts tag every intrinsic goal with the type that produced it so
    audit logs and the metrics view show motivation diversity without
    the host having to reverse-engineer it from goal predicates.
    """

    ACHIEVEMENT = "achievement"
    AFFILIATION = "affiliation"
    POWER = "power"
    NOVELTY = "novelty"
    COMPETENCE = "competence"
    SURPRISE = "surprise"
    EXTRINSIC = "extrinsic"
    UNCLASSIFIED = "unclassified"


class MotivationEvent(BaseModel):
    """One immutable record describing a motivation activation.

    Hosts emit one of these every time their motivation system
    produces (or refuses to produce) a goal. The auditor stores them.
    """

    motivation_type: MotivationType
    goal_id: str | None = Field(
        default=None,
        description=(
            "ID of the goal produced by this motivation. ``None`` "
            "when the activation was rejected by the envelope."
        ),
    )
    cycle_id: str | None = None
    accepted: bool = Field(
        default=True,
        description=(
            "True if the resulting goal was accepted into the goal "
            "graph; False if the envelope or relevance filter "
            "rejected it."
        ),
    )
    reason: str = ""
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ComputationalMotivationMetrics:
    """Summary of motivation quality over a recent window.

    All four fields are bounded scalars in [0, 1] so a host can route
    on them with simple thresholds.

    * ``diversity_score``: Shannon entropy of the motivation-type
      distribution divided by ``log2(num_types_present)``. ``1.0``
      means every type fired equally; lower means a single drive is
      dominating.
    * ``stability_score``: ``1.0 - (acceptance-rate variance over a
      sliding window)``. Lower means the host is oscillating between
      accepting and rejecting motivation impulses.
    * ``risk_assessment``: rolling fraction of events tagged ``POWER``
      or ``SURPRISE`` (the two motivation classes flagged in the
      literature as risk-correlated). Higher means more risk-seeking
      motivation.
    * ``communication_cost``: rolling fraction of events with a
      non-empty ``reason`` field. Approximates how much human-facing
      narrative the motivation system is producing.
    """

    diversity_score: float
    stability_score: float
    risk_assessment: float
    communication_cost: float

    def __post_init__(self) -> None:
        for label, value in (
            ("diversity_score", self.diversity_score),
            ("stability_score", self.stability_score),
            ("risk_assessment", self.risk_assessment),
            ("communication_cost", self.communication_cost),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be in [0, 1], got {value!r}")


@dataclass(frozen=True)
class CreativityEnvelope:
    """Bounds on the host's motivation creativity.

    The envelope is host-declared. Sakshi observes a proposed
    goal-from-motivation against it; goals that fall outside the
    envelope are rejected and the rejection is logged.

    Attributes:
        allowed_predicates: Predicate names a motivated goal MAY use.
            Empty tuple means no constraint.
        forbidden_attributes: Predicate-argument keys the goal MUST
            NOT contain. The classic example is ``"target_human"`` for
            a host that wants to forbid power-motivated goals targeting
            humans.
        max_novelty_score: Highest acceptable novelty scalar (host-
            scored, in [0, 1]). Defaults to 1.0 (no cap).
        forbidden_motivation_types: Motivation types forbidden from
            generating goals at all. ``POWER`` is a common entry for
            constrained deployments.
    """

    allowed_predicates: tuple[str, ...] = ()
    forbidden_attributes: tuple[str, ...] = ()
    max_novelty_score: float = 1.0
    forbidden_motivation_types: tuple[MotivationType, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_novelty_score <= 1.0:
            raise ValueError("max_novelty_score must be in [0, 1]")


@dataclass(frozen=True)
class EnvelopeVerdict:
    """Result of running a candidate against ``CreativityEnvelope``."""

    accepted: bool
    reason: str = ""
    violated_field: str = ""

    @classmethod
    def ok(cls) -> EnvelopeVerdict:
        return cls(accepted=True, reason="within envelope")


def evaluate_envelope(
    *,
    envelope: CreativityEnvelope,
    motivation_type: MotivationType,
    predicate_name: str,
    predicate_args: dict[str, object] | None = None,
    novelty_score: float = 0.0,
) -> EnvelopeVerdict:
    """Decide whether a candidate motivation+goal fits the envelope.

    The function is pure: same inputs produce the same verdict.
    Hosts pass the verdict through ``MotivationAuditor`` and to their
    own goal-acceptance logic.
    """
    if motivation_type in envelope.forbidden_motivation_types:
        return EnvelopeVerdict(
            accepted=False,
            reason=(f"{motivation_type.value} motivation forbidden by envelope"),
            violated_field="motivation_type",
        )
    if (
        envelope.allowed_predicates
        and predicate_name not in envelope.allowed_predicates
    ):
        return EnvelopeVerdict(
            accepted=False,
            reason=(f"predicate {predicate_name!r} not in allowed list"),
            violated_field="predicate_name",
        )
    if not 0.0 <= novelty_score <= 1.0:
        raise ValueError("novelty_score must be in [0, 1]")
    if novelty_score > envelope.max_novelty_score:
        return EnvelopeVerdict(
            accepted=False,
            reason=(
                f"novelty {novelty_score:.2f} exceeds envelope cap "
                f"{envelope.max_novelty_score:.2f}"
            ),
            violated_field="novelty_score",
        )
    if predicate_args:
        for forbidden in envelope.forbidden_attributes:
            if forbidden in predicate_args:
                return EnvelopeVerdict(
                    accepted=False,
                    reason=(f"goal contains forbidden attribute {forbidden!r}"),
                    violated_field=forbidden,
                )
    return EnvelopeVerdict.ok()


@dataclass
class GoalRelevanceFilter:
    """Filter a motivated goal against a host-defined value taxonomy.

    Hosts declare a tuple of ``allowed_value_tags``. A goal proposed
    by the motivation system carries one or more value tags (in
    ``Goal.metadata['value_tags']`` by convention); the filter accepts
    only goals whose tags overlap with the allowed list.

    Attributes:
        allowed_value_tags: Tags the host considers organizationally
            valuable. Empty tuple short-circuits to "accept any".
        require_value_tag: When ``True``, a goal that carries no tags
            at all is rejected. Defaults to ``False`` to keep
            backward-compatible.
    """

    allowed_value_tags: tuple[str, ...] = field(default_factory=tuple)
    require_value_tag: bool = False

    def evaluate(self, goal_value_tags: tuple[str, ...]) -> EnvelopeVerdict:
        if not self.allowed_value_tags:
            return EnvelopeVerdict.ok()
        if not goal_value_tags:
            if self.require_value_tag:
                return EnvelopeVerdict(
                    accepted=False,
                    reason="goal carries no value tags",
                    violated_field="value_tags",
                )
            return EnvelopeVerdict.ok()
        overlap = set(self.allowed_value_tags) & set(goal_value_tags)
        if overlap:
            return EnvelopeVerdict.ok()
        return EnvelopeVerdict(
            accepted=False,
            reason=(
                f"goal value tags {goal_value_tags!r} do not overlap "
                f"with allowed {self.allowed_value_tags!r}"
            ),
            violated_field="value_tags",
        )


__all__ = [
    "ComputationalMotivationMetrics",
    "CreativityEnvelope",
    "EnvelopeVerdict",
    "GoalRelevanceFilter",
    "MotivationEvent",
    "MotivationType",
    "evaluate_envelope",
]
