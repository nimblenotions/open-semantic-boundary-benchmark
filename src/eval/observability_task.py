"""Observability consumer inputs: serialize exports for utility assessment."""

from __future__ import annotations

import json
from typing import Any

TEXT_CONDITIONS = frozenset(
    {"raw", "redact_bracket", "redact_tokenize", "redact_surrogate"}
)
# Optional appendix pilots — not in frozen v0.1 lattice; kept for future Tier-0 runs.
LLM_TEXT_CONDITIONS = frozenset(
    {"redact_llm_substitute", "redact_llm_rephrase"}
)
SEMANTIC_CONDITIONS = frozenset({"sem_coarse", "sem_medium", "sem_fine"})


def condition_kind(condition_id: str) -> str:
    if condition_id in TEXT_CONDITIONS or condition_id in LLM_TEXT_CONDITIONS:
        return "text"
    if condition_id in SEMANTIC_CONDITIONS:
        return "semantic"
    raise ValueError(f"Unknown condition_id: {condition_id}")


def serialize_text_export(z: dict[str, Any]) -> str:
    journal = z.get("journal_text", "")
    assistant = z.get("assistant_text", "")
    return f"journal: {journal}\nassistant: {assistant}"


def flatten_semantic_z(z: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in z.items():
        if isinstance(value, list):
            flat[key] = "|".join(str(v) for v in value)
        else:
            flat[key] = value
    return flat


def consumer_input(export: dict[str, Any]) -> str | dict[str, Any]:
    z = export["z"]
    condition_id = export["condition_id"]
    if condition_kind(condition_id) == "text":
        return serialize_text_export(z)
    return flatten_semantic_z(z)


def serialize_for_storage(export: dict[str, Any]) -> str:
    payload = consumer_input(export)
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, sort_keys=True)


def ground_truth_failure_mode(label: dict[str, Any]) -> str:
    return label["failure_mode"]


def ground_truth_error_stage(label: dict[str, Any]) -> str:
    return label["error_stage"]
