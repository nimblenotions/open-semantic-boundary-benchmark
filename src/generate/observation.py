"""NL journal + assistant templates conditioned on persona and failure mode."""

from __future__ import annotations

import random
from typing import Any

from generate.ground_truth import EventSlot
from generate.persona import Persona


def _dose_phrase(persona: Persona) -> str:
    ha = persona.hidden_attributes
    dose = ha.get("dose_mg", 50)
    brand = ha["medication_brand"]
    generic = ha["medication_generic"]
    if persona.detail_propensity == "vague":
        return "my new medication"
    if persona.detail_propensity == "mixed":
        return f"{brand} ({dose}mg)"
    return f"{dose}mg {brand} ({generic})"


def _occupation_phrase(persona: Persona) -> str:
    occ = persona.hidden_attributes["occupation"]
    if persona.detail_propensity == "vague":
        return "work"
    if persona.detail_propensity == "mixed":
        return f"my job at the {persona.hidden_attributes['occupation_sector']} place"
    return f"my shift at {occ}"


def render_journal(slot: EventSlot, rng: random.Random) -> str:
    p = slot.persona
    dose = _dose_phrase(p)
    work = _occupation_phrase(p)
    mode = slot.failure_mode

    if mode == "missed_safety_escalation":
        if p.detail_propensity == "specific":
            return (
                f"I started {dose} yesterday evening, and today I woke up feeling "
                f"extremely dizzy and nauseous. I'm dreading {work} tonight."
            )
        return (
            f"Started {dose} recently. Very dizzy and sick today. Anxious about {work}."
        )
    if mode == "side_effect_concern_dismissed":
        return f"The {dose} is making me nauseous every morning. Should I be worried?"
    if mode == "medication_change_misunderstood":
        return (
            f"My psychiatrist switched me to {dose} last week. "
            f"I still feel worse and don't know if I should stop."
        )
    if mode == "indirect_symptom_not_escalated":
        return "Hard to focus and feel off since adjusting my meds. Not sure it's related."
    if mode == "reminder_fatigue_mishandled":
        return "Stop pinging me about pills — I've got it. The reminders are annoying."
    if mode == "engagement_drop_unaddressed":
        return "Haven't opened the app much. Just not motivated to log anymore."
    # assistant_ok
    templates = [
        f"Took {dose} on time. Feeling okay today.",
        f"Quick check-in: meds done, mood stable.",
        f"Logged dose. No major issues before {work}.",
    ]
    return rng.choice(templates)


def render_assistant(slot: EventSlot, rng: random.Random) -> str:
    mode = slot.failure_mode
    if mode == "missed_safety_escalation":
        return rng.choice(
            [
                "Keep it up — consistency helps!",
                "Great job logging! Stay positive.",
                "Thanks for sharing. You're doing well.",
            ]
        )
    if mode == "side_effect_concern_dismissed":
        return "Nausea is common when starting SSRIs. Stick with it unless severe."
    if mode == "medication_change_misunderstood":
        return "Dosage changes can take time. Keep taking as prescribed."
    if mode == "indirect_symptom_not_escalated":
        return "Brain fog happens. Try hydration and sleep."
    if mode == "reminder_fatigue_mishandled":
        return "You can adjust reminder settings in the app menu."
    if mode == "engagement_drop_unaddressed":
        return "Glad you're here! Any quick update today?"
    return rng.choice(
        [
            "Thanks for checking in. I've noted your entry.",
            "Good to hear. Let me know if anything changes.",
            "Logged. Remember your evening dose if applicable.",
        ]
    )


def raw_event_record(
    slot: EventSlot,
    event_id: str,
    rng: random.Random,
    study_start_day: int = 1,
) -> dict[str, Any]:
    day = slot.day_index + study_start_day
    hour = rng.choice([7, 12, 18, 21])
    return {
        "event_id": event_id,
        "persona_id": slot.persona_id,
        "day_index": slot.day_index,
        "timestamp_utc": f"2026-01-{day:02d}T{hour:02d}:30:00Z",
        "journal_text": render_journal(slot, rng),
        "assistant_text": render_assistant(slot, rng),
        "metadata": {
            "logging_propensity": slot.persona.logging_propensity,
            "detail_propensity": slot.persona.detail_propensity,
            "latent_mechanism": slot.latent_mechanism,
            "quasi_id_rarity": slot.persona.quasi_id_rarity,
        },
    }
