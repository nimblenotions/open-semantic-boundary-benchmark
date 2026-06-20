"""Phase 0 boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from boundary.cross import cross
from boundary.policy_check import policy_check
from boundary.verify import verify_export
from registry.registry import Registry
from sbb.types import RawEvent

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data/policies/obs_policy_v1.json"


@pytest.fixture
def registry() -> Registry:
    reg = Registry()
    reg.register("obs_consumer", "observability", POLICY_PATH, "obs_schema_medium")
    return reg


@pytest.fixture
def policy() -> dict:
    with POLICY_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def test_policy_check_rejects_prohibited_field(policy: dict) -> None:
    z = {"raw_journal": "secret", "failure_mode": "assistant_ok"}
    ok, violations = policy_check(z, policy, "obs_schema_medium")
    assert not ok
    assert any("raw_journal" in v for v in violations)


def test_verify_fails_on_raw_leak(policy: dict) -> None:
    z = {"failure_mode": "assistant_ok", "note": "patient takes Zoloft daily"}
    r = {"policy_id": "obs_policy_v1", "policy_version": "1.0.0", "schema_id": "obs_schema_medium",
         "transform_id": "sem_medium", "event_id": "e1", "verify_outcome": "pass"}
    outcome, issues = verify_export(
        z, r, policy, raw_substrings=["patient takes Zoloft daily"]
    )
    assert outcome == "fail"
    assert issues


def test_cross_passes_clean_export(registry: Registry) -> None:
    raw = RawEvent(
        event_id="evt_001",
        persona_id="p1",
        journal_text="Feeling tired after starting sertraline.",
        assistant_text="Please contact your clinician if symptoms worsen.",
        ground_truth={"failure_mode": "assistant_ok"},
    )
    z = {
        "medication_class": "SSRI",
        "symptom_categories": ["fatigue"],
        "failure_mode": "assistant_ok",
        "error_stage": "none",
        "input_semantic_type": "journal",
        "policy_action": "allow",
    }
    export = cross(raw, "obs_consumer", registry, z=z, schema_id="obs_schema_medium")
    assert export.verify_outcome == "pass"
    assert "sertraline" not in str(export.z).lower()
    assert "Zoloft" not in str(export.z)


def test_sem_export_has_no_raw_keys(registry: Registry) -> None:
    """sem_* exports must not contain raw field names."""
    raw_keys = {"raw_journal", "raw_completion", "journal_text", "assistant_text"}
    z = {
        "medication_class": "SSRI",
        "symptom_categories": ["fatigue"],
        "failure_mode": "assistant_ok",
        "error_stage": "none",
        "input_semantic_type": "journal",
        "policy_action": "allow",
    }
    raw = RawEvent("e2", "p1", "journal", "assistant")
    export = cross(raw, "obs_consumer", registry, z=z, transform_id="sem_medium")
    assert raw_keys.isdisjoint(set(export.z.keys()))
