"""Verify export z and provenance r."""

from __future__ import annotations

from typing import Any


def _contains_raw_leak(z: dict[str, Any], raw_substrings: list[str]) -> list[str]:
    """Detect verbatim replay of raw journal/assistant in export z (not oracle label overlap)."""
    blob = str(z).lower()
    hits: list[str] = []
    for s in raw_substrings:
        if not s or len(s) < 24:
            continue
        low = s.lower().strip()
        if low in blob:
            hits.append(s[:48])
    return hits


def verify_export(
    z: dict[str, Any],
    r: dict[str, Any],
    policy: dict[str, Any],
    raw_substrings: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Return (verify_outcome, issues)."""
    issues: list[str] = []
    for field in policy.get("required_provenance_fields", []):
        if field not in r:
            issues.append(f"missing_provenance:{field}")

    if raw_substrings:
        leaks = _contains_raw_leak(z, raw_substrings)
        if leaks:
            issues.extend([f"raw_leak:{x[:32]}" for x in leaks[:5]])

    return ("pass" if not issues else "fail"), issues
