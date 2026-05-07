"""Tests for CalibrationTracker."""

from __future__ import annotations

import pytest

from sakshi.interpret import CalibrationTracker, CalibrationWarning


def test_empty_tracker_reports_perfect_calibration() -> None:
    tracker = CalibrationTracker()
    report = tracker.report()
    assert report.sample_count == 0
    assert report.self_trust_score == 1.0
    assert report.warnings == ()


def test_well_calibrated_agent_scores_near_one() -> None:
    tracker = CalibrationTracker(deciles=2, miscalibration_threshold=0.1)
    # Well-calibrated: claim 0.9 conf, right ~90% of the time;
    # claim 0.1 conf, right ~10% of the time.
    for i in range(50):
        tracker.record(predicted_confidence=0.9, actually_correct=i < 45)
        tracker.record(predicted_confidence=0.1, actually_correct=i < 5)
    report = tracker.report()
    assert report.self_trust_score > 0.95
    assert report.warnings == ()


def test_overconfident_agent_emits_warning() -> None:
    tracker = CalibrationTracker(deciles=10, miscalibration_threshold=0.05)
    # Claim 0.9 confidence; only 50% actually right.
    for i in range(20):
        tracker.record(predicted_confidence=0.9, actually_correct=i < 10)
    report = tracker.report()
    assert report.sample_count == 20
    assert len(report.warnings) >= 1
    bad = next(w for w in report.warnings if w.decile_low == 0.9)
    assert bad.is_overconfident
    assert bad.predicted_mean > bad.empirical_hit_rate


def test_underconfident_agent_emits_signed_negative_delta() -> None:
    tracker = CalibrationTracker(deciles=10)
    # Claim 0.2 confidence; 90% actually right.
    for i in range(20):
        tracker.record(predicted_confidence=0.2, actually_correct=i < 18)
    report = tracker.report()
    bad = next(w for w in report.warnings if w.decile_low == 0.2)
    assert bad.is_underconfident
    assert bad.delta < 0


def test_warning_is_frozen_dataclass() -> None:
    from dataclasses import FrozenInstanceError

    tracker = CalibrationTracker(deciles=2)
    for _ in range(20):
        tracker.record(predicted_confidence=0.9, actually_correct=False)
    warning = tracker.report().warnings[0]
    assert isinstance(warning, CalibrationWarning)
    with pytest.raises(FrozenInstanceError):
        warning.delta = 0  # type: ignore[misc]


def test_window_bounds_observations() -> None:
    tracker = CalibrationTracker(window_size=5)
    for _ in range(20):
        tracker.record(predicted_confidence=0.5, actually_correct=True)
    assert tracker.sample_count == 5


def test_invalid_construction() -> None:
    with pytest.raises(ValueError):
        CalibrationTracker(window_size=0)
    with pytest.raises(ValueError):
        CalibrationTracker(deciles=1)
    with pytest.raises(ValueError):
        CalibrationTracker(miscalibration_threshold=0.0)


def test_invalid_observation_rejected() -> None:
    tracker = CalibrationTracker()
    with pytest.raises(ValueError):
        tracker.record(predicted_confidence=1.5, actually_correct=True)
