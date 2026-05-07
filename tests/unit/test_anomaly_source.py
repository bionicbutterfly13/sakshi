"""Tests for AnomalySourceType and lane-tagged anomaly DTOs."""

from __future__ import annotations

import pytest

from sakshi.interpret.a_distance import AnomalyEvent
from sakshi.models import AnomalyEscalation, AnomalySourceType


def test_anomaly_source_type_values() -> None:
    assert AnomalySourceType.WORLD == "WORLD"
    assert AnomalySourceType.COGNITIVE == "COGNITIVE"
    assert AnomalySourceType.COMPOUND == "COMPOUND"


def test_anomaly_event_default_source_is_world() -> None:
    event = AnomalyEvent(a_distance=0.7)
    assert event.source == AnomalySourceType.WORLD


def test_anomaly_event_can_be_tagged_cognitive() -> None:
    event = AnomalyEvent(a_distance=0.9, source=AnomalySourceType.COGNITIVE)
    assert event.source == AnomalySourceType.COGNITIVE


def test_anomaly_event_round_trip_preserves_source() -> None:
    original = AnomalyEvent(a_distance=0.5, source=AnomalySourceType.COMPOUND)
    payload = original.model_dump()
    rebuilt = AnomalyEvent.model_validate(payload)
    assert rebuilt.source == AnomalySourceType.COMPOUND


def test_anomaly_escalation_carries_source() -> None:
    esc = AnomalyEscalation.from_count(
        "g-1",
        anomaly_count=3,
        source=AnomalySourceType.COGNITIVE,
    )
    assert esc.source == AnomalySourceType.COGNITIVE
    assert esc.current_level == "WIDEN_PRECISION"


def test_anomaly_escalation_default_source_is_world() -> None:
    esc = AnomalyEscalation.from_count("g-2", anomaly_count=0)
    assert esc.source == AnomalySourceType.WORLD


def test_anomaly_source_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        AnomalySourceType("INTERNAL")
