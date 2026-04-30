"""Cognitive blackboard DTOs.

Typed keys and snapshot model for the inter-phase cognitive blackboard.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BlackboardKey(str, Enum):
    """Typed keys for the cognitive blackboard.

    - STATES: current world state (from PERCEIVE)
    - GOALS: active goals (from INTEND)
    - PLANS: current plans (from PLAN)
    - ACTIONS: committed actions (from ACT)
    - DISCREPANCY: detected discrepancies (from INTERPRET / EVAL)
    - META_MONITOR: meta-loop monitoring data
    - META_ASSESS: meta-loop assessment results
    - META_CONTROL: meta-loop control actions
    - CUSTOM: extension point for ad-hoc data
    """

    STATES = "states"
    GOALS = "goals"
    PLANS = "plans"
    ACTIONS = "actions"
    DISCREPANCY = "discrepancy"
    META_MONITOR = "meta_monitor"
    META_ASSESS = "meta_assess"
    META_CONTROL = "meta_control"
    CUSTOM = "custom"


class BlackboardSnapshot(BaseModel):
    """Immutable snapshot of blackboard state at a point in time.

    Created at cycle finalize to record the full inter-phase state
    alongside a `CycleTrace`.
    """

    data: dict[str, Any] = Field(default_factory=dict)
    cycle_id: str = ""


__all__ = ["BlackboardKey", "BlackboardSnapshot"]
