"""Anomaly explanation.

Builds a structured causal hypothesis from an anomaly event, optional
anomaly history, optional goal graph history, and optional basin profile
data supplied by a host adapter.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from sakshi.goals.graph import GoalGraph

logger = logging.getLogger(__name__)

RecurrenceCounter = Callable[[str], int | Awaitable[int]]
BasinProfileProvider = Callable[[str], "BasinProfile | Mapping[str, Any] | None"]


class BasinProfile(BaseModel):
    """Host-supplied basin profile summary."""

    stability: float = 0.0
    strength: float = 0.0


class AnomalyExplanation(BaseModel):
    """Structured causal hypothesis for a detected anomaly."""

    anomaly_class: str = Field(description="Most-shifted activation key")
    recurrence_count: int = Field(
        description="Times this anomaly class appeared in supplied history"
    )
    prior_resolution: str | None = Field(
        default=None,
        description=(
            "Prior goal resolution: achieved|abandoned|delegated|active|unresolved"
        ),
    )
    prior_goal_id: str | None = Field(default=None)
    basin_stability: float = 0.0
    basin_strength: float = 0.0
    is_novel: bool = True
    hypothesis: str = ""
    confidence: float = 0.3
    explained_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnomalyExplainer:
    """Produce structured anomaly explanations from package-native inputs.

    Runtime histories and basin profiles enter through constructor args
    or per-call overrides. No event bus, graph database, or basin service
    is imported by this class.
    """

    def __init__(
        self,
        *,
        recurrence_counter: RecurrenceCounter | None = None,
        goal_graph: GoalGraph | None = None,
        basin_profile_provider: BasinProfileProvider | None = None,
        anomaly_history: Iterable[Mapping[str, Any] | object] | None = None,
    ) -> None:
        self._recurrence_counter = recurrence_counter
        self._goal_graph = goal_graph
        self._basin_profile_provider = basin_profile_provider
        self._anomaly_history = list(anomaly_history or [])

    async def explain(
        self,
        anomaly_event: object,
        *,
        anomaly_history: Iterable[Mapping[str, Any] | object] | None = None,
        goal_graph: GoalGraph | None = None,
        basin_profile_provider: BasinProfileProvider | None = None,
    ) -> AnomalyExplanation:
        """Return a best-effort explanation, never blocking goal generation."""
        try:
            current = _as_float_map(
                getattr(anomaly_event, "current_activations", {}) or {}
            )
            baseline = _as_float_map(getattr(anomaly_event, "baseline_mean", {}) or {})
            a_distance = float(getattr(anomaly_event, "a_distance", 0.0))

            anomaly_class = find_most_shifted_key(current, baseline)
            recurrence_count = await self._count_recurrences(
                anomaly_class,
                anomaly_history=anomaly_history,
            )
            prior_resolution, prior_goal_id = self._lookup_prior_resolution(
                anomaly_class,
                goal_graph=goal_graph,
            )
            profile = self._get_basin_profile(
                anomaly_class,
                basin_profile_provider=basin_profile_provider,
            )

            hypothesis = self._build_hypothesis(
                anomaly_class=anomaly_class,
                recurrence_count=recurrence_count,
                prior_resolution=prior_resolution,
                basin_stability=profile.stability,
                a_distance=a_distance,
            )
            confidence = self._compute_confidence(
                recurrence_count=recurrence_count,
                prior_resolution=prior_resolution,
                basin_stability=profile.stability,
            )

            return AnomalyExplanation(
                anomaly_class=anomaly_class,
                recurrence_count=recurrence_count,
                prior_resolution=prior_resolution,
                prior_goal_id=prior_goal_id,
                basin_stability=profile.stability,
                basin_strength=profile.strength,
                is_novel=recurrence_count == 0,
                hypothesis=hypothesis,
                confidence=confidence,
            )
        except Exception as exc:
            logger.warning(
                "AnomalyExplainer.explain failed (%s: %s); returning "
                "degraded explanation marked anomaly_class=unknown",
                type(exc).__name__,
                exc,
            )
            return AnomalyExplanation(
                anomaly_class="unknown",
                recurrence_count=0,
                basin_stability=0.0,
                basin_strength=0.0,
                is_novel=True,
                hypothesis=(
                    f"Anomaly detected; causal explanation unavailable "
                    f"(explainer error: {type(exc).__name__})."
                ),
                confidence=0.3,
            )

    async def explain_distribution(
        self,
        anomaly_event: object,
        *,
        anomaly_history: Iterable[Mapping[str, Any] | object] | None = None,
        goal_graph: GoalGraph | None = None,
        basin_profile_provider: BasinProfileProvider | None = None,
        top_k: int = 3,
    ) -> list[AnomalyExplanation]:
        """Return up to ``top_k`` ranked competing hypotheses.

        Where ``explain`` collapses to the single most-shifted key,
        this method returns several candidate explanations — one per
        meaningfully shifted key, sorted by descending confidence.

        The shape lets a meta-cycle hedge across competing diagnoses:
        a ``SWAP_MODULE`` action on the top-1 hypothesis is sound only
        when its confidence exceeds the runner-up by a comfortable
        margin; otherwise the host should defer or gather more
        evidence.
        """
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        try:
            current = _as_float_map(
                getattr(anomaly_event, "current_activations", {}) or {}
            )
            baseline = _as_float_map(
                getattr(anomaly_event, "baseline_mean", {}) or {}
            )
            a_distance = float(getattr(anomaly_event, "a_distance", 0.0))
        except Exception as exc:
            logger.warning(
                "AnomalyExplainer.explain_distribution failed early "
                "(%s: %s); returning empty distribution",
                type(exc).__name__,
                exc,
            )
            return []

        if not current or not baseline:
            single = await self.explain(
                anomaly_event,
                anomaly_history=anomaly_history,
                goal_graph=goal_graph,
                basin_profile_provider=basin_profile_provider,
            )
            return [single]

        # Rank by absolute activation shift across baseline keys.
        keys = sorted(
            set(current.keys()) | set(baseline.keys()),
            key=lambda k: abs(
                current.get(k, 0.0) - baseline.get(k, 0.0)
            ),
            reverse=True,
        )

        explanations: list[AnomalyExplanation] = []
        for anomaly_class in keys[:top_k]:
            try:
                recurrence_count = await self._count_recurrences(
                    anomaly_class,
                    anomaly_history=anomaly_history,
                )
                prior_resolution, prior_goal_id = self._lookup_prior_resolution(
                    anomaly_class,
                    goal_graph=goal_graph,
                )
                profile = self._get_basin_profile(
                    anomaly_class,
                    basin_profile_provider=basin_profile_provider,
                )
                hypothesis = self._build_hypothesis(
                    anomaly_class=anomaly_class,
                    recurrence_count=recurrence_count,
                    prior_resolution=prior_resolution,
                    basin_stability=profile.stability,
                    a_distance=a_distance,
                )
                confidence = self._compute_confidence(
                    recurrence_count=recurrence_count,
                    prior_resolution=prior_resolution,
                    basin_stability=profile.stability,
                )
                explanations.append(
                    AnomalyExplanation(
                        anomaly_class=anomaly_class,
                        recurrence_count=recurrence_count,
                        prior_resolution=prior_resolution,
                        prior_goal_id=prior_goal_id,
                        basin_stability=profile.stability,
                        basin_strength=profile.strength,
                        is_novel=recurrence_count == 0,
                        hypothesis=hypothesis,
                        confidence=confidence,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "AnomalyExplainer.explain_distribution: skipping "
                    "candidate %r (%s: %s)",
                    anomaly_class,
                    type(exc).__name__,
                    exc,
                )

        explanations.sort(key=lambda e: e.confidence, reverse=True)
        return explanations

    async def _count_recurrences(
        self,
        anomaly_class: str,
        *,
        anomaly_history: Iterable[Mapping[str, Any] | object] | None = None,
    ) -> int:
        if self._recurrence_counter is not None:
            result = self._recurrence_counter(anomaly_class)
            if inspect.isawaitable(result):
                return int(await result)
            return int(result)

        history = (
            list(anomaly_history)
            if anomaly_history is not None
            else self._anomaly_history
        )
        count = 0
        for event in history:
            data = _event_data(event)
            current = _as_float_map(data.get("current_activations", {}))
            baseline = _as_float_map(data.get("baseline_mean", {}))
            if baseline:
                if find_most_shifted_key(current, baseline) == anomaly_class:
                    count += 1
            elif anomaly_class in current:
                count += 1
        return count

    def _lookup_prior_resolution(
        self,
        anomaly_class: str,
        *,
        goal_graph: GoalGraph | None = None,
    ) -> tuple[str | None, str | None]:
        graph = goal_graph or self._goal_graph
        if graph is None:
            return None, None

        status_map = {
            "achieved": "achieved",
            "abandoned": "abandoned",
            "delegated": "delegated",
            "active": "active",
        }
        for node in getattr(graph, "_nodes", {}).values():
            goal = node.goal
            if goal.predicate.name != "INVESTIGATE_ANOMALY":
                continue
            if goal.predicate.args.get("basin") != anomaly_class:
                continue
            return status_map.get(goal.status.value, "unresolved"), goal.id
        return None, None

    def _get_basin_profile(
        self,
        basin_name: str,
        *,
        basin_profile_provider: BasinProfileProvider | None = None,
    ) -> BasinProfile:
        provider = basin_profile_provider or self._basin_profile_provider
        if provider is None:
            return BasinProfile()
        profile = provider(basin_name)
        if profile is None:
            return BasinProfile()
        if isinstance(profile, BasinProfile):
            return profile
        return BasinProfile(
            stability=float(profile.get("stability", 0.0)),
            strength=float(profile.get("strength", 0.0)),
        )

    def _build_hypothesis(
        self,
        *,
        anomaly_class: str,
        recurrence_count: int,
        prior_resolution: str | None,
        basin_stability: float,
        a_distance: float,
    ) -> str:
        parts: list[str] = []
        if recurrence_count == 0:
            parts.append(
                f"Novel anomaly detected in {anomaly_class!r} "
                f"(first occurrence, A-distance={a_distance:.3f})."
            )
        else:
            parts.append(
                f"Recurring anomaly in {anomaly_class!r} "
                f"(seen {recurrence_count} times before, A-distance={a_distance:.3f})."
            )

        if prior_resolution == "achieved":
            parts.append("A prior goal for this anomaly was successfully resolved.")
        elif prior_resolution == "abandoned":
            parts.append("A prior goal for this anomaly was abandoned.")
        elif prior_resolution == "active":
            parts.append("A goal for this anomaly is currently active.")
        elif prior_resolution == "delegated":
            parts.append("A prior goal was delegated externally.")

        if basin_stability < 0.3:
            parts.append(f"Profile {anomaly_class!r} is unstable.")
        elif basin_stability >= 0.7:
            parts.append(f"Profile {anomaly_class!r} is stable.")

        return " ".join(parts)

    def _compute_confidence(
        self,
        *,
        recurrence_count: int,
        prior_resolution: str | None,
        basin_stability: float,
    ) -> float:
        recurrence_bonus = min(0.3, recurrence_count / 10.0 * 0.3)
        resolution_bonus = 0.2 if prior_resolution is not None else 0.0
        stability_bonus = float(basin_stability) * 0.2
        return min(
            1.0,
            max(0.0, 0.3 + recurrence_bonus + resolution_bonus + stability_bonus),
        )


def find_most_shifted_key(
    current: Mapping[str, float],
    baseline: Mapping[str, float],
) -> str:
    """Return the key with the largest activation shift from baseline."""
    if not current or not baseline:
        return "unknown"
    return max(
        current,
        key=lambda key: abs(current.get(key, 0.0) - baseline.get(key, 0.0)),
    )


def _event_data(event: Mapping[str, Any] | object) -> dict[str, Any]:
    if isinstance(event, Mapping):
        return dict(event)
    if hasattr(event, "get_data_dict"):
        data_dict = event.get_data_dict()
        if isinstance(data_dict, Mapping):
            return dict(data_dict)
    if hasattr(event, "model_dump"):
        return event.model_dump()  # type: ignore[no-any-return]
    data = getattr(event, "data", None)
    if isinstance(data, Mapping):
        return dict(data)
    return {
        "current_activations": getattr(event, "current_activations", {}),
        "baseline_mean": getattr(event, "baseline_mean", {}),
    }


def _as_float_map(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): float(raw) for key, raw in value.items()}


__all__ = [
    "AnomalyExplainer",
    "AnomalyExplanation",
    "BasinProfile",
    "BasinProfileProvider",
    "RecurrenceCounter",
    "find_most_shifted_key",
]
