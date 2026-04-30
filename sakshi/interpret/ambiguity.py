"""Decision-relevance-free-energy ambiguity detection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AmbiguityReport:
    """Summary of ambiguity in a belief distribution."""

    ambiguity_score: float
    decision_relevant: bool
    blocked_goals: list[str]
    epistemic_action: str
    confidence: float
    hypothesis_count: int


class DRFreeAmbiguityDetector:
    """Detect decision-relevant ambiguity from hypothesis probabilities."""

    AMBIGUITY_THRESHOLD = 0.6
    MIN_HYPOTHESES = 2

    def detect(
        self,
        belief_distribution: dict[str, float],
        active_goals: list[str],
        context: dict[str, Any] | None = None,
    ) -> AmbiguityReport:
        del context
        if not belief_distribution or len(belief_distribution) < self.MIN_HYPOTHESES:
            return AmbiguityReport(
                ambiguity_score=0.0,
                decision_relevant=False,
                blocked_goals=[],
                epistemic_action="proceed_with_confidence",
                confidence=1.0,
                hypothesis_count=len(belief_distribution),
            )

        probabilities = self._normalize_probabilities(belief_distribution)
        ambiguity_score = self._compute_normalized_entropy(probabilities)
        relevant, blocked_goals = self._check_decision_relevance(
            belief_distribution,
            active_goals,
        )
        epistemic_action = self._recommend_epistemic_action(
            ambiguity_score,
            blocked_goals,
        )

        return AmbiguityReport(
            ambiguity_score=round(ambiguity_score, 6),
            decision_relevant=(
                relevant and ambiguity_score >= self.AMBIGUITY_THRESHOLD
            ),
            blocked_goals=blocked_goals,
            epistemic_action=epistemic_action,
            confidence=round(1.0 - ambiguity_score, 6),
            hypothesis_count=len(belief_distribution),
        )

    def _normalize_probabilities(
        self, belief_distribution: dict[str, float]
    ) -> list[float]:
        total = sum(belief_distribution.values())
        if total <= 0:
            return [1.0 / len(belief_distribution)] * len(belief_distribution)
        if abs(total - 1.0) > 0.01:
            return [value / total for value in belief_distribution.values()]
        return list(belief_distribution.values())

    def _compute_normalized_entropy(self, probabilities: list[float]) -> float:
        """Return Shannon entropy normalized to [0, 1]."""
        count = len(probabilities)
        if count < 2:
            return 0.0
        entropy = -sum(
            probability * math.log2(probability)
            for probability in probabilities
            if probability > 0
        )
        maximum = math.log2(count)
        return entropy / maximum if maximum > 0 else 0.0

    def _check_decision_relevance(
        self,
        belief_distribution: dict[str, float],
        active_goals: list[str],
    ) -> tuple[bool, list[str]]:
        if not active_goals:
            return False, []
        keywords = [hypothesis.lower() for hypothesis in belief_distribution]
        blocked = [
            goal
            for goal in active_goals
            if any(
                keyword in goal.lower() or goal.lower() in keyword
                for keyword in keywords
            )
        ]
        return bool(blocked), blocked

    def _recommend_epistemic_action(
        self,
        ambiguity_score: float,
        blocked_goals: list[str],
    ) -> str:
        if ambiguity_score >= self.AMBIGUITY_THRESHOLD:
            return "seek_clarification" if blocked_goals else "background_exploration"
        return "proceed_with_confidence"
