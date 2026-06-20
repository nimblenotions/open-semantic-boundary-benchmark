"""Convert legacy per-event JSON exports to events.jsonl bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sbb.config import load_config, repo_root
from transform.io import (
    EVENTS_BUNDLE_NAME,
    bundle_checksum,
    condition_has_exports,
    load_condition_exports,
    remove_legacy_per_event_exports,
    write_jsonl_bundle,
)


def bundle_condition_dir(
    condition_dir: Path,
    *,
    remove_per_event: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    bundle_path = condition_dir / EVENTS_BUNDLE_NAME
    legacy = list(condition_dir.glob("evt_*.json"))
    if bundle_path.is_file() and not force and not legacy:
        exports = load_condition_exports(condition_dir)
        return {
            "condition_id": condition_dir.name,
            "event_count": len(exports),
            "format": "events.jsonl",
            "checksum": bundle_checksum(condition_dir),
            "skipped": True,
        }

    if legacy:
        records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(legacy, key=lambda p: p.name)
        ]
    elif bundle_path.is_file():
        exports = load_condition_exports(condition_dir)
        records = [exports[eid] for eid in sorted(exports)]
    else:
        return {
            "condition_id": condition_dir.name,
            "event_count": 0,
            "format": "events.jsonl",
            "checksum": "",
            "skipped": True,
        }

    write_jsonl_bundle(bundle_path, records)
    removed = remove_legacy_per_event_exports(condition_dir) if remove_per_event else 0

    manifest = {
        "condition_id": condition_dir.name,
        "event_count": len(records),
        "format": "events.jsonl",
        "verify_fail_count": sum(1 for r in records if r.get("verify_outcome") != "pass"),
        "checksum": bundle_checksum(condition_dir),
        "legacy_evt_removed": removed,
    }
    (condition_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def bundle_all(
    transformed_root: Path,
    *,
    remove_per_event: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    stats: dict[str, Any] = {"conditions": {}, "event_count": 0, "verify_failures": 0}
    for condition_dir in sorted(transformed_root.iterdir()):
        if not condition_dir.is_dir():
            continue
        if condition_dir.name.startswith("."):
            continue
        if not condition_has_exports(condition_dir):
            continue
        manifest = bundle_condition_dir(
            condition_dir,
            remove_per_event=remove_per_event,
            force=force,
        )
        stats["conditions"][condition_dir.name] = manifest
        if manifest.get("event_count"):
            stats["event_count"] = manifest["event_count"]
        stats["verify_failures"] += manifest.get("verify_fail_count", 0)
    (transformed_root / "manifest.json").write_text(json.dumps(stats, indent=2) + "\n")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bundle per-event transform JSON into events.jsonl per condition"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--keep-per-event",
        action="store_true",
        help="Keep legacy evt_*.json files after bundling",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild events.jsonl from legacy evt_*.json even if bundle exists",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    root = repo_root()
    stats = bundle_all(
        root / cfg["paths"]["transformed"],
        remove_per_event=not args.keep_per_event,
        force=args.force,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
