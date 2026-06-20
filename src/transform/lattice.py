"""Apply full export lattice and write data/transformed/{condition}/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from boundary.cross import cross
from registry.registry import Registry
from sbb.types import RawEvent
from transform.io import (
    EVENTS_BUNDLE_NAME,
    bundle_checksum,
    index_by_event_id,
    load_jsonl,
    remove_legacy_per_event_exports,
    write_jsonl_bundle,
)
from transform.llm_sanitize import llm_sanitize_event
from transform.redact import redact_event
from transform.semantic_map import map_semantic, schema_id_for
from transform.spans import TokenVault
from transform.surrogate import SurrogateVault, surrogate_event
from transform.tokenize import tokenize_event

SEMANTIC_CONDITIONS = ("sem_coarse", "sem_medium", "sem_fine")
RULE_REDACT = "redact_bracket"
RULE_TOKENIZE = "redact_tokenize"
RULE_SURROGATE = "redact_surrogate"
# Appendix-only LLM arms — not in cfg["lattice"]["conditions"] for v0.1.
# Run via: scripts/warm_llm_cache.py or
#   python -m transform.run_transforms --conditions redact_llm_substitute redact_llm_rephrase
LLM_CONDITIONS = {
    "redact_llm_substitute": "substitute",
    "redact_llm_rephrase": "rephrase",
}


def _checksum_dir(condition_dir: Path) -> str:
    return bundle_checksum(condition_dir)


def _build_registry(cfg: dict[str, Any], root: Path) -> Registry:
    reg = Registry()
    policy_path = root / cfg["paths"]["policy"]
    study = cfg.get("study", {})
    reg.register(
        study.get("consumer_id", "obs_vendor"),
        study.get("purpose_id", "observability"),
        policy_path,
        "obs_schema_medium",
    )
    return reg


def _build_token_vaults(events: list[dict[str, Any]]) -> dict[str, TokenVault]:
    vaults: dict[str, TokenVault] = {}
    for event in events:
        pid = event["persona_id"]
        if pid not in vaults:
            vaults[pid] = TokenVault(pid)
    return vaults


def _build_surrogate_vaults(
    events: list[dict[str, Any]], cfg: dict[str, Any]
) -> dict[str, SurrogateVault]:
    seed = int(cfg.get("transform", {}).get("surrogate", {}).get("seed", 42))
    vaults: dict[str, SurrogateVault] = {}
    for event in events:
        pid = event["persona_id"]
        if pid not in vaults:
            vaults[pid] = SurrogateVault(pid, seed=seed)
    return vaults


def transform_event(
    event: dict[str, Any],
    labels: dict[str, Any],
    condition_id: str,
    registry: Registry,
    cfg: dict[str, Any],
    *,
    token_vaults: dict[str, TokenVault],
    surrogate_vaults: dict[str, SurrogateVault],
    root: Path,
) -> dict[str, Any]:
    study = cfg.get("study", {})
    consumer_id = study.get("consumer_id", "obs_vendor")
    raw_obs = RawEvent(
        event_id=event["event_id"],
        persona_id=event["persona_id"],
        journal_text=event["journal_text"],
        assistant_text=event["assistant_text"],
        metadata=event.get("metadata", {}),
    )

    if condition_id == "raw":
        z = {
            "journal_text": event["journal_text"],
            "assistant_text": event["assistant_text"],
        }
        r = {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "raw_reference",
            "transform_id": "raw",
            "event_id": event["event_id"],
            "verify_outcome": "pass",
        }
        return {
            "event_id": event["event_id"],
            "persona_id": event["persona_id"],
            "condition_id": condition_id,
            "schema_id": "raw_reference",
            "z": z,
            "r": r,
            "verify_outcome": "pass",
        }

    if condition_id == RULE_REDACT:
        z = redact_event(event["journal_text"], event["assistant_text"], "bracket")
        r = {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "redact_operator": "labeled_placeholder",
            "event_id": event["event_id"],
            "fields_suppressed": ["medication_names", "occupation_spans", "time_spans"],
            "verify_outcome": "pass",
        }
        return {
            "event_id": event["event_id"],
            "persona_id": event["persona_id"],
            "condition_id": condition_id,
            "schema_id": "redacted_text",
            "z": z,
            "r": r,
            "verify_outcome": "pass",
        }

    if condition_id == RULE_TOKENIZE:
        vault = token_vaults[event["persona_id"]]
        z = tokenize_event(
            event["journal_text"],
            event["assistant_text"],
            event["persona_id"],
            vault,
        )
        r = {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "redact_operator": "stable_tokenize",
            "event_id": event["event_id"],
            "fields_suppressed": ["raw_medication_literals", "raw_occupation_literals"],
            "verify_outcome": "pass",
        }
        return {
            "event_id": event["event_id"],
            "persona_id": event["persona_id"],
            "condition_id": condition_id,
            "schema_id": "redacted_text",
            "z": z,
            "r": r,
            "verify_outcome": "pass",
        }

    if condition_id == RULE_SURROGATE:
        vault = surrogate_vaults[event["persona_id"]]
        z = surrogate_event(
            event["journal_text"],
            event["assistant_text"],
            event["persona_id"],
            vault,
        )
        r = {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "redact_operator": "i2b2_surrogate",
            "event_id": event["event_id"],
            "fields_suppressed": ["raw_medication_literals", "raw_occupation_literals"],
            "verify_outcome": "pass",
        }
        return {
            "event_id": event["event_id"],
            "persona_id": event["persona_id"],
            "condition_id": condition_id,
            "schema_id": "redacted_text",
            "z": z,
            "r": r,
            "verify_outcome": "pass",
        }

    if condition_id in LLM_CONDITIONS:
        mode = LLM_CONDITIONS[condition_id]
        z = llm_sanitize_event(
            event["journal_text"],
            event["assistant_text"],
            mode,
            cfg,
            root,
            condition_id=condition_id,
            event_id=event["event_id"],
        )
        r = {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "llm_sanitize_mode": mode,
            "llm_model": cfg.get("transform", {})
            .get("llm", {})
            .get("model", cfg.get("eval", {}).get("tier1", {}).get("primary_model")),
            "prompt_version": "v1",
            "event_id": event["event_id"],
            "verify_outcome": "pass",
        }
        return {
            "event_id": event["event_id"],
            "persona_id": event["persona_id"],
            "condition_id": condition_id,
            "schema_id": "redacted_text",
            "z": z,
            "r": r,
            "verify_outcome": "pass",
        }

    if condition_id in SEMANTIC_CONDITIONS:
        schema_id = schema_id_for(condition_id)
        z = map_semantic(labels, condition_id)
        export = cross(
            raw_obs,
            consumer_id,
            registry,
            z=z,
            schema_id=schema_id,
            transform_id=condition_id,
            purpose_id=study.get("purpose_id", "observability"),
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

    raise ValueError(f"Unknown condition: {condition_id}")


def run_lattice(
    cfg: dict[str, Any],
    root: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    conditions = conditions or cfg["lattice"]["conditions"]
    events = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")
    labels_list = load_jsonl(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    labels_by_id = index_by_event_id(labels_list)
    token_vaults = _build_token_vaults(events)
    surrogate_vaults = _build_surrogate_vaults(events, cfg)

    out_root = root / cfg["paths"]["transformed"]
    allowed = set(cfg["lattice"]["conditions"])
    for old_dir in out_root.iterdir():
        if old_dir.is_dir() and old_dir.name not in allowed:
            shutil.rmtree(old_dir)
    registry = _build_registry(cfg, root)

    stats: dict[str, Any] = {
        "conditions": {},
        "verify_failures": 0,
        "event_count": len(events),
    }

    for condition_id in conditions:
        cond_dir = out_root / condition_id
        cond_dir.mkdir(parents=True, exist_ok=True)
        remove_legacy_per_event_exports(cond_dir)
        bundle_path = cond_dir / EVENTS_BUNDLE_NAME
        if bundle_path.exists():
            bundle_path.unlink()

        fail_count = 0
        records: list[dict[str, Any]] = []
        for i, event in enumerate(events):
            lab = labels_by_id[event["event_id"]]
            record = transform_event(
                event,
                lab,
                condition_id,
                registry,
                cfg,
                token_vaults=token_vaults,
                surrogate_vaults=surrogate_vaults,
                root=root,
            )
            if record["verify_outcome"] != "pass":
                fail_count += 1
            records.append(record)
            if condition_id in LLM_CONDITIONS and (i + 1) % 25 == 0:
                print(
                    f"  {condition_id}: {i + 1}/{len(events)}",
                    flush=True,
                )

        write_jsonl_bundle(bundle_path, records)

        manifest = {
            "condition_id": condition_id,
            "event_count": len(events),
            "format": "events.jsonl",
            "verify_fail_count": fail_count,
            "checksum": _checksum_dir(cond_dir),
        }
        (cond_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        stats["conditions"][condition_id] = manifest

    stats["verify_failures"] = sum(
        s["verify_fail_count"] for s in stats["conditions"].values()
    )
    (out_root / "manifest.json").write_text(json.dumps(stats, indent=2) + "\n")
    return stats
