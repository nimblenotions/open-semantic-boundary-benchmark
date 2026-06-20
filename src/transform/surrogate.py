"""i2b2-style surrogate replacement baseline.

Replaces detected PHI spans with realistic, persona-consistent alternates (date-shift
style time phrases, alternate medications, occupations) rather than placeholders or
masks — following the 2014 i2b2/UTHealth de-identification shared task design
(Stubbs and Uzuner, 2015; Stubbs et al., 2015).
"""

from __future__ import annotations

import hashlib
import random
import re

from generate.persona import MEDICATIONS, OCCUPATIONS
from transform.spans import RULES

# Alternate medication surface forms (not in generator lexicon by default).
_SURROGATE_MEDICATIONS = [
    {"brand": "Celexa", "generic": "citalopram", "dose": "20mg"},
    {"brand": "Paxil", "generic": "paroxetine", "dose": "10mg"},
    {"brand": "Effexor", "generic": "venlafaxine", "dose": "75mg"},
    {"brand": "Buspar", "generic": "buspirone", "dose": "15mg"},
    {"brand": "Remeron", "generic": "mirtazapine", "dose": "15mg"},
]

_MED_TOKEN_MAP: dict[str, str] = {}
for i, med in enumerate(MEDICATIONS):
    alt = _SURROGATE_MEDICATIONS[i % len(_SURROGATE_MEDICATIONS)]
    _MED_TOKEN_MAP[med["brand"].lower()] = alt["brand"]
    _MED_TOKEN_MAP[med["generic"].lower()] = alt["generic"]
    _MED_TOKEN_MAP[med["class"].lower()] = med["class"]  # preserve class label in fluent text
_MED_TOKEN_MAP.update(
    {
        "zoloft": "Celexa",
        "sertraline": "citalopram",
        "ssri": "SNRI",
        "snri": "tricyclic",
        "ndri": "atypical",
        "medication": "prescription",
        "meds": "prescriptions",
        "pill": "tablet",
        "pills": "tablets",
        "dose": "dosage",
    }
)

_TIME_PHRASE_MAP = {
    "yesterday evening": "a few days ago in the late afternoon",
    "yesterday": "recently",
    "this morning": "earlier today",
    "tonight": "later today",
    "evening": "afternoon",
    "morning": "mid-day",
}

_SYMPTOM_PHRASE_MAP = {
    "extremely dizzy and nauseous": "quite lightheaded and queasy",
    "brain fog": "mental fatigue",
    "dizzy": "lightheaded",
    "nauseous": "queasy",
    "nausea": "an upset stomach",
}

_OCCUPATION_PHRASE_MAP = {
    "hospital nurse": "an elementary teacher",
    "hospital": "the clinic",
    "healthcare": "the school district",
    "work": "my workplace",
}


class SurrogateVault:
    """Persona-stable realistic surrogates per (span type, normalized surface)."""

    def __init__(self, persona_id: str, seed: int = 42) -> None:
        self.persona_id = persona_id
        digest = hashlib.sha256(f"{persona_id}:{seed}".encode()).hexdigest()
        self._rng = random.Random(int(digest[:16], 16))
        self._dose_offset = (int(digest[16:20], 16) % 3) * 5 + 5  # 5, 10, or 15 mg shift
        self._surrogates: dict[tuple[str, str], str] = {}
        self._occ_alts = [o["label"] for o in OCCUPATIONS]
        self._rng.shuffle(self._occ_alts)

    def surrogate(self, tag: str, surface: str) -> str:
        norm = surface.lower().strip()
        key = (tag, norm)
        if key in self._surrogates:
            return self._surrogates[key]

        if tag == "MEDICATION":
            if re.fullmatch(r"\d+\s*mg", norm):
                mg = int(re.search(r"\d+", surface).group())  # type: ignore[union-attr]
                alt_mg = max(5, mg - self._dose_offset)
                out = f"{alt_mg}mg"
            elif norm in _MED_TOKEN_MAP:
                out = _MED_TOKEN_MAP[norm]
                if surface[0].isupper() and out.islower():
                    out = out.capitalize()
            else:
                out = self._rng.choice(_SURROGATE_MEDICATIONS)["brand"]
        elif tag == "TIME":
            if re.fullmatch(r"\d{1,2}:\d{2}", norm):
                h, m = surface.split(":")
                out = f"{(int(h) + 2) % 24}:{m}"
            elif norm in _TIME_PHRASE_MAP:
                out = _TIME_PHRASE_MAP[norm]
            else:
                out = "recently"
        elif tag == "OCCUPATION":
            if norm.startswith("shift at "):
                alt = self._occ_alts[0]
                out = f"shift at {alt}"
            elif norm.startswith("my job at the ") and norm.endswith(" place"):
                sector = surface.split()[-2]
                out = f"my job at the {sector} office"
            elif norm in _OCCUPATION_PHRASE_MAP:
                out = _OCCUPATION_PHRASE_MAP[norm]
            else:
                out = self._occ_alts[1]
        elif tag == "SYMPTOM":
            out = _SYMPTOM_PHRASE_MAP.get(norm, "unwell")
        else:
            out = surface

        self._surrogates[key] = out
        return out


def _apply_token_surrogates(
    text: str, tokens: list[str], tag: str, vault: SurrogateVault
) -> str:
    out = text
    for token in tokens:
        pattern = rf"\b{re.escape(token)}\b"

        def _sub(m: re.Match[str], t: str = tag, v: vault = vault) -> str:
            return v.surrogate(t, m.group(0))

        out = re.sub(pattern, _sub, out, flags=re.I)
    return out


def _apply_pattern_surrogates(
    text: str, patterns: list[re.Pattern[str]], tag: str, vault: SurrogateVault
) -> str:
    out = text
    for pat in patterns:

        def _sub(m: re.Match[str], t: str = tag, v: vault = vault) -> str:
            return v.surrogate(t, m.group(0))

        out = pat.sub(_sub, out)
    return out


def surrogate_text(
    text: str,
    persona_id: str,
    vault: SurrogateVault | None = None,
) -> str:
    v = vault or SurrogateVault(persona_id)
    out = text
    for name, rules, tag in RULES:
        if name == "medication":
            out = _apply_token_surrogates(out, rules, tag, v)  # type: ignore[arg-type]
        else:
            out = _apply_pattern_surrogates(out, rules, tag, v)  # type: ignore[arg-type]
    return out


def surrogate_event(
    journal_text: str,
    assistant_text: str,
    persona_id: str,
    vault: SurrogateVault | None = None,
) -> dict[str, str]:
    v = vault or SurrogateVault(persona_id)
    return {
        "journal_text": surrogate_text(journal_text, persona_id, v),
        "assistant_text": surrogate_text(assistant_text, persona_id, v),
    }
