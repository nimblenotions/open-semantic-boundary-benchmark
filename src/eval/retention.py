"""Embedding retention diagnostic (Option D): cosine similarity raw vs export.

Appendix metric — measures distributional semantic overlap between raw prose
and transformed exports. Retention != task utility (Tier-0 F1) but helps explain
information loss across the lattice.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from eval.embeddings import (
    Embedder,
    cosine_similarity,
)
from eval.export_text import export_text_for_embedding
from eval.io import load_raw_events
from eval.observability_task import condition_kind, serialize_text_export
from eval.study import resolve_eval_conditions
from transform.io import load_condition_exports


def raw_text_reference(raw_event: dict[str, Any]) -> str:
    """Canonical raw prose: journal + assistant (matches text export layout)."""
    return serialize_text_export(
        {
            "journal_text": raw_event.get("journal_text", ""),
            "assistant_text": raw_event.get("assistant_text", ""),
        }
    )


def export_text_for_retention(export: dict[str, Any]) -> str:
    """Serialize export z the way retention compares against raw prose."""
    return export_text_for_embedding(export)


def retention_pair(
    raw_event: dict[str, Any], export: dict[str, Any]
) -> tuple[str, str]:
    return raw_text_reference(raw_event), export_text_for_retention(export)


def _aggregate(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "n_events": len(values),
    }


def evaluate_condition_retention(
    exports: dict[str, dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    embedder: Embedder,
    *,
    event_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Per-event cosine sim; aggregate mean/median for one condition."""
    ids = event_ids or sorted(exports.keys())
    pairs: list[tuple[str, str]] = []
    used_ids: list[str] = []
    for event_id in ids:
        if event_id not in exports or event_id not in raw_by_id:
            continue
        ref, exp = retention_pair(raw_by_id[event_id], exports[event_id])
        pairs.append((ref, exp))
        used_ids.append(event_id)

    if not pairs:
        return {"per_event": {}, "aggregate": _aggregate([])}

    ref_texts = [p[0] for p in pairs]
    exp_texts = [p[1] for p in pairs]
    ref_vecs = embedder.embed(ref_texts)
    exp_vecs = embedder.embed(exp_texts)

    per_event: dict[str, float] = {}
    sims: list[float] = []
    for event_id, rv, ev in zip(used_ids, ref_vecs, exp_vecs, strict=True):
        sim = cosine_similarity(rv, ev)
        per_event[event_id] = sim
        sims.append(sim)

    return {"per_event": per_event, "aggregate": _aggregate(sims)}


def run_retention(
    cfg: dict[str, Any],
    root: Path,
    embedder: Embedder,
    *,
    event_ids: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run retention diagnostic across eval conditions."""
    eval_conditions = resolve_eval_conditions(cfg, root)
    raw_by_id = load_raw_events(root / cfg["paths"]["raw"] / "events.jsonl")
    transformed_root = root / cfg["paths"]["transformed"]

    condition_results: dict[str, dict[str, Any]] = {}
    for condition_id, role in eval_conditions:
        exports = load_condition_exports(transformed_root / condition_id)
        if not exports:
            continue
        result = evaluate_condition_retention(
            exports, raw_by_id, embedder, event_ids=event_ids
        )
        agg = result["aggregate"]
        entry: dict[str, Any] = {
            "role": role,
            "kind": condition_kind(condition_id),
            "cosine_mean": agg["mean"],
            "cosine_median": agg["median"],
            "cosine_std": agg["std"],
            "cosine_min": agg["min"],
            "cosine_max": agg["max"],
            "n_events": agg["n_events"],
        }
        if metrics and condition_id in metrics.get("conditions", {}):
            tier0 = metrics["conditions"][condition_id].get("tier0", {})
            utility = tier0.get("utility", {})
            entry["tier0_failure_mode_macro_f1"] = utility.get("failure_mode_macro_f1")
        condition_results[condition_id] = entry

    embed_model = getattr(embedder, "model_name", "mock")

    return {
        "study": cfg.get("study", {}).get("name", "sbb-obs"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "metric": "embedding_retention_cosine",
        "embedding_model": embed_model,
        "primary_metric_note": (
            "Diagnostic appendix only — retention measures distributional overlap "
            "with raw prose, not task utility (Tier-0 F1)."
        ),
        "semantic_reference": "raw journal+assistant text (serialize_text_export layout)",
        "semantic_export": "json.dumps(flatten_semantic_z(z), sort_keys=True)",
        "text_export": "serialize_text_export(z) vs same layout from raw events",
        "conditions": condition_results,
        "notes": {
            "not_primary_metric": True,
            "interpretation": (
                "High cosine similarity indicates the export embedding stays close "
                "to raw text in MiniLM space; low utility F1 with high retention "
                "suggests task-relevant signal is structured differently than prose."
            ),
            "sampled": event_ids is not None,
            "n_sampled_events": len(event_ids) if event_ids else None,
        },
    }
