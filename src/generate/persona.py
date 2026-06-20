"""Synthetic persona cohort for SBB-Obs."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Literal

LoggingPropensity = Literal["low", "medium", "high"]
DetailPropensity = Literal["vague", "mixed", "specific"]
QuasiRarity = Literal["common", "rare"]
ClinicalEngagement = Literal["avoidant", "moderate", "anxious-hypervigilant"]

MEDICATIONS = [
    {"brand": "Zoloft", "generic": "sertraline", "class": "SSRI"},
    {"brand": "Lexapro", "generic": "escitalopram", "class": "SSRI"},
    {"brand": "Prozac", "generic": "fluoxetine", "class": "SSRI"},
    {"brand": "Wellbutrin", "generic": "bupropion", "class": "NDRI"},
    {"brand": "Cymbalta", "generic": "duloxetine", "class": "SNRI"},
]

OCCUPATIONS = [
    {"label": "hospital nurse", "sector": "healthcare"},
    {"label": "elementary teacher", "sector": "education"},
    {"label": "retail associate", "sector": "retail"},
    {"label": "software engineer", "sector": "technology"},
    {"label": "home health aide", "sector": "healthcare"},
    {"label": "line cook", "sector": "hospitality"},
]


@dataclass
class Persona:
    id: str
    logging_propensity: LoggingPropensity
    detail_propensity: DetailPropensity
    quasi_id_rarity: QuasiRarity
    clinical_engagement: ClinicalEngagement
    adherence_trajectory: Literal["stable", "side-effect-barrier", "missed-dose"]
    hidden_attributes: dict[str, Any] = field(default_factory=dict)

    def event_count_range(self) -> tuple[int, int]:
        if self.logging_propensity == "low":
            return 10, 15
        if self.logging_propensity == "medium":
            return 25, 40
        return 60, 100

    def sample_event_count(self, rng: random.Random) -> int:
        lo, hi = self.event_count_range()
        return rng.randint(lo, hi)


def _pick_medication(rng: random.Random, rare: bool) -> dict[str, str]:
    if rare:
        return rng.choice([m for m in MEDICATIONS if m["class"] in ("SNRI", "NDRI")])
    return rng.choice(MEDICATIONS)


def _pick_occupation(rng: random.Random, rare: bool) -> dict[str, str]:
    if rare:
        return rng.choice([o for o in OCCUPATIONS if o["sector"] == "healthcare"])
    return rng.choice(OCCUPATIONS)


def generate_personas(count: int, rng: random.Random, rare_fraction: float = 0.12) -> list[Persona]:
    """Build a fixed-seed cohort with heterogeneous propensities."""
    logging_opts: list[LoggingPropensity] = ["low", "medium", "high"]
    detail_opts: list[DetailPropensity] = ["vague", "mixed", "specific"]
    clinical_opts: list[ClinicalEngagement] = ["avoidant", "moderate", "anxious-hypervigilant"]
    trajectory_opts = ["stable", "side-effect-barrier", "missed-dose"]

    rare_count = int(round(count * rare_fraction))
    if count >= 5:
        rare_count = max(2, rare_count)
    elif count >= 2:
        rare_count = max(1, rare_count)
    else:
        rare_count = 0
    rare_count = min(rare_count, count)
    rare_indices = set(rng.sample(range(count), rare_count)) if rare_count else set()

    personas: list[Persona] = []
    for i in range(count):
        rare = i in rare_indices
        med = _pick_medication(rng, rare)
        occ = _pick_occupation(rng, rare)
        personas.append(
            Persona(
                id=f"persona_{i + 1:03d}",
                logging_propensity=rng.choice(logging_opts),
                detail_propensity=rng.choice(detail_opts),
                quasi_id_rarity="rare" if rare else "common",
                clinical_engagement=rng.choice(clinical_opts),
                adherence_trajectory=rng.choice(trajectory_opts),
                hidden_attributes={
                    "medication_brand": med["brand"],
                    "medication_generic": med["generic"],
                    "medication_class": med["class"],
                    "occupation": occ["label"],
                    "occupation_sector": occ["sector"],
                    "dose_mg": rng.choice([25, 50, 75, 100]),
                    "time_bucket_pref": rng.choice(["morning", "afternoon", "evening"]),
                    "condition_focus": rng.choice(
                        ["generalized_anxiety", "depression", "mixed_anxiety_depression"]
                    ),
                },
            )
        )
    return personas


def personas_to_records(personas: list[Persona]) -> list[dict[str, Any]]:
    return [
        {
            "persona_id": p.id,
            "logging_propensity": p.logging_propensity,
            "detail_propensity": p.detail_propensity,
            "quasi_id_rarity": p.quasi_id_rarity,
            "clinical_engagement": p.clinical_engagement,
            "adherence_trajectory": p.adherence_trajectory,
            "hidden_attributes": p.hidden_attributes,
        }
        for p in personas
    ]
