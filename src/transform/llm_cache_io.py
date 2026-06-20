"""JSONL cache I/O for LLM transform arms."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from transform.io import load_jsonl, write_jsonl_bundle

CACHE_BUNDLE_NAME = "cache.jsonl"

# In-memory index per condition cache dir (survives for process lifetime).
_store: dict[str, dict[str, dict[str, Any]]] = {}


def llm_cache_root(root: Path, cfg: dict[str, Any]) -> Path:
    tcfg = cfg.get("transform", {}).get("llm", {})
    return root / tcfg.get("cache_dir", "data/llm_transform_cache")


def llm_condition_cache_dir(root: Path, cfg: dict[str, Any], condition_id: str) -> Path:
    return llm_cache_root(root, cfg) / condition_id


def cache_bundle_path(root: Path, cfg: dict[str, Any], condition_id: str) -> Path:
    return llm_condition_cache_dir(root, cfg, condition_id) / CACHE_BUNDLE_NAME


def _store_key(condition_dir: Path) -> str:
    return str(condition_dir.resolve())


def invalidate_llm_cache_store(condition_dir: Path) -> None:
    _store.pop(_store_key(condition_dir), None)


def load_llm_cache_entries(condition_dir: Path) -> dict[str, dict[str, Any]]:
    """Load cache records indexed by event_id from cache.jsonl and legacy evt_*.json."""
    entries: dict[str, dict[str, Any]] = {}
    bundle = condition_dir / CACHE_BUNDLE_NAME
    if bundle.is_file():
        for row in load_jsonl(bundle):
            if row.get("event_id"):
                entries[row["event_id"]] = row

    for path in sorted(condition_dir.glob("evt_*.json"), key=lambda p: p.name):
        data = json.loads(path.read_text(encoding="utf-8"))
        event_id = data.get("event_id", path.stem)
        entries.setdefault(event_id, data)
    return entries


def _get_store(condition_dir: Path) -> dict[str, dict[str, Any]]:
    key = _store_key(condition_dir)
    if key not in _store:
        _store[key] = load_llm_cache_entries(condition_dir)
    return _store[key]


def flush_llm_cache(condition_dir: Path, *, remove_legacy: bool = True) -> None:
    """Write in-memory store to cache.jsonl."""
    store = _get_store(condition_dir)
    condition_dir.mkdir(parents=True, exist_ok=True)
    if store:
        records = [store[eid] for eid in sorted(store)]
        write_jsonl_bundle(condition_dir / CACHE_BUNDLE_NAME, records)
    if remove_legacy:
        for path in condition_dir.glob("evt_*.json"):
            path.unlink()


def upsert_llm_cache_entry(
    condition_dir: Path,
    record: dict[str, Any],
    *,
    flush: bool = True,
    remove_legacy: bool = True,
) -> None:
    event_id = record["event_id"]
    _get_store(condition_dir)[event_id] = record
    if flush:
        flush_llm_cache(condition_dir, remove_legacy=remove_legacy)


def upsert_llm_cache_entries(
    condition_dir: Path,
    records: list[dict[str, Any]],
    *,
    flush: bool = True,
    remove_legacy: bool = True,
) -> None:
    if not records:
        return
    store = _get_store(condition_dir)
    for record in records:
        store[record["event_id"]] = record
    if flush:
        flush_llm_cache(condition_dir, remove_legacy=remove_legacy)


def get_llm_cache_z(condition_dir: Path, event_id: str) -> dict[str, str] | None:
    entry = _get_store(condition_dir).get(event_id)
    if entry is None:
        return None
    return cache_entry_z(entry)


def has_llm_cache_entry(condition_dir: Path, event_id: str) -> bool:
    return event_id in _get_store(condition_dir)


def consolidate_llm_cache(
    condition_dir: Path,
    *,
    remove_per_event: bool = True,
    remove_batches: bool = True,
) -> dict[str, Any]:
    """Merge evt_*.json sprawl into cache.jsonl (no-op if already jsonl-only)."""
    legacy = sorted(condition_dir.glob("evt_*.json"), key=lambda p: p.name)
    invalidate_llm_cache_store(condition_dir)
    store = _get_store(condition_dir)

    if legacy:
        for path in legacy:
            data = json.loads(path.read_text(encoding="utf-8"))
            event_id = data.get("event_id", path.stem)
            store.setdefault(event_id, data)

    if not store:
        return {
            "condition_id": condition_dir.name,
            "format": CACHE_BUNDLE_NAME,
            "event_count": 0,
            "legacy_evt_removed": 0,
            "skipped": True,
        }

    flush_llm_cache(condition_dir, remove_legacy=remove_per_event)
    removed = len(legacy) if remove_per_event else 0

    if remove_batches:
        batches_dir = condition_dir / "batches"
        if batches_dir.is_dir():
            shutil.rmtree(batches_dir)

    return {
        "condition_id": condition_dir.name,
        "format": CACHE_BUNDLE_NAME,
        "event_count": len(store),
        "legacy_evt_removed": removed,
    }


def cache_entry_z(entry: dict[str, Any]) -> dict[str, str] | None:
    z = entry.get("z")
    if isinstance(z, dict) and "journal_text" in z and "assistant_text" in z:
        return {"journal_text": z["journal_text"], "assistant_text": z["assistant_text"]}
    return None
