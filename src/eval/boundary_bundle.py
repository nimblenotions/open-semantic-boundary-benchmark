"""Emit Open SBB boundary bundle v0 from published observability metrics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sbb.frozen_tier import SPLIT_MANIFEST_V0
from typing import Any

from eval.study import LATTICE_RULE_SEMANTIC, _condition_trial4, _utility_f1


def _linkage_score(metrics: dict[str, Any]) -> float:
    t4 = _condition_trial4(metrics)
    if t4:
        return float(t4.get("combined_linkage_score", t4.get("persona_top1", 1.0)))
    return float(metrics.get("tier0", {}).get("risk", {}).get("persona_top1", 1.0))


def schema_for_condition(
    condition_id: str,
    cfg: dict[str, Any],
) -> dict[str, str] | None:
    """Return governed schema ref for semantic lattice arms only."""
    schema_key = {
        "sem_coarse": "coarse",
        "sem_medium": "medium",
        "sem_fine": "fine",
    }.get(condition_id)
    if schema_key is None:
        return None
    return {
        "id": f"obs_schema_{schema_key}",
        "path": cfg["paths"]["schemas"][schema_key],
    }


def export_kind_for_condition(condition_id: str) -> str:
    if condition_id.startswith("sem_"):
        return "semantic"
    return "text_redaction"


def choose_recommended_condition(
    primary_metrics: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    """Pick highest utility among lattice arms with linkage below redact_bracket."""
    lattice = {
        cid: m for cid, m in primary_metrics.items() if cid in LATTICE_RULE_SEMANTIC
    }
    bracket_linkage = _linkage_score(lattice.get("redact_bracket", {}))

    candidates: list[tuple[str, float]] = []
    for condition_id, metrics in lattice.items():
        f1 = _utility_f1(metrics)
        linkage = _linkage_score(metrics)
        if linkage <= bracket_linkage + 1e-9:
            candidates.append((condition_id, f1))

    if not candidates:
        return "sem_medium", "fallback: no arm below redact_bracket linkage"

    best = max(candidates, key=lambda item: item[1])
    return best[0], (
        f"highest failure_mode_macro_f1 ({best[1]:.3f}) among conditions with "
        f"linkage <= redact_bracket ({bracket_linkage:.3f})"
    )


def build_boundary_bundle(
    metrics: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    primary = {
        cid: m
        for cid, m in metrics.get("conditions", {}).items()
        if m.get("role") in ("primary", "frozen")
    }
    recommended, rule = choose_recommended_condition(primary)
    schema = schema_for_condition(recommended, cfg)

    bundle: dict[str, Any] = {
        "sbb_version": "0.1.1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "purpose": {
            "id": cfg.get("study", {}).get("purpose_id", "observability"),
            "consumer_id": cfg.get("study", {}).get("consumer_id", "obs_vendor"),
            "task_labels": ["failure_mode", "error_stage"],
        },
        "policy": {
            "id": "obs_policy_v1",
            "path": cfg["paths"]["policy"],
        },
        "export_kind": export_kind_for_condition(recommended),
        "schema": schema,
        "transform_ladder": list(cfg["lattice"]["conditions"]),
        "recommended_condition": recommended,
        "recommended_condition_rule": rule,
        "i1_metrics_ref": str(
            Path(cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2"))
            / "metrics.json"
        ),
        "split_manifest": SPLIT_MANIFEST_V0,
        "hypotheses": metrics.get("hypotheses", {}),
    }
    return bundle


def write_boundary_bundle(
    metrics: dict[str, Any],
    cfg: dict[str, Any],
    out_path: Path,
) -> Path:
    bundle = build_boundary_bundle(metrics, cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return out_path
