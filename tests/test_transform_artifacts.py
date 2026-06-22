"""Smoke tests for committed transform artifacts (no Ollama required)."""

from __future__ import annotations


import pytest

from sbb.config import load_config, repo_root
from transform.io import EVENTS_BUNDLE_NAME, load_condition_exports, load_jsonl

ROOT = repo_root()
CFG = load_config()
CONDITIONS = CFG["lattice"]["conditions"]
TRANSFORMED = ROOT / CFG["paths"]["transformed"]


def _event_count() -> int:
    raw_dir = TRANSFORMED / "raw"
    if not raw_dir.is_dir():
        return 0
    bundle = raw_dir / EVENTS_BUNDLE_NAME
    if bundle.is_file():
        return len(load_jsonl(bundle))
    return len(list(raw_dir.glob("evt_*.json")))


@pytest.fixture(scope="module")
def expected_events() -> int:
    n = _event_count()
    if n == 0:
        pytest.skip("no transformed artifacts; run make transform")
    return n


def test_all_lattice_artifacts_complete(expected_events: int):
    for cond in CONDITIONS:
        cond_dir = TRANSFORMED / cond
        assert cond_dir.is_dir(), f"missing {cond_dir}"
        bundle = cond_dir / EVENTS_BUNDLE_NAME
        assert bundle.is_file(), f"{cond}: missing {EVENTS_BUNDLE_NAME}"
        exports = load_condition_exports(cond_dir)
        assert len(exports) == expected_events, f"{cond}: {len(exports)} != {expected_events}"


def test_obsolete_conditions_removed():
    for obsolete in (
        "redact_mask",
        "redact_remove",
        "redact_type",
    ):
        assert not (TRANSFORMED / obsolete).exists(), f"obsolete dir still present: {obsolete}"


def test_llm_conditions_materialized(expected_events: int):
    for cond in ("redact_llm_substitute", "redact_llm_rephrase"):
        cond_dir = TRANSFORMED / cond
        assert cond_dir.is_dir(), f"missing LLM condition {cond_dir}"
        exports = load_condition_exports(cond_dir)
        assert len(exports) == expected_events


def test_tokenize_export_has_pseudonyms(expected_events: int):
    cond_dir = TRANSFORMED / "redact_tokenize"
    exports = load_condition_exports(cond_dir)
    sample = exports.get("evt_000060")
    if sample is None:
        pytest.skip("redact_tokenize evt_000060 missing")
    journal = sample["z"]["journal_text"]
    assert "MED_" in journal or "TIME_" in journal or "OCC_" in journal or "SYM_" in journal


def test_surrogate_export_readable(expected_events: int):
    cond_dir = TRANSFORMED / "redact_surrogate"
    exports = load_condition_exports(cond_dir)
    rec = exports.get("evt_000001")
    if rec is None:
        pytest.skip("redact_surrogate evt_000001 missing")
    assert rec["condition_id"] == "redact_surrogate"
    assert rec["r"].get("redact_operator") == "i2b2_surrogate"
    journal = rec["z"]["journal_text"]
    assert "[" not in journal or "[MEDICATION]" not in journal
    assert "Prozac" not in journal
