"""Transform bundle I/O tests."""

from __future__ import annotations

import json

from transform.io import (
    EVENTS_BUNDLE_NAME,
    load_condition_exports,
    write_jsonl_bundle,
)


def test_write_and_load_jsonl_bundle(tmp_path):
    records = [
        {"event_id": "evt_000001", "z": {"a": 1}},
        {"event_id": "evt_000002", "z": {"a": 2}},
    ]
    bundle = tmp_path / EVENTS_BUNDLE_NAME
    write_jsonl_bundle(bundle, records)
    lines = bundle.read_text().strip().splitlines()
    assert len(lines) == 2
    loaded = load_condition_exports(tmp_path)
    assert set(loaded) == {"evt_000001", "evt_000002"}
    assert loaded["evt_000001"]["z"]["a"] == 1


def test_load_prefers_bundle_over_legacy(tmp_path):
    write_jsonl_bundle(
        tmp_path / EVENTS_BUNDLE_NAME,
        [{"event_id": "evt_000001", "source": "bundle"}],
    )
    (tmp_path / "evt_000001.json").write_text(
        json.dumps({"event_id": "evt_000001", "source": "legacy"}),
        encoding="utf-8",
    )
    loaded = load_condition_exports(tmp_path)
    assert loaded["evt_000001"]["source"] == "bundle"
