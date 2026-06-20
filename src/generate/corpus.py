"""Orchestrate corpus generation and JSONL export."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from generate.ground_truth import BENIGN_MODE, FAILURE_MODES, build_event_slots, label_record
from generate.observation import raw_event_record
from generate.persona import generate_personas, personas_to_records


def _persona_splits(
    persona_ids: list[str],
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> dict[str, str]:
    rng = random.Random(seed)
    ids = list(persona_ids)
    rng.shuffle(ids)
    n = len(ids)
    n_train = max(1, int(n * train_ratio))
    n_val = max(0, int(n * val_ratio))
    if n_train + n_val >= n:
        n_val = max(0, n - n_train - 1)
    splits: dict[str, str] = {}
    for i, pid in enumerate(ids):
        if i < n_train:
            splits[pid] = "train"
        elif i < n_train + n_val:
            splits[pid] = "val"
        else:
            splits[pid] = "test"
    return splits


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def generate_corpus(cfg: dict[str, Any], root: Path) -> dict[str, Any]:
    corpus_cfg = cfg["corpus"]
    persona_count = int(cfg.get("persona_count", corpus_cfg.get("persona_count", 10)))
    days = int(corpus_cfg.get("days", 30))
    seed = int(corpus_cfg.get("split_seed", 42))

    rng = random.Random(seed)
    personas = generate_personas(persona_count, rng)
    slots = build_event_slots(personas, rng, days, corpus_cfg)

    events: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    for i, slot in enumerate(slots):
        event_id = f"evt_{i + 1:06d}"
        events.append(raw_event_record(slot, event_id, rng))
        labels.append(label_record(slot, event_id))

    persona_records = personas_to_records(personas)
    splits = _persona_splits(
        [p.id for p in personas],
        seed,
        float(corpus_cfg.get("train_ratio", 0.8)),
        float(corpus_cfg.get("val_ratio", 0.1)),
    )
    for rec in persona_records:
        rec["split"] = splits[rec["persona_id"]]
    for lab in labels:
        lab["split"] = splits[lab["persona_id"]]

    raw_dir = root / cfg["paths"]["raw"]
    gt_dir = root / cfg["paths"]["ground_truth"]
    events_path = raw_dir / "events.jsonl"
    labels_path = gt_dir / "labels.jsonl"
    persona_path = gt_dir / "persona_table.jsonl"
    splits_path = gt_dir / "splits.json"

    write_jsonl(events_path, events)
    write_jsonl(labels_path, labels)
    write_jsonl(persona_path, persona_records)
    splits_path.write_text(json.dumps({"persona_split": splits, "seed": seed}, indent=2) + "\n")

    failure_counts = {m: 0 for m in FAILURE_MODES + [BENIGN_MODE]}
    for lab in labels:
        failure_counts[lab["failure_mode"]] = failure_counts.get(lab["failure_mode"], 0) + 1

    rare_personas = sum(1 for p in personas if p.quasi_id_rarity == "rare")
    manifest = {
        "status": "generated",
        "study": cfg.get("study", {}).get("name", "sbb-obs-v0.1"),
        "persona_count": persona_count,
        "event_count": len(events),
        "failure_labeled_count": sum(
            1 for lab in labels if lab["failure_mode"] != BENIGN_MODE
        ),
        "failure_mode_counts": failure_counts,
        "rare_persona_count": rare_personas,
        "checksums": {
            "events.jsonl": _checksum(events_path),
            "labels.jsonl": _checksum(labels_path),
        },
        "seed": seed,
    }
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    return manifest
