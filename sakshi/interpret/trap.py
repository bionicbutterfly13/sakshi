"""Failure-axis classification.

When a module declares an admissible failure mode through its
``ExpectationProfile``, the classification along the four-axis
TRAP taxonomy (Transparency, Reasoning, Adaptation, Perception)
makes routing easier: a Reasoning failure suggests a module swap; a
Perception failure suggests strengthening the perception pipeline; a
Transparency failure suggests asking the host for more visibility
before acting.

This module supplies:

* ``TRAPDimension`` — the four-axis enum.
* ``classify_failure_mode`` — a small helper that classifies a
  ``FailureMode`` against the axes using deterministic keyword
  matching plus an explicit override field. No NLP, no host calls,
  no heuristic guesswork beyond what the host can audit.
* ``TRAPRouter`` — maps the classified axis to a recommended
  ``ControlActionType`` so the meta-cycle has a typed default
  intervention per failure class.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from sakshi.models import ControlActionType, FailureMode


class TRAPDimension(StrEnum):
    """Four-axis failure taxonomy."""

    TRANSPARENCY = "transparency"
    REASONING = "reasoning"
    ADAPTATION = "adaptation"
    PERCEPTION = "perception"
    UNCLASSIFIED = "unclassified"


_KEYWORD_MAP: Mapping[TRAPDimension, tuple[str, ...]] = {
    TRAPDimension.TRANSPARENCY: (
        "opaque",
        "unexplain",
        "untraceable",
        "blackbox",
        "black-box",
        "audit",
    ),
    TRAPDimension.REASONING: (
        "impasse",
        "no_plan",
        "empty_plan",
        "infeasible",
        "contradiction",
        "logic",
        "inference",
    ),
    TRAPDimension.ADAPTATION: (
        "drift",
        "stale",
        "outdated",
        "novelty",
        "regression",
        "miscalibration",
    ),
    TRAPDimension.PERCEPTION: (
        "sensor",
        "observation",
        "perceive",
        "noisy_input",
        "missed",
        "missing_data",
    ),
}


def classify_failure_mode(
    failure_mode: FailureMode,
    *,
    override: TRAPDimension | None = None,
) -> TRAPDimension:
    """Classify a ``FailureMode`` along the four axes.

    Resolution order:

    1. ``override`` argument, if supplied.
    2. The substring ``"trap:<axis>"`` inside ``failure_mode.description``
       (case-insensitive). This is the primary host-supplied signal.
    3. Keyword match against ``failure_mode.name`` then
       ``failure_mode.description``.
    4. ``UNCLASSIFIED``.

    The function is deterministic and dependency-free.
    """
    if override is not None:
        return override

    description_lower = (failure_mode.description or "").lower()
    name_lower = failure_mode.name.lower()

    # Step 2: explicit "trap:<axis>" tag in description.
    for axis in TRAPDimension:
        marker = f"trap:{axis.value}"
        if marker in description_lower:
            return axis

    # Step 3: keyword fallback.
    haystack = f"{name_lower} {description_lower}"
    for axis, keywords in _KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in haystack:
                return axis

    return TRAPDimension.UNCLASSIFIED


_DEFAULT_ROUTING: Mapping[TRAPDimension, ControlActionType] = {
    TRAPDimension.TRANSPARENCY: ControlActionType.SUPPRESS_MODULE,
    TRAPDimension.REASONING: ControlActionType.SWAP_MODULE,
    TRAPDimension.ADAPTATION: ControlActionType.ADJUST_PRECISION,
    TRAPDimension.PERCEPTION: ControlActionType.STRENGTHEN_MODULE,
}


class TRAPRouter:
    """Map a classified ``TRAPDimension`` to a recommended control action.

    The default routing is opinionated; hosts that disagree pass a
    custom ``routing`` mapping at construction.
    """

    def __init__(
        self,
        routing: Mapping[TRAPDimension, ControlActionType] | None = None,
    ) -> None:
        self._routing: dict[TRAPDimension, ControlActionType] = dict(_DEFAULT_ROUTING)
        if routing is not None:
            self._routing.update(routing)

    def recommend(self, dimension: TRAPDimension) -> ControlActionType | None:
        """Return the recommended action, or ``None`` if unclassified."""
        return self._routing.get(dimension)


__all__ = [
    "TRAPDimension",
    "TRAPRouter",
    "classify_failure_mode",
]
