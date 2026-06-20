"""Apply analytics-purpose lattice exports (Phase 2 appendix)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from boundary.cross import cross
from registry.registry import Registry
from sbb.config import load_config, repo_root
from sbb.types import RawEvent
from transform.analytics_map import map_analytics, schema_id_for
from transform.io import (
    EVENTS_BUNDLE_NAME,
    bundle_checksum,
    index_by_event_id,
    load_jsonl,
    remove_legacy_per_event_exports,
    write_jsonl_bundle,
)

from transform.lattice import LLM_CONDITIONS

SEMANTIC_CONDITIONS = ("sem_coarse", "sem_medium", "sem_fine")
TEXT_CONDITIONS = (
    "raw",
    "redact_bracket",
    "redact_tokenize",
    "redact_surrogate",
)
LLM_TEXT_CONDITIONS = frozenset(LLM_CONDITIONS)


def _build_registry(cfg: dict[str, Any], root: Path) -> Registry:
    reg = Registry()
    policy_path = root / cfg["paths"]["analytics_policy"]
    reg.register(
        "analytics_vendor",
        "analytics",
        policy_path,
        "analytics_schema_medium",
    )
    return reg


def stamp_analytics_provenance(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-stamp observability text exports for analytics consumer."""
    out: list[dict[str, Any]] = []
    for record in records:
        r = dict(record.get("r", {}))
        r["consumer_id"] = "analytics_vendor"
        r["purpose_id"] = "analytics"
        out.append({**record, "r": r})
    return out


def _copy_text_arm(
    src_dir: Path,
    dst_dir: Path,
    *,
    condition_id: str,
) -> list[dict[str, Any]]:
    """Reuse text exports from observability lattice (same z)."""
    records = load_jsonl(src_dir / EVENTS_BUNDLE_NAME)
    return stamp_analytics_provenance(records)


def _transform_semantic_event(
    event: dict[str, Any],
    labels: dict[str, Any],
    persona_row: dict[str, Any],
    condition_id: str,
    registry: Registry,
) -> dict[str, Any]:
    schema_id = schema_id_for(condition_id)
    z = map_analytics(labels, condition_id, persona_row=persona_row)
    raw_obs = RawEvent(
        event_id=event["event_id"],
        persona_id=event["persona_id"],
        journal_text=event["journal_text"],
        assistant_text=event["assistant_text"],
        metadata=event.get("metadata", {}),
    )
    export = cross(
        raw_obs,
        "analytics_vendor",
        registry,
        z=z,
        schema_id=schema_id,
        transform_id=condition_id,
        purpose_id="analytics",
    )
    return {
        "event_id": event["event_id"],
        "persona_id": event["persona_id"],
        "condition_id": condition_id,
        "schema_id": schema_id,
        "z": export.z,
        "r": export.r,
        "verify_outcome": export.verify_outcome,
    }


def run_analytics_lattice(
    cfg: dict[str, Any],
    root: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    conditions = conditions or list(cfg["lattice"]["conditions"])
    obs_root = root / cfg["paths"]["transformed"]
    out_root = root / cfg["paths"]["transformed_analytics"]
    events = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")
    labels_by_id = index_by_event_id(
        load_jsonl(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    )
    persona_by_id = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }

    registry = _build_registry(cfg, root)
    stats: dict[str, Any] = {
        "conditions": {},
        "verify_failures": 0,
        "event_count": len(events),
        "purpose_id": "analytics",
        "consumer_id": "analytics_vendor",
        "policy_id": "analytics_policy_v1",
    }

    for condition_id in conditions:
        cond_dir = out_root / condition_id
        cond_dir.mkdir(parents=True, exist_ok=True)
        remove_legacy_per_event_exports(cond_dir)
        bundle_path = cond_dir / EVENTS_BUNDLE_NAME
        if bundle_path.exists():
            bundle_path.unlink()

        fail_count = 0
        if condition_id in TEXT_CONDITIONS or condition_id in LLM_TEXT_CONDITIONS:
            src = obs_root / condition_id
            if not (src / EVENTS_BUNDLE_NAME).is_file():
                raise FileNotFoundError(
                    f"Missing observability export for {condition_id}: {src}"
                )
            records = _copy_text_arm(src, cond_dir, condition_id=condition_id)
        elif condition_id in SEMANTIC_CONDITIONS:
            records = []
            for event in events:
                lab = labels_by_id[event["event_id"]]
                persona_row = persona_by_id[event["persona_id"]]
                record = _transform_semantic_event(
                    event, lab, persona_row, condition_id, registry
                )
                if record["verify_outcome"] != "pass":
                    fail_count += 1
                records.append(record)
        else:
            raise ValueError(f"Unknown condition: {condition_id}")

        write_jsonl_bundle(bundle_path, records)
        manifest = {
            "condition_id": condition_id,
            "event_count": len(records),
            "format": "events.jsonl",
            "verify_fail_count": fail_count,
            "checksum": bundle_checksum(cond_dir),
            "purpose_id": "analytics",
            "policy_id": "analytics_policy_v1",
        }
        (cond_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        stats["conditions"][condition_id] = manifest

    stats["verify_failures"] = sum(
        s["verify_fail_count"] for s in stats["conditions"].values()
    )
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "manifest.json").write_text(json.dumps(stats, indent=2) + "\n")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transform observability lattice → analytics-purpose exports"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        help="Subset of lattice conditions (default: all in config)",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    root = repo_root()
    stats = run_analytics_lattice(cfg, root, conditions=args.conditions)
    print(json.dumps(stats, indent=2))
    if stats.get("verify_failures", 0) > 0:
        print(
            f"warning: {stats['verify_failures']} exports failed verify",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
