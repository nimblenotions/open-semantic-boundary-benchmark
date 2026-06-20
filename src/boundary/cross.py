"""cross(observation, consumer, registry) → ExportEvent."""

from __future__ import annotations

from typing import Any

from boundary.policy_check import policy_check
from boundary.verify import verify_export
from registry.registry import Registry
from sbb.types import ExportEvent, RawEvent


def cross(
    observation: RawEvent | dict[str, Any],
    consumer_id: str,
    registry: Registry,
    *,
    z: dict[str, Any],
    schema_id: str = "obs_schema_medium",
    transform_id: str = "sem_medium",
    purpose_id: str = "observability",
) -> ExportEvent:
    """
    Emit governed export (z, r). Caller supplies z (from transform layer).
    Raw text never copied into z by this function.
    """
    if isinstance(observation, RawEvent):
        event_id = observation.event_id
        raw_hints = [observation.journal_text, observation.assistant_text]
    else:
        event_id = observation.get("event_id", "")
        raw_hints = [
            observation.get("journal_text", ""),
            observation.get("assistant_text", ""),
        ]

    policy = registry.load_policy(consumer_id, purpose_id)
    ok, violations = policy_check(z, policy, schema_id)

    r: dict[str, Any] = {
        "policy_id": policy.get("policy_id", "obs_policy_v1"),
        "policy_version": policy.get("policy_version", "1.0.0"),
        "schema_id": schema_id,
        "transform_id": transform_id,
        "event_id": event_id,
        "fields_suppressed": ["raw_journal", "raw_completion"],
        "verify_outcome": "pending",
    }

    verify_outcome, issues = verify_export(z, r, policy, raw_substrings=raw_hints)
    if not ok:
        verify_outcome = "fail"
        r["policy_violations"] = violations
    if issues:
        r["verify_issues"] = issues

    r["verify_outcome"] = verify_outcome
    return ExportEvent(
        z=z,
        r=r,
        verify_outcome=verify_outcome,
        event_id=event_id,
        condition_id=transform_id,
    )
