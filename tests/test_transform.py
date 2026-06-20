"""Phase 2 transform lattice tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sbb.config import load_config, repo_root
from transform.lattice import run_lattice
from transform.spans import TokenVault, transform_text
from transform.surrogate import SurrogateVault, surrogate_text
from transform.tokenize import tokenize_text
from transform.semantic_map import map_sem_coarse, map_sem_fine, map_sem_medium

ROOT = repo_root()
CFG = load_config()
CONDITIONS = CFG["lattice"]["conditions"]
RAW_KEYS = {"raw_journal", "raw_completion", "journal_text", "assistant_text"}

ANCHOR = (
    "I started 50mg Prozac (fluoxetine) yesterday evening, and today I woke up "
    "feeling extremely dizzy and nauseous. I'm dreading my shift at line cook tonight."
)


@pytest.fixture(scope="module")
def lattice_stats():
    if os.environ.get("TRANSFORM_INTEGRATION") != "1":
        pytest.skip("set TRANSFORM_INTEGRATION=1 for full lattice regen")
    stats = run_lattice(CFG, ROOT)
    return stats


def test_redact_bracket_labeled_placeholders():
    out = transform_text(ANCHOR, "bracket")
    assert "Prozac" not in out
    assert "[MEDICATION]" in out
    assert "[SYMPTOM]" in out


def test_redact_tokenize_stable_per_persona():
    v = TokenVault("persona_a")
    t1 = tokenize_text("I take 50mg Prozac daily.", "persona_a", v)
    t2 = tokenize_text("Prozac makes me nauseous.", "persona_a", v)
    assert "Prozac" not in t1
    assert "Prozac" not in t2
    med_tokens = {part for part in t1.split() if part.startswith("MED_")}
    med_tokens |= {part for part in t2.split() if part.startswith("MED_")}
    assert len(med_tokens) == 1


def test_redact_surrogate_realistic_alternates():
    v = SurrogateVault("persona_sur")
    out = surrogate_text(ANCHOR, "persona_sur", v)
    assert "Prozac" not in out
    assert "fluoxetine" not in out
    assert "[MEDICATION]" not in out
    assert "line cook" not in out
    assert "dizzy" not in out or "lightheaded" in out


def test_redact_surrogate_stable_per_persona():
    v = SurrogateVault("persona_b")
    t1 = surrogate_text("Started 50mg Prozac yesterday.", "persona_b", v)
    t2 = surrogate_text("Prozac again today.", "persona_b", v)
    assert "Prozac" not in t1
    assert "Prozac" not in t2
    # Same persona should map Prozac to the same surrogate brand
    words1 = set(t1.split())
    words2 = set(t2.split())
    assert words1 & words2


def test_sem_maps_exclude_raw_fields():
    labels = {
        "side_effect": True,
        "adherence_barrier": True,
        "risk_level": "elevated",
        "medication_class": "SSRI",
        "symptom_categories": ["vestibular"],
        "failure_mode": "missed_safety_escalation",
        "error_stage": "risk_recognition",
        "input_semantic_type": "side_effect_indirect_report",
        "policy_action": "raw_text_suppressed",
        "specific_medication": "SSRI_class_zoloft",
        "symptoms": ["dizziness"],
        "occupation_sector": "healthcare",
        "time_bucket": "evening",
    }
    for z in (
        map_sem_coarse(labels),
        map_sem_medium(labels),
        map_sem_fine(labels),
    ):
        assert RAW_KEYS.isdisjoint(z.keys())


def test_lattice_config_has_nine_conditions_including_llm():
    assert "redact_surrogate" in CONDITIONS
    assert "redact_llm_substitute" in CONDITIONS
    assert "redact_llm_rephrase" in CONDITIONS
    assert "redact_mask" not in CONDITIONS
    assert len(CONDITIONS) == 9


def test_lattice_writes_all_conditions(lattice_stats):
    assert lattice_stats["event_count"] > 0
    for cond in CONDITIONS:
        assert cond in lattice_stats["conditions"]
        from transform.io import EVENTS_BUNDLE_NAME, load_jsonl

        cond_dir = ROOT / CFG["paths"]["transformed"] / cond
        bundle = cond_dir / EVENTS_BUNDLE_NAME
        assert bundle.is_file(), f"{cond}: missing {EVENTS_BUNDLE_NAME}"
        assert len(load_jsonl(bundle)) == lattice_stats["event_count"]
