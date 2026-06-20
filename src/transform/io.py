"""JSONL / bundle I/O for transforms."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EVENTS_BUNDLE_NAME = "events.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def index_by_event_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["event_id"]: r for r in rows}


def write_jsonl_bundle(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        for record in records
    )
    path.write_text(body + "\n", encoding="utf-8")


def write_event_export(path: Path, record: dict[str, Any]) -> None:
    """Legacy per-event JSON writer (dev/cache layout)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bundle_checksum(condition_dir: Path) -> str:
    bundle = condition_dir / EVENTS_BUNDLE_NAME
    if not bundle.is_file():
        return ""
    return hashlib.sha256(bundle.read_bytes()).hexdigest()[:16]


def condition_has_exports(condition_dir: Path) -> bool:
    if (condition_dir / EVENTS_BUNDLE_NAME).is_file():
        return True
    return any(condition_dir.glob("evt_*.json"))


def load_condition_exports(condition_dir: Path) -> dict[str, dict[str, Any]]:
    """Load exports from events.jsonl (preferred) or legacy evt_*.json files."""
    bundle = condition_dir / EVENTS_BUNDLE_NAME
    if bundle.is_file():
        return index_by_event_id(load_jsonl(bundle))
    exports: dict[str, dict[str, Any]] = {}
    for path in sorted(condition_dir.glob("evt_*.json")):
        exports[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return exports


def remove_legacy_per_event_exports(condition_dir: Path) -> int:
    removed = 0
    for path in condition_dir.glob("evt_*.json"):
        path.unlink()
        removed += 1
    return removed
