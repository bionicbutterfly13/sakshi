"""Interpretation and anomaly-detection runtime classes."""

from __future__ import annotations

from sakshi.interpret.a_distance import (
    ADistanceDetector,
    AnomalyEvent,
    PredicateStream,
    compute_a_distance,
)
from sakshi.interpret.ambiguity import AmbiguityReport, DRFreeAmbiguityDetector
from sakshi.interpret.anomaly_persistence import AnomalyPersistenceTracker
from sakshi.interpret.calibration import (
    DEFAULT_DECILES,
    DEFAULT_MISCALIBRATION_THRESHOLD,
    DEFAULT_WINDOW_SIZE,
    CalibrationReport,
    CalibrationTracker,
    CalibrationWarning,
    ConfidenceObservation,
)
from sakshi.interpret.expectations import ExpectationEvaluator
from sakshi.interpret.explanation import ExplanationEngine, ExplanationHypothesis
from sakshi.interpret.lineage import (
    DEFAULT_DEPTH_DRIFT_THRESHOLD,
    DEFAULT_DEPTH_WARN_THRESHOLD,
    GoalLineageAuditor,
    LineageReport,
    LineageVerdict,
)

__all__ = [
    "ADistanceDetector",
    "AmbiguityReport",
    "AnomalyEvent",
    "AnomalyPersistenceTracker",
    "CalibrationReport",
    "CalibrationTracker",
    "CalibrationWarning",
    "ConfidenceObservation",
    "DEFAULT_DECILES",
    "DEFAULT_DEPTH_DRIFT_THRESHOLD",
    "DEFAULT_DEPTH_WARN_THRESHOLD",
    "DEFAULT_MISCALIBRATION_THRESHOLD",
    "DEFAULT_WINDOW_SIZE",
    "DRFreeAmbiguityDetector",
    "ExpectationEvaluator",
    "ExplanationEngine",
    "ExplanationHypothesis",
    "GoalLineageAuditor",
    "LineageReport",
    "LineageVerdict",
    "PredicateStream",
    "compute_a_distance",
]
