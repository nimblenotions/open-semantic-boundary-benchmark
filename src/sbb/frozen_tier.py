"""Frozen release artifact helpers (split manifest v0, canonical checksums)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SPLIT_MANIFEST_V0 = "data/ground_truth/split_manifest_v0.json"
BOUNDARY_BUNDLE_SCHEMA = "data/schemas/boundary_bundle_v0.schema.json"


def canonical_json_sha256(obj: Any) -> str:
    """SHA256 of canonical JSON (sorted keys, compact separators)."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_split_manifest_v0(root: Path) -> dict[str, Any]:
    """Build split_manifest_v0 from committed splits.json and labels.jsonl."""
    gt = root / "data" / "ground_truth"
    splits = json.loads((gt / "splits.json").read_text(encoding="utf-8"))
    persona_split: dict[str, str] = splits["persona_split"]
    seed = int(splits.get("seed", 42))

    counts: dict[str, int] = {"train": 0, "val": 0, "test": 0}
    for split_name in persona_split.values():
        counts[split_name] = counts.get(split_name, 0) + 1

    test_personas = {pid for pid, s in persona_split.items() if s == "test"}
    test_event_count = 0
    labels_path = gt / "labels.jsonl"
    if labels_path.is_file():
        for line in labels_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("persona_id") in test_personas:
                test_event_count += 1

    return {
        "manifest_version": "v0",
        "sbb_version": "0.1.1",
        "seed": seed,
        "split_policy": "persona_block",
        "split_ratio": {"train": 0.7, "val": 0.1, "test": 0.2},
        "persona_counts": counts,
        "test_event_count": test_event_count,
        "persona_split_source": "data/ground_truth/splits.json",
        "persona_split": persona_split,
    }


def write_split_manifest_v0(root: Path) -> tuple[Path, str]:
    """Write split_manifest_v0.json; return path and canonical SHA256."""
    manifest = build_split_manifest_v0(root)
    out = root / SPLIT_MANIFEST_V0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out, canonical_json_sha256(manifest)
