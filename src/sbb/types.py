"""Shared types for boundary and eval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExportEvent:
    """Governed export crossing the boundary: (z, r, verify_outcome)."""

    z: dict[str, Any]
    r: dict[str, Any]
    verify_outcome: str  # pass | fail
    event_id: str = ""
    condition_id: str = ""


@dataclass
class PurposeRegistration:
    consumer_id: str
    purpose_id: str
    policy_path: str
    schema_id: str


@dataclass
class RawEvent:
    """Canonical synthetic event in zone_in."""

    event_id: str
    persona_id: str
    journal_text: str
    assistant_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ground_truth: dict[str, Any] = field(default_factory=dict)
