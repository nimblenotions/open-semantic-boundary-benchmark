"""JSONL I/O for Tier-1 eval prediction caches (obs + analytics)."""

from __future__ import annotations

import contextlib
import fcntl
import json
import re
from pathlib import Path
from typing import Any

from transform.io import load_jsonl, write_jsonl_bundle

PREDICTIONS_BUNDLE_NAME = "predictions.jsonl"
OBS_EVAL_CACHE_DIR = "eval_cache"
ANALYTICS_EVAL_CACHE_DIR = "eval_cache_analytics"

_store: dict[str, dict[str, dict[str, Any]]] = {}


def sanitize_model_dir(model: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", model)


def eval_cache_root(root: Path, *, analytics: bool = False) -> Path:
    name = ANALYTICS_EVAL_CACHE_DIR if analytics else OBS_EVAL_CACHE_DIR
    return root / "data" / name


def eval_condition_cache_dir(
    root: Path,
    model: str,
    condition_id: str,
    *,
    analytics: bool = False,
) -> Path:
    return eval_cache_root(root, analytics=analytics) / sanitize_model_dir(model) / condition_id


def _store_key(condition_dir: Path) -> str:
    return str(condition_dir.resolve())


def invalidate_eval_cache_store(condition_dir: Path) -> None:
    _store.pop(_store_key(condition_dir), None)


def load_eval_cache_entries(condition_dir: Path) -> dict[str, dict[str, Any]]:
    """Load cache records from predictions.jsonl and legacy evt_*.json."""
    entries: dict[str, dict[str, Any]] = {}
    bundle = condition_dir / PREDICTIONS_BUNDLE_NAME
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
        _store[key] = load_eval_cache_entries(condition_dir)
    return _store[key]


def get_eval_cache_entry(condition_dir: Path, event_id: str) -> dict[str, Any] | None:
    return _get_store(condition_dir).get(event_id)


def has_eval_cache_entry(condition_dir: Path, event_id: str) -> bool:
    return event_id in _get_store(condition_dir)


@contextlib.contextmanager
def eval_cache_write_lock(condition_dir: Path):
    """Exclusive lock for predictions.jsonl writes (safe parallel Tier-1 workers)."""
    condition_dir.mkdir(parents=True, exist_ok=True)
    lock_path = condition_dir / ".write.lock"
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def flush_eval_cache(condition_dir: Path, *, remove_legacy: bool = True) -> None:
    store = _get_store(condition_dir)
    condition_dir.mkdir(parents=True, exist_ok=True)
    with eval_cache_write_lock(condition_dir):
        if store:
            records = [store[eid] for eid in sorted(store)]
            write_jsonl_bundle(condition_dir / PREDICTIONS_BUNDLE_NAME, records)
        if remove_legacy:
            for path in condition_dir.glob("evt_*.json"):
                path.unlink()


def upsert_eval_cache_entries(
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
        flush_eval_cache(condition_dir, remove_legacy=remove_legacy)


def consolidate_eval_cache(
    condition_dir: Path,
    *,
    remove_per_event: bool = True,
) -> dict[str, Any]:
    """Merge evt_*.json sprawl into predictions.jsonl."""
    legacy = sorted(condition_dir.glob("evt_*.json"), key=lambda p: p.name)
    invalidate_eval_cache_store(condition_dir)
    store = _get_store(condition_dir)

    if legacy:
        for path in legacy:
            data = json.loads(path.read_text(encoding="utf-8"))
            event_id = data.get("event_id", path.stem)
            store.setdefault(event_id, data)

    if not store and not legacy:
        return {
            "condition_id": condition_dir.name,
            "model_dir": condition_dir.parent.name,
            "format": PREDICTIONS_BUNDLE_NAME,
            "event_count": 0,
            "legacy_evt_removed": 0,
            "skipped": True,
        }

    flush_eval_cache(condition_dir, remove_legacy=remove_per_event)
    return {
        "condition_id": condition_dir.name,
        "model_dir": condition_dir.parent.name,
        "format": PREDICTIONS_BUNDLE_NAME,
        "event_count": len(store),
        "legacy_evt_removed": len(legacy) if remove_per_event else 0,
    }


def consolidate_all_eval_caches(
    root: Path,
    *,
    analytics: bool = False,
    remove_per_event: bool = True,
) -> dict[str, Any]:
    cache_root = eval_cache_root(root, analytics=analytics)
    stats: dict[str, Any] = {"conditions": {}}
    if not cache_root.is_dir():
        return stats

    for model_dir in sorted(cache_root.iterdir()):
        if not model_dir.is_dir():
            continue
        for condition_dir in sorted(model_dir.iterdir()):
            if not condition_dir.is_dir():
                continue
            key = f"{model_dir.name}/{condition_dir.name}"
            stats["conditions"][key] = consolidate_eval_cache(
                condition_dir,
                remove_per_event=remove_per_event,
            )
    return stats
