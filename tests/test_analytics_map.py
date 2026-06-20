"""Analytics oracle map tests."""

from __future__ import annotations

from transform.analytics_map import (
    map_analytics_coarse,
    map_analytics_fine,
    map_analytics_medium,
    schema_id_for,
)

RAW_KEYS = {
    "raw_journal",
    "raw_completion",
    "journal_text",
    "assistant_text",
    "failure_mode",
    "error_stage",
}

LABELS = {
    "side_effect": True,
    "adherence_barrier": False,
    "risk_level": "elevated",
    "medication_class": "SSRI",
    "symptom_categories": ["vestibular"],
    "time_bucket": "evening",
    "specific_medication": "SSRI_class_zoloft",
    "failure_mode": "missed_safety_escalation",
    "error_stage": "risk_recognition",
}

PERSONA = {
    "persona_id": "persona_002",
    "logging_propensity": "high",
    "clinical_engagement": "anxious-hypervigilant",
    "adherence_trajectory": "missed-dose",
}


def test_coarse_excludes_prohibited_fields():
    z = map_analytics_coarse(LABELS)
    assert RAW_KEYS.isdisjoint(z.keys())
    assert z["side_effect_present"] is True
    assert z["adherence_friction_present"] is False
    assert z["risk_band"] == "elevated"


def test_medium_has_ta_fields_no_failure_mode():
    z = map_analytics_medium(LABELS)
    assert "failure_mode" not in z
    assert z["medication_class"] == "SSRI"
    assert z["side_effect_signal"] == "present"
    assert z["adherence_signal"] == "none"
    assert z["time_bucket"] == "evening"


def test_fine_omits_time_bucket_avoids_triple():
    z = map_analytics_fine(LABELS, PERSONA)
    assert "time_bucket" not in z
    assert "cohort_segment" in z
    assert "engagement_trend" in z
    assert z["cohort_segment"] == "high_anxious-hypervigilant"
    assert z["engagement_trend"] == "missed-dose"


def test_schema_ids_are_analytics():
    assert schema_id_for("sem_coarse") == "analytics_schema_coarse"
    assert schema_id_for("sem_medium") == "analytics_schema_medium"
    assert schema_id_for("sem_fine") == "analytics_schema_fine"
