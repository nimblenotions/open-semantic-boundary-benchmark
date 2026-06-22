"""Load labels, splits, and frozen transform exports for evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transform.io import index_by_event_id, load_jsonl


def load_labels(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_splits(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["persona_split"]


def event_split(persona_id: str, persona_split: dict[str, str]) -> str:
    return persona_split[persona_id]


def load_raw_events(path: Path) -> dict[str, dict[str, Any]]:
    return index_by_event_id(load_jsonl(path))


def join_eval_rows(
    labels: list[dict[str, Any]],
    exports: dict[str, dict[str, Any]],
    persona_split: dict[str, str],
    *,
    split: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in labels:
        event_id = label["event_id"]
        if event_id not in exports:
            continue
        row_split = event_split(label["persona_id"], persona_split)
        if split is not None and row_split != split:
            continue
        export = exports[event_id]
        rows.append(
            {
                "event_id": event_id,
                "persona_id": label["persona_id"],
                "split": row_split,
                "label": label,
                "export": export,
            }
        )
    return rows
