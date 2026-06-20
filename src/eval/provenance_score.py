"""Provenance completeness audit for frozen transform exports."""

from __future__ import annotations

from typing import Any

REQUIRED_R_FIELDS = (
    "policy_id",
    "policy_version",
    "schema_id",
    "transform_id",
    "event_id",
    "verify_outcome",
)


def provenance_complete(export: dict[str, Any]) -> bool:
    r = export.get("r")
    if not isinstance(r, dict):
        return False
    return all(r.get(field) not in (None, "") for field in REQUIRED_R_FIELDS)


def evaluate_provenance(exports: dict[str, dict[str, Any]]) -> dict[str, float]:
    if not exports:
        return {"completeness": 0.0, "n_exports": 0}
    complete = sum(1 for export in exports.values() if provenance_complete(export))
    return {
        "completeness": complete / len(exports),
        "n_exports": len(exports),
    }
