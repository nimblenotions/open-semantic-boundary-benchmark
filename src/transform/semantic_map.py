"""Oracle semantic projection from generator ground truth."""

from __future__ import annotations

from typing import Any

SCHEMA_BY_CONDITION = {
    "sem_coarse": "obs_schema_coarse",
    "sem_medium": "obs_schema_medium",
    "sem_fine": "obs_schema_fine",
}


def map_sem_coarse(labels: dict[str, Any]) -> dict[str, Any]:
    return {
        "side_effect": bool(labels.get("side_effect")),
        "adherence_barrier": bool(labels.get("adherence_barrier")),
        "risk_level": labels.get("risk_level", "low"),
    }


def map_sem_medium(labels: dict[str, Any]) -> dict[str, Any]:
    return {
        "medication_class": labels["medication_class"],
        "symptom_categories": list(labels.get("symptom_categories", [])),
        "failure_mode": labels["failure_mode"],
        "error_stage": labels["error_stage"],
        "input_semantic_type": labels["input_semantic_type"],
        "policy_action": labels.get("policy_action", "allow"),
    }


def map_sem_fine(labels: dict[str, Any]) -> dict[str, Any]:
    """Fine granularity; omits time_bucket when triple would violate obs_policy_v1."""
    z = {
        "specific_medication": labels["specific_medication"],
        "symptoms": list(labels.get("symptoms", [])),
        "occupation_sector": labels["occupation_sector"],
        "failure_mode": labels["failure_mode"],
    }
    # Policy prohibits specific_medication + occupation_sector + time_bucket together.
    return z


def map_semantic(labels: dict[str, Any], condition_id: str) -> dict[str, Any]:
    if condition_id == "sem_coarse":
        return map_sem_coarse(labels)
    if condition_id == "sem_medium":
        return map_sem_medium(labels)
    if condition_id == "sem_fine":
        return map_sem_fine(labels)
    raise ValueError(f"Not a semantic condition: {condition_id}")


def schema_id_for(condition_id: str) -> str:
    return SCHEMA_BY_CONDITION[condition_id]
