"""Tests for Tier-1 eval cache JSONL consolidation."""

from __future__ import annotations

import json

from eval.eval_cache_io import (
    PREDICTIONS_BUNDLE_NAME,
    consolidate_eval_cache,
    get_eval_cache_entry,
    load_eval_cache_entries,
    upsert_eval_cache_entries,
)
from eval.tier1_consumer import PROMPT_VERSION, load_cached_prediction, write_eval_cache


def _write_evt_prediction(condition_dir, event_id: str, prediction: dict[str, str]) -> None:
    path = condition_dir / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "event_id": event_id,
                "condition_id": condition_dir.name,
                "model": "qwen3:8b",
                "seed": 42,
                "prompt_version": PROMPT_VERSION,
                "prediction": prediction,
                "raw_completion": "{}",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_consolidate_eval_cache_removes_sprawl(tmp_path):
    cond_dir = tmp_path / "data" / "eval_cache" / "qwen3_8b" / "raw"
    _write_evt_prediction(
        cond_dir,
        "evt_a",
        {"failure_mode": "assistant_ok", "error_stage": "none"},
    )
    _write_evt_prediction(
        cond_dir,
        "evt_b",
        {"failure_mode": "missed_safety_escalation", "error_stage": "risk_recognition"},
    )

    stats = consolidate_eval_cache(cond_dir)
    assert stats["event_count"] == 2
    assert stats["legacy_evt_removed"] == 2
    assert (cond_dir / PREDICTIONS_BUNDLE_NAME).is_file()
    assert not list(cond_dir.glob("evt_*.json"))

    entries = load_eval_cache_entries(cond_dir)
    assert len(entries) == 2
    assert entries["evt_a"]["prediction"]["failure_mode"] == "assistant_ok"


def test_write_eval_cache_uses_jsonl_bundle(tmp_path):
    root = tmp_path
    write_eval_cache(
        root,
        model="qwen3:8b",
        condition_id="raw",
        event_id="evt_a",
        seed=42,
        prediction={"failure_mode": "assistant_ok", "error_stage": "none"},
        raw_completion="{}",
    )

    cond_dir = root / "data" / "eval_cache" / "qwen3_8b" / "raw"
    assert (cond_dir / PREDICTIONS_BUNDLE_NAME).is_file()
    assert not list(cond_dir.glob("evt_*.json"))
    assert get_eval_cache_entry(cond_dir, "evt_a") is not None
    assert load_cached_prediction(root, "qwen3:8b", "raw", "evt_a") == {
        "failure_mode": "assistant_ok",
        "error_stage": "none",
    }


def test_legacy_evt_json_still_readable(tmp_path):
    root = tmp_path
    cond_dir = root / "data" / "eval_cache" / "qwen3_8b" / "raw"
    _write_evt_prediction(
        cond_dir,
        "evt_a",
        {"failure_mode": "assistant_ok", "error_stage": "none"},
    )

    assert load_cached_prediction(root, "qwen3:8b", "raw", "evt_a") == {
        "failure_mode": "assistant_ok",
        "error_stage": "none",
    }

    upsert_eval_cache_entries(
        cond_dir,
        [
            {
                "event_id": "evt_b",
                "condition_id": "raw",
                "model": "qwen3:8b",
                "seed": 42,
                "prompt_version": PROMPT_VERSION,
                "prediction": {
                    "failure_mode": "missed_safety_escalation",
                    "error_stage": "risk_recognition",
                },
                "raw_completion": "{}",
            }
        ],
    )
    entries = load_eval_cache_entries(cond_dir)
    assert len(entries) == 2
