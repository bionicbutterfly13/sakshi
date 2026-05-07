"""Cost-matrix error shaping.

When an anomaly classifier returns a probability vector across
classes, naive arg-max picks the most likely class. That is the right
choice only when every misclassification is equally costly. Real
hosts have asymmetric costs — a missed critical-class anomaly costs
more than a false alarm; a missed safety-critical fault costs more
than a missed cosmetic one.

``ConfusionWeighter`` reweights an arg-max-style decision against a
host-supplied cost matrix and returns both the chosen class label
and a typed ``ConfusionDecision`` record describing the reweighting
that produced it. Pure function over numbers; no external deps.

This is decision-only support; the actual classifier model lives in
the host.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ConfusionDecision(Generic[T]):
    """Result of one cost-weighted classification call."""

    chosen_class: T
    expected_cost: float
    naive_argmax: T
    naive_max_probability: float
    cost_matrix_label: str = ""


def expected_cost(
    probabilities: Mapping[T, float],
    cost_row: Mapping[T, float],
) -> float:
    """Sum of `prob[j] * cost[j]` over the class space."""
    total = 0.0
    for cls, prob in probabilities.items():
        total += prob * cost_row.get(cls, 0.0)
    return total


def cost_weighted_argmin(
    probabilities: Mapping[T, float],
    cost_matrix: Mapping[T, Mapping[T, float]],
) -> tuple[T, float]:
    """Pick the predicted class minimizing expected cost.

    ``cost_matrix[i][j]`` reads "cost incurred if we predict ``i``
    when truth is ``j``." Implementations may set ``cost_matrix[i][i]``
    to zero (or to a small negative value to encode a *benefit* for
    correct classification).
    """
    if not probabilities:
        raise ValueError("probabilities must be non-empty")
    best_class: T | None = None
    best_cost = float("inf")
    for predicted in cost_matrix.keys():
        row = cost_matrix[predicted]
        cost = expected_cost(probabilities, row)
        if cost < best_cost:
            best_cost = cost
            best_class = predicted
    if best_class is None:
        raise ValueError("cost_matrix must be non-empty")
    return best_class, best_cost


class ConfusionWeighter(Generic[T]):
    """Apply a cost matrix to a probability vector.

    Args:
        cost_matrix: ``{predicted_class: {true_class: cost}}``.
        label: Optional human-readable label for the matrix; carried
            into emitted records for audit clarity.
    """

    def __init__(
        self,
        cost_matrix: Mapping[T, Mapping[T, float]],
        *,
        label: str = "",
    ) -> None:
        if not cost_matrix:
            raise ValueError("cost_matrix must be non-empty")
        self._cost_matrix = {k: dict(v) for k, v in cost_matrix.items()}
        self._label = label

    @property
    def label(self) -> str:
        return self._label

    def decide(
        self,
        probabilities: Mapping[T, float],
    ) -> ConfusionDecision[T]:
        """Return the cost-weighted choice plus the naive baseline."""
        if not probabilities:
            raise ValueError("probabilities must be non-empty")

        chosen, cost = cost_weighted_argmin(probabilities, self._cost_matrix)
        naive_class, naive_prob = max(probabilities.items(), key=lambda kv: kv[1])
        return ConfusionDecision(
            chosen_class=chosen,
            expected_cost=cost,
            naive_argmax=naive_class,
            naive_max_probability=naive_prob,
            cost_matrix_label=self._label,
        )

    @classmethod
    def from_uniform(
        cls,
        classes: Sequence[T],
        *,
        false_positive_cost: float = 1.0,
        false_negative_cost: float = 1.0,
        label: str = "uniform",
    ) -> ConfusionWeighter[T]:
        """Build a uniform off-diagonal cost matrix.

        Diagonal entries are 0; off-diagonal entries split between
        ``false_positive_cost`` (predicted-positive when truth is
        negative — that is, when ``predicted == classes[0]`` and
        ``true != classes[0]``) and ``false_negative_cost`` for the
        complementary case. Useful as a starting point hosts can
        further specialize.
        """
        if not classes:
            raise ValueError("classes must be non-empty")
        matrix: dict[T, dict[T, float]] = {}
        positive = classes[0]
        for predicted in classes:
            row: dict[T, float] = {}
            for actual in classes:
                if predicted == actual:
                    row[actual] = 0.0
                elif predicted == positive:
                    row[actual] = false_positive_cost
                else:
                    row[actual] = false_negative_cost
            matrix[predicted] = row
        return cls(matrix, label=label)


__all__ = [
    "ConfusionDecision",
    "ConfusionWeighter",
    "cost_weighted_argmin",
    "expected_cost",
]
