"""Forward world-state simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sakshi.models.cycle import CycleTrace


@dataclass(frozen=True)
class SimulationResult:
    """Result of forward-model prediction."""

    predicted_state: dict[str, Any]
    action_applied: str
    confidence: float = 0.5
    discrepancy: dict[str, Any] | None = None


class WorldSimulator:
    """Simple forward model for predicting action outcomes."""

    async def simulate(
        self,
        current_state: dict[str, Any],
        last_action: dict[str, Any] | None = None,
    ) -> SimulationResult:
        """Predict the next state given current state and optional action."""
        if last_action is None:
            return SimulationResult(
                predicted_state=dict(current_state),
                action_applied="none",
                confidence=1.0,
            )

        action_name = last_action.get("tool_name", "unknown")
        expected_outcome = last_action.get("expected_outcome", "")
        predicted = dict(current_state)
        predicted["_last_action"] = action_name
        predicted["_expected_outcome"] = expected_outcome

        outcome_lower = str(expected_outcome).lower()
        if "increase" in outcome_lower:
            self._scale_numeric_values(predicted, 1.1)
        elif "decrease" in outcome_lower:
            self._scale_numeric_values(predicted, 0.9)

        return SimulationResult(
            predicted_state=predicted,
            action_applied=action_name,
            confidence=0.6,
        )

    def detect_discrepancy(
        self,
        predicted: SimulationResult,
        actual_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare predicted state against actual perceived state."""
        discrepancies: dict[str, Any] = {}
        for key, predicted_value in predicted.predicted_state.items():
            if key.startswith("_"):
                continue
            actual_value = actual_state.get(key)
            if actual_value is None:
                continue
            if predicted_value != actual_value:
                discrepancies[key] = {
                    "predicted": predicted_value,
                    "actual": actual_value,
                }
        return discrepancies

    def extract_last_action(
        self,
        cycle_trace: CycleTrace,
    ) -> dict[str, Any] | None:
        """Extract ACT phase output from a completed cycle trace."""
        return cycle_trace.get_phase_output("ACT")

    def _scale_numeric_values(
        self,
        state: dict[str, Any],
        factor: float,
    ) -> None:
        for key, value in list(state.items()):
            if isinstance(value, (int, float)) and not key.startswith("_"):
                state[key] = value * factor
