"""Unit tests for batch LLM journal sanitization parsing."""

from __future__ import annotations

import pytest

from transform.llm_sanitize import (
    _parse_journal_array,
    _parse_text_array,
    build_text_export,
    llm_sanitize_batch,
    write_cache,
)


def test_parse_journal_array_plain_list():
    out = _parse_journal_array('["a sanitized", "b sanitized"]', 2)
    assert out == ["a sanitized", "b sanitized"]


def test_parse_journal_array_wrapped_object():
    raw = '{"journal_texts": ["one", "two", "three"]}'
    out = _parse_journal_array(raw, 3)
    assert len(out) == 3


def test_parse_text_array_assistant_wrapped_object():
    raw = '{"assistant_texts": ["one", "two"]}'
    out = _parse_text_array(raw, 2, label="assistant")
    assert out == ["one", "two"]


def test_parse_journal_array_length_mismatch_raises():
    with pytest.raises(ValueError, match="Expected 2"):
        _parse_journal_array('["only one"]', 2)


def test_build_text_export_fills_boilerplate():
    event = {
        "event_id": "evt_000001",
        "persona_id": "persona_001",
        "journal_text": "raw journal",
        "assistant_text": "raw assistant",
    }
    rec = build_text_export(
        event,
        "sanitized journal",
        condition_id="redact_llm_substitute",
        llm_sanitize_mode="substitute",
        model="qwen3:8b",
        prompt_version="batch_v1",
    )
    assert rec["z"]["journal_text"] == "sanitized journal"
    assert rec["z"]["assistant_text"] == "raw assistant"
    assert rec["r"]["llm_sanitize_mode"] == "substitute"
    assert rec["event_id"] == "evt_000001"


def test_assistant_batch_split_fallback_reads_journal_cache(tmp_path, monkeypatch):
    """Split retry must still read journal cache when use_cache=False on sub-batches."""
    root = tmp_path
    cfg = {"transform": {"llm": {"cache_dir": "cache", "model": "test"}}}
    condition_id = "redact_llm_rephrase"
    events = [
        {
            "event_id": "e1",
            "persona_id": "p1",
            "journal_text": "j1",
            "assistant_text": "a1",
        },
        {
            "event_id": "e2",
            "persona_id": "p1",
            "journal_text": "j2",
            "assistant_text": "a2",
        },
    ]
    for event in events:
        write_cache(
            root,
            cfg,
            condition_id=condition_id,
            event_id=event["event_id"],
            model="test",
            z={
                "journal_text": f"sj_{event['event_id']}",
                "assistant_text": event["assistant_text"],
            },
        )

    def fake_batch(texts, mode, cfg, text_field="journal_text"):
        if len(texts) > 1:
            raise ValueError("simulated batch parse failure")
        return [f"sanitized_{texts[0]}"]

    monkeypatch.setattr("transform.llm_sanitize.call_ollama_batch", fake_batch)

    out = llm_sanitize_batch(
        events,
        "rephrase",
        cfg,
        root,
        condition_id=condition_id,
        text_field="assistant_text",
    )
    assert len(out) == 2
    assert out[0]["journal_text"] == "sj_e1"
    assert out[0]["assistant_text"] == "sanitized_a1"
    assert out[1]["journal_text"] == "sj_e2"
    assert out[1]["assistant_text"] == "sanitized_a2"


def test_llm_sanitize_batch_writes_cache_jsonl(tmp_path, monkeypatch):
    root = tmp_path
    cfg = {"transform": {"llm": {"cache_dir": "cache", "model": "test"}}}
    condition_id = "redact_llm_rephrase"
    events = [
        {
            "event_id": "e1",
            "persona_id": "p1",
            "journal_text": "j1",
            "assistant_text": "a1",
        },
    ]

    def fake_batch(texts, mode, cfg, text_field="journal_text"):
        return [f"sanitized_{texts[0]}"]

    monkeypatch.setattr("transform.llm_sanitize.call_ollama_batch", fake_batch)

    llm_sanitize_batch(
        events,
        "rephrase",
        cfg,
        root,
        condition_id=condition_id,
        use_cache=False,
        text_field="journal_text",
    )

    cache_dir = root / "cache" / condition_id
    assert (cache_dir / "cache.jsonl").is_file()
    assert not list(cache_dir.glob("evt_*.json"))
