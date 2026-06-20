"""Materialize LLM cache → observability and analytics events.jsonl bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transform.io import (
    EVENTS_BUNDLE_NAME,
    bundle_checksum,
    load_jsonl,
    remove_legacy_per_event_exports,
    write_jsonl_bundle,
)
from transform.lattice import LLM_CONDITIONS
from transform.llm_cache_io import (
    CACHE_BUNDLE_NAME,
    consolidate_llm_cache,
    load_llm_cache_entries,
    llm_condition_cache_dir,
)
from transform.run_analytics_transforms import stamp_analytics_provenance


def cache_entry_to_export(
    entry: dict[str, Any],
    event: dict[str, Any],
    *,
    condition_id: str,
    mode: str,
) -> dict[str, Any]:
    z = entry["z"]
    return {
        "event_id": event["event_id"],
        "persona_id": event["persona_id"],
        "condition_id": condition_id,
        "schema_id": "redacted_text",
        "z": {
            "journal_text": z["journal_text"],
            "assistant_text": z["assistant_text"],
        },
        "r": {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "llm_sanitize_mode": mode,
            "llm_model": entry.get("model"),
            "prompt_version": entry.get("prompt_version", "v1"),
            "event_id": event["event_id"],
            "verify_outcome": "pass",
        },
        "verify_outcome": "pass",
    }


def materialize_llm_condition(
    cfg: dict[str, Any],
    root: Path,
    condition_id: str,
    *,
    consolidate_cache: bool = False,
    require_full_corpus: bool = False,
) -> dict[str, Any]:
    if condition_id not in LLM_CONDITIONS:
        raise ValueError(f"Not an LLM appendix condition: {condition_id}")

    mode = LLM_CONDITIONS[condition_id]
    cache_dir = llm_condition_cache_dir(root, cfg, condition_id)
    if not cache_dir.is_dir():
        raise FileNotFoundError(f"Missing LLM cache dir: {cache_dir}")

    consolidate_stats: dict[str, Any] | None = None
    if consolidate_cache:
        consolidate_stats = consolidate_llm_cache(cache_dir)

    cache_by_id = load_llm_cache_entries(cache_dir)
    events = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")

    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for event in events:
        entry = cache_by_id.get(event["event_id"])
        if entry is None:
            missing.append(event["event_id"])
            continue
        records.append(
            cache_entry_to_export(entry, event, condition_id=condition_id, mode=mode)
        )

    if require_full_corpus and missing:
        raise ValueError(
            f"{condition_id}: missing cache for {len(missing)} events "
            f"(first: {missing[0]})"
        )

    obs_dir = root / cfg["paths"]["transformed"] / condition_id
    obs_dir.mkdir(parents=True, exist_ok=True)
    remove_legacy_per_event_exports(obs_dir)
    write_jsonl_bundle(obs_dir / EVENTS_BUNDLE_NAME, records)
    obs_manifest = {
        "condition_id": condition_id,
        "event_count": len(records),
        "format": EVENTS_BUNDLE_NAME,
        "verify_fail_count": 0,
        "checksum": bundle_checksum(obs_dir),
        "source": str(cache_dir.relative_to(root)),
        "cache_format": CACHE_BUNDLE_NAME if (cache_dir / CACHE_BUNDLE_NAME).is_file() else "evt_*.json",
    }
    if missing:
        obs_manifest["missing_cache_count"] = len(missing)
    (obs_dir / "manifest.json").write_text(
        json.dumps(obs_manifest, indent=2) + "\n", encoding="utf-8"
    )

    analytics_dir = root / cfg["paths"]["transformed_analytics"] / condition_id
    analytics_dir.mkdir(parents=True, exist_ok=True)
    remove_legacy_per_event_exports(analytics_dir)
    analytics_records = stamp_analytics_provenance(records)
    write_jsonl_bundle(analytics_dir / EVENTS_BUNDLE_NAME, analytics_records)
    ana_manifest = {
        **obs_manifest,
        "purpose_id": "analytics",
        "policy_id": "analytics_policy_v1",
        "checksum": bundle_checksum(analytics_dir),
    }
    (analytics_dir / "manifest.json").write_text(
        json.dumps(ana_manifest, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "condition_id": condition_id,
        "obs_event_count": len(records),
        "analytics_event_count": len(analytics_records),
        "missing_cache_count": len(missing),
        "consolidate": consolidate_stats,
        "obs_dir": str(obs_dir.relative_to(root)),
        "analytics_dir": str(analytics_dir.relative_to(root)),
    }


def materialize_llm_conditions(
    cfg: dict[str, Any],
    root: Path,
    *,
    conditions: list[str] | None = None,
    consolidate_cache: bool = False,
    require_full_corpus: bool = False,
) -> dict[str, Any]:
    if conditions is None:
        conditions = [
            c for c in cfg["lattice"]["conditions"] if c in LLM_CONDITIONS
        ]
        if not conditions:
            conditions = list(cfg.get("eval", {}).get("appendix_conditions", []))
    stats: dict[str, Any] = {"conditions": {}}
    for condition_id in conditions:
        stats["conditions"][condition_id] = materialize_llm_condition(
            cfg,
            root,
            condition_id,
            consolidate_cache=consolidate_cache,
            require_full_corpus=require_full_corpus,
        )
    return stats
