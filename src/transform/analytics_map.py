"""Oracle analytics projection from generator ground truth (purpose T_a)."""

from __future__ import annotations

from typing import Any

SCHEMA_BY_CONDITION = {
    "sem_coarse": "analytics_schema_coarse",
    "sem_medium": "analytics_schema_medium",
    "sem_fine": "analytics_schema_fine",
}


def _side_effect_signal(labels: dict[str, Any]) -> str:
    return "present" if labels.get("side_effect") else "absent"


def _adherence_signal(labels: dict[str, Any]) -> str:
    return "barrier" if labels.get("adherence_barrier") else "none"


def cohort_segment(persona_row: dict[str, Any]) -> str:
    """Ta-5: logging propensity × clinical engagement archetype."""
    return (
        f"{persona_row['logging_propensity']}_"
        f"{persona_row['clinical_engagement']}"
    )


def engagement_trend(persona_row: dict[str, Any]) -> str:
    """Ta-5: persona adherence trajectory as engagement trend label."""
    return persona_row["adherence_trajectory"]


def map_analytics_coarse(labels: dict[str, Any]) -> dict[str, Any]:
    return {
        "side_effect_present": bool(labels.get("side_effect")),
        "adherence_friction_present": bool(labels.get("adherence_barrier")),
        "risk_band": labels.get("risk_level", "low"),
    }


def map_analytics_medium(labels: dict[str, Any]) -> dict[str, Any]:
    return {
        "medication_class": labels["medication_class"],
        "symptom_categories": list(labels.get("symptom_categories", [])),
        "side_effect_signal": _side_effect_signal(labels),
        "adherence_signal": _adherence_signal(labels),
        "time_bucket": labels["time_bucket"],
    }


def map_analytics_fine(
    labels: dict[str, Any], persona_row: dict[str, Any]
) -> dict[str, Any]:
    """Fine granularity; omits time_bucket to avoid med_class+cohort_segment+time_bucket triple."""
    return {
        "medication_class": labels["medication_class"],
        "symptom_categories": list(labels.get("symptom_categories", [])),
        "side_effect_signal": _side_effect_signal(labels),
        "adherence_signal": _adherence_signal(labels),
        "cohort_segment": cohort_segment(persona_row),
        "engagement_trend": engagement_trend(persona_row),
    }


def map_analytics(
    labels: dict[str, Any],
    condition_id: str,
    *,
    persona_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if condition_id == "sem_coarse":
        return map_analytics_coarse(labels)
    if condition_id == "sem_medium":
        return map_analytics_medium(labels)
    if condition_id == "sem_fine":
        if persona_row is None:
            raise ValueError("persona_row required for sem_fine analytics map")
        return map_analytics_fine(labels, persona_row)
    raise ValueError(f"Not an analytics semantic condition: {condition_id}")


def schema_id_for(condition_id: str) -> str:
    return SCHEMA_BY_CONDITION[condition_id]
