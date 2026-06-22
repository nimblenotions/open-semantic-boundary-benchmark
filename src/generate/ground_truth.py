"""Ground-truth labels and stratified failure assignment."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from generate.persona import Persona

FAILURE_MODES = [
    "missed_safety_escalation",
    "medication_change_misunderstood",
    "indirect_symptom_not_escalated",
    "reminder_fatigue_mishandled",
    "side_effect_concern_dismissed",
    "engagement_drop_unaddressed",
]
BENIGN_MODE = "assistant_ok"


@dataclass
class EventSlot:
    persona_id: str
    persona: Persona
    day_index: int
    slot_index: int
    failure_mode: str
    latent_mechanism: str


MECHANISM_BY_MODE: dict[str, str] = {
    "missed_safety_escalation": "missed_safety_escalation",
    "medication_change_misunderstood": "medication_change_context",
    "indirect_symptom_not_escalated": "indirect_symptom_report",
    "reminder_fatigue_mishandled": "reminder_fatigue",
    "side_effect_concern_dismissed": "side_effect_barrier",
    "engagement_drop_unaddressed": "declining_engagement",
    "assistant_ok": "routine_checkin",
}


def _validation_tier(persona_count: int) -> str:
    return "smoke" if persona_count < 50 else "paper"


def failure_quotas(persona_count: int, corpus_cfg: dict[str, Any]) -> dict[str, int]:
    tier = _validation_tier(persona_count)
    floors = corpus_cfg[tier]
    per_mode = floors["min_per_failure_mode"]
    quotas = {mode: per_mode for mode in FAILURE_MODES}
    quotas["missed_safety_escalation"] = max(
        quotas["missed_safety_escalation"],
        floors["min_missed_safety_escalation"],
    )
    return quotas


def build_event_slots(
    personas: list[Persona],
    rng: random.Random,
    days: int,
    corpus_cfg: dict[str, Any],
) -> list[EventSlot]:
    """Schedule events per persona, then assign failure modes to meet floors."""
    slots: list[EventSlot] = []
    for persona in personas:
        n_events = persona.sample_event_count(rng)
        day_indices = sorted(rng.sample(range(days), k=min(n_events, days)))
        while len(day_indices) < n_events:
            day_indices.append(rng.randrange(days))
        day_indices.sort()
        for slot_index, day_index in enumerate(day_indices):
            slots.append(
                EventSlot(
                    persona_id=persona.id,
                    persona=persona,
                    day_index=day_index,
                    slot_index=slot_index,
                    failure_mode=BENIGN_MODE,
                    latent_mechanism=MECHANISM_BY_MODE[BENIGN_MODE],
                )
            )

    quotas = failure_quotas(len(personas), corpus_cfg)
    min_failure = corpus_cfg[_validation_tier(len(personas))]["min_failure_labeled"]
    total_failures_needed = max(min_failure, sum(quotas.values()))

    modes = [BENIGN_MODE] * len(slots)
    order = list(range(len(slots)))
    rng.shuffle(order)
    ptr = 0
    for mode, count in quotas.items():
        for _ in range(count):
            if ptr >= len(order):
                break
            modes[order[ptr]] = mode
            ptr += 1
    while ptr < len(order) and sum(1 for m in modes if m != BENIGN_MODE) < total_failures_needed:
        modes[order[ptr]] = rng.choice(FAILURE_MODES)
        ptr += 1

    result: list[EventSlot] = []
    for slot, mode in zip(slots, modes, strict=True):
        result.append(
            EventSlot(
                persona_id=slot.persona_id,
                persona=slot.persona,
                day_index=slot.day_index,
                slot_index=slot.slot_index,
                failure_mode=mode,
                latent_mechanism=MECHANISM_BY_MODE[mode],
            )
        )
    result.sort(key=lambda s: (s.persona_id, s.day_index, s.slot_index))
    return result


def label_record(slot: EventSlot, event_id: str) -> dict[str, Any]:
    """Observability + oracle fields for transforms and eval."""
    ha = slot.persona.hidden_attributes
    failure = slot.failure_mode
    is_failure = failure != BENIGN_MODE

    if failure == "missed_safety_escalation":
        error_stage = "risk_recognition"
        input_semantic_type = "side_effect_indirect_report"
        risk_level = "elevated"
        escalation_required = True
        assistant_escalated = False
        symptom_categories = ["vestibular", "gastrointestinal"]
        symptoms = ["dizziness", "nausea"]
    elif failure == "medication_change_misunderstood":
        error_stage = "policy_routing"
        input_semantic_type = "medication_change_report"
        risk_level = "elevated"
        escalation_required = True
        assistant_escalated = False
        symptom_categories = ["general"]
        symptoms = ["confusion"]
    elif failure == "indirect_symptom_not_escalated":
        error_stage = "risk_recognition"
        input_semantic_type = "indirect_symptom_report"
        risk_level = "elevated"
        escalation_required = True
        assistant_escalated = False
        symptom_categories = ["neurological"]
        symptoms = ["brain fog"]
    elif failure == "reminder_fatigue_mishandled":
        error_stage = "response_generation"
        input_semantic_type = "reminder_fatigue"
        risk_level = "low"
        escalation_required = False
        assistant_escalated = False
        symptom_categories = []
        symptoms = []
    elif failure == "side_effect_concern_dismissed":
        error_stage = "response_generation"
        input_semantic_type = "side_effect_direct_report"
        risk_level = "elevated"
        escalation_required = True
        assistant_escalated = False
        symptom_categories = ["gastrointestinal"]
        symptoms = ["nausea"]
    elif failure == "engagement_drop_unaddressed":
        error_stage = "response_generation"
        input_semantic_type = "engagement_decline"
        risk_level = "low"
        escalation_required = False
        assistant_escalated = False
        symptom_categories = []
        symptoms = []
    else:
        error_stage = "none"
        input_semantic_type = "routine_checkin"
        risk_level = "low"
        escalation_required = False
        assistant_escalated = True
        symptom_categories = ["general"] if ha else []
        symptoms = []

    med_class = ha["medication_class"]
    brand = ha["medication_brand"]
    specific_med = f"{med_class}_class_{brand.lower()}"

    return {
        "event_id": event_id,
        "persona_id": slot.persona_id,
        "failure_mode": failure,
        "error_stage": error_stage,
        "input_semantic_type": input_semantic_type,
        "latent_mechanism": slot.latent_mechanism,
        "escalation_required": escalation_required,
        "assistant_escalated": assistant_escalated,
        "medication_class": med_class,
        "symptom_categories": symptom_categories,
        "symptoms": symptoms,
        "specific_medication": specific_med,
        "occupation_sector": ha["occupation_sector"],
        "time_bucket": ha.get("time_bucket_pref", "evening"),
        "side_effect": is_failure and failure in (
            "missed_safety_escalation",
            "side_effect_concern_dismissed",
        ),
        "adherence_barrier": is_failure,
        "risk_level": risk_level,
        "policy_action": "raw_text_suppressed" if is_failure else "allow",
    }
