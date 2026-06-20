"""Tests for LLM cache JSONL consolidation and materialization."""

from __future__ import annotations

import json

from transform.io import EVENTS_BUNDLE_NAME, load_jsonl
from transform.llm_cache_io import CACHE_BUNDLE_NAME, consolidate_llm_cache, load_llm_cache_entries
from transform.llm_materialize import materialize_llm_condition
from transform.llm_sanitize import write_cache


def _write_evt_cache(condition_dir, event_id: str, z: dict[str, str]) -> None:
    path = condition_dir / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "condition_id": condition_dir.name,
                "event_id": event_id,
                "model": "test",
                "prompt_version": "batch_v1",
                "z": z,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_consolidate_llm_cache_removes_sprawl(tmp_path):
    cond_dir = tmp_path / "redact_llm_substitute"
    _write_evt_cache(
        cond_dir,
        "evt_000001",
        {"journal_text": "j1", "assistant_text": "a1"},
    )
    _write_evt_cache(
        cond_dir,
        "evt_000002",
        {"journal_text": "j2", "assistant_text": "a2"},
    )

    stats = consolidate_llm_cache(cond_dir)
    assert stats["event_count"] == 2
    assert stats["legacy_evt_removed"] == 2
    assert (cond_dir / CACHE_BUNDLE_NAME).is_file()
    assert not list(cond_dir.glob("evt_*.json"))

    entries = load_llm_cache_entries(cond_dir)
    assert len(entries) == 2
    assert entries["evt_000001"]["z"]["journal_text"] == "j1"


def test_materialize_llm_writes_obs_and_analytics(tmp_path):
    root = tmp_path
    cfg = {
        "paths": {
            "raw": "data/raw",
            "transformed": "data/transformed",
            "transformed_analytics": "data/transformed_analytics",
        },
        "transform": {"llm": {"cache_dir": "data/llm_transform_cache"}},
    }
    raw_dir = root / "data/raw"
    raw_dir.mkdir(parents=True)
    events = [
        {
            "event_id": "evt_000001",
            "persona_id": "persona_001",
            "journal_text": "raw j",
            "assistant_text": "raw a",
        },
        {
            "event_id": "evt_000002",
            "persona_id": "persona_001",
            "journal_text": "raw j2",
            "assistant_text": "raw a2",
        },
    ]
    (raw_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )

    cond_dir = root / "data/llm_transform_cache/redact_llm_rephrase"
    for event in events:
        write_cache(
            root,
            cfg,
            condition_id="redact_llm_rephrase",
            event_id=event["event_id"],
            model="test",
            z={
                "journal_text": f"sj_{event['event_id']}",
                "assistant_text": f"sa_{event['event_id']}",
            },
        )

    stats = materialize_llm_condition(
        cfg,
        root,
        "redact_llm_rephrase",
        consolidate_cache=True,
        require_full_corpus=True,
    )
    assert stats["obs_event_count"] == 2
    assert stats["analytics_event_count"] == 2

    obs_bundle = root / "data/transformed/redact_llm_rephrase" / EVENTS_BUNDLE_NAME
    ana_bundle = root / "data/transformed_analytics/redact_llm_rephrase" / EVENTS_BUNDLE_NAME
    assert obs_bundle.is_file()
    assert ana_bundle.is_file()

    obs_rows = load_jsonl(obs_bundle)
    ana_rows = load_jsonl(ana_bundle)
    assert obs_rows[0]["z"]["journal_text"] == "sj_evt_000001"
    assert ana_rows[0]["r"]["purpose_id"] == "analytics"
    assert ana_rows[0]["r"]["consumer_id"] == "analytics_vendor"
    assert (cond_dir / CACHE_BUNDLE_NAME).is_file()
    assert not list(cond_dir.glob("evt_*.json"))
