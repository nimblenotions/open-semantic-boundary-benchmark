"""Post-acceptance Ta-5 cohort-utility audit.

Writes only under outputs/post_acceptance_experiments/ta5_cohort_audit/.
Does not modify outputs/pilot_v2, data/eval_cache_analytics, or the manuscript.

Compares historical cohort modes (mixed, export-symmetric) with the published
CIKM protocol (assessor-symmetric; paper_protocol.ta5_cohort.primary =
track_c_assessor_symmetric). Not invoked by make repro-cikm-2026.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.advisor_figures import (  # noqa: E402
    DEFAULT_R_MAX_FOCAL,
    REGRET_PURPOSES,
    build_cross_purpose_regret_matrix,
)
from eval.analytics_cohort import (  # noqa: E402
    _group_by_persona,
    _persona_features,
    _persona_features_from_predictions,
    evaluate_cohort_export_symmetric,
    evaluate_cohort_from_assessor_predictions,
    evaluate_cohort_from_tier1_predictions,
    evaluate_cohort_mixed_frozen,
    evaluate_cohort_tasks,
    inspect_feature_schema,
)
from eval.io import join_eval_rows, load_labels, load_splits  # noqa: E402
from eval.operative_selection import (  # noqa: E402
    DEFAULT_R_MAX_GRID,
    TASK_BUNDLES,
    build_condition_points,
    risk_constrained_selection,
    task_bundle_feasibility,
)
from eval.study import resolve_eval_conditions  # noqa: E402
from eval.tier1_analytics_consumer import (  # noqa: E402
    PROMPT_VERSION,
    _tier1_cfg,
    build_analytics_system_prompt,
    cache_stats_for_rows,
    load_analytics_vocab,
    load_cached_prediction,
    predict_rows,
)
from eval.paper_protocol import paper_protocol, ta5_output_dir  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402
from transform.analytics_map import cohort_segment  # noqa: E402
from transform.io import load_condition_exports, load_jsonl  # noqa: E402

FOCAL_R_MAX = (0.40, 0.45, 0.50, 0.55)
CONDITION_FAMILIES = {
    "raw": "raw",
    "redact_bracket": "bracket",
    "redact_tokenize": "token",
    "redact_surrogate": "surrogate",
    "redact_llm_substitute": "llm",
    "redact_llm_rephrase": "llm",
    "sem_coarse": "semantic",
    "sem_medium": "semantic",
    "sem_fine": "semantic",
}


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _git_meta(root: Path) -> dict[str, str]:
    def _run(args: list[str]) -> str:
        try:
            return subprocess.check_output(args, cwd=root, text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "commit_short": _run(["git", "rev-parse", "--short", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "status_short": _run(["git", "status", "-sb"]),
        "diffstat": _run(["git", "diff", "--stat", "--", "src/eval/analytics_cohort.py"]),
    }


def _z_key_inventory(exports: dict[str, dict[str, Any]], n: int = 50) -> dict[str, Any]:
    keys: Counter[str] = Counter()
    types: set[str] = set()
    for i, rec in enumerate(exports.values()):
        if i >= n:
            break
        z = rec.get("z")
        types.add(type(z).__name__)
        if isinstance(z, dict):
            keys.update(z.keys())
    return {
        "z_python_types": sorted(types),
        "z_keys_in_sample": dict(keys),
        "sample_n": min(n, len(exports)),
    }


def _load_predictions(
    rows: list[dict], *, model: str, condition_id: str, root: Path
) -> dict[str, dict[str, str]]:
    preds: dict[str, dict[str, str]] = {}
    for row in rows:
        cached = load_cached_prediction(root, model, condition_id, row["event_id"])
        if cached is not None:
            preds[row["event_id"]] = cached
    return preds


def _class_distribution(
    persona_ids: list[str], persona_table: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    labels = [cohort_segment(persona_table[pid]) for pid in persona_ids]
    counts = dict(Counter(labels))
    logging = Counter(persona_table[pid]["logging_propensity"] for pid in persona_ids)
    engagement = Counter(persona_table[pid]["clinical_engagement"] for pid in persona_ids)
    return {
        "n": len(persona_ids),
        "n_classes": len(counts),
        "cohort_segment": counts,
        "logging_propensity": dict(logging),
        "clinical_engagement": dict(engagement),
    }


def _rank(scores: dict[str, float]) -> list[dict[str, Any]]:
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        {"rank": i + 1, "condition_id": cid, "score": sc}
        for i, (cid, sc) in enumerate(ordered)
    ]


def reconstruct(ctx: dict[str, Any]) -> dict[str, Any]:
    """Describe the mixed pipeline recorded in frozen pilot_v2 analytics metrics.

    That mixed path (export features on train, assessor features on test) is
    historical. It is not the published CIKM Ta-5 protocol.
    """
    root: Path = ctx["root"]
    cfg = ctx["cfg"]
    persona_table = ctx["persona_table"]
    persona_split = ctx["persona_split"]
    frozen = ctx["frozen_analytics"]
    model = ctx["model"]
    seed = ctx["seed"]

    split_ids: dict[str, list[str]] = defaultdict(list)
    for pid, split in persona_split.items():
        split_ids[split].append(pid)

    reconstruction = {
        "target": {
            "name": "cohort_segment",
            "construction": "logging_propensity × clinical_engagement",
            "formula": "{logging_propensity}_{clinical_engagement}",
            "n_possible_classes": 9,
            "logging_levels": ["low", "medium", "high"],
            "engagement_levels": ["avoidant", "moderate", "anxious-hypervigilant"],
            "metric": "macro-F1",
            "classifier": {
                "family": "RandomForestClassifier",
                "n_estimators": 50,
                "random_state": seed,
                "class_weight": "balanced",
                "vectorizer": "DictVectorizer(sparse=False)",
            },
        },
        "splits": {
            "rule": "whole-persona 70/10/20, split_seed=42",
            "train": _class_distribution(sorted(split_ids["train"]), persona_table),
            "val": _class_distribution(sorted(split_ids["val"]), persona_table),
            "test": _class_distribution(sorted(split_ids["test"]), persona_table),
            "note": "Val personas are unused by Ta-5.",
        },
        "event_count_ranges": {
            "low": [10, 15],
            "medium": [25, 40],
            "high": [60, 100],
            "note": "Non-overlapping ranges; event_count identifies logging_propensity exactly.",
        },
        "frozen_pipeline": {
            "note": (
                "Historical mixed path stored in outputs/pilot_v2/analytics_metrics.json "
                "(export z on train, Tier-1 assessor outputs on test). "
                "Not the published CIKM Ta-5 protocol, which is assessor-symmetric."
            ),
            "track_a_function": "evaluate_cohort_from_tier1_predictions",
            "track_a_field": "conditions.*.tier1_cohort.cohort_segment_macro_f1",
            "track_b_function": "evaluate_cohort_tasks",
            "track_b_field": "conditions.*.cohort.cohort_segment_macro_f1",
            "train_features": "export z fields via _persona_features",
            "test_features": "Tier-1 assessor outputs via _persona_features_from_predictions",
            "assessor": {
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "event_fields": [
                    "medication_class",
                    "side_effect_signal",
                    "adherence_signal",
                ],
                "split_scored": "test only (zero-shot; train unused by evaluate_tier1_analytics)",
            },
        },
        "sem_fine_note": (
            "sem_fine oracle z contains cohort_segment and engagement_trend, "
            "but _persona_features does not read those keys."
        ),
        "conditions": {},
    }

    analytics_root = root / cfg["paths"]["transformed_analytics"]
    for condition_id, role in resolve_eval_conditions(cfg, root):
        cond_dir = analytics_root / condition_id
        if not cond_dir.is_dir():
            continue
        exports = load_condition_exports(cond_dir)
        if not exports:
            continue
        train_rows = join_eval_rows(
            ctx["labels"], exports, persona_split, split="train"
        )
        test_rows = join_eval_rows(
            ctx["labels"], exports, persona_split, split="test"
        )
        test_preds = _load_predictions(
            test_rows, model=model, condition_id=condition_id, root=root
        )
        train_x = [
            _persona_features(evs, condition_id=condition_id)
            for _pid, evs in sorted(_group_by_persona(train_rows).items())
        ]
        test_x_export = [
            _persona_features(evs, condition_id=condition_id)
            for _pid, evs in sorted(_group_by_persona(test_rows).items())
        ]
        test_x_assessor = [
            _persona_features_from_predictions(evs, test_preds)
            for _pid, evs in sorted(_group_by_persona(test_rows).items())
        ]
        mixed_schema = inspect_feature_schema(train_x, test_x_assessor)
        export_schema = inspect_feature_schema(train_x, test_x_export)
        frozen_block = frozen["conditions"].get(condition_id, {})
        reconstruction["conditions"][condition_id] = {
            "role": role,
            "family": CONDITION_FAMILIES.get(condition_id, "other"),
            "n_train_events": len(train_rows),
            "n_test_events": len(test_rows),
            "n_test_preds_cached": len(test_preds),
            "z_inventory": _z_key_inventory(exports),
            "mixed_schema": mixed_schema,
            "export_symmetric_schema": export_schema,
            "frozen_tier1_cohort": frozen_block.get("tier1_cohort"),
            "frozen_export_cohort": frozen_block.get("cohort"),
        }
    return reconstruction


def run_no_llm_tracks(ctx: dict[str, Any]) -> dict[str, Any]:
    root: Path = ctx["root"]
    cfg = ctx["cfg"]
    model = ctx["model"]
    seed = ctx["seed"]
    persona_table = ctx["persona_table"]
    persona_split = ctx["persona_split"]
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    results: dict[str, Any] = {}

    for condition_id, _role in resolve_eval_conditions(cfg, root):
        cond_dir = analytics_root / condition_id
        if not cond_dir.is_dir():
            continue
        exports = load_condition_exports(cond_dir)
        if not exports:
            continue
        train_rows = join_eval_rows(
            ctx["labels"], exports, persona_split, split="train"
        )
        test_rows = join_eval_rows(
            ctx["labels"], exports, persona_split, split="test"
        )
        test_preds = _load_predictions(
            test_rows, model=model, condition_id=condition_id, root=root
        )
        frozen_a = evaluate_cohort_from_tier1_predictions(
            train_rows,
            test_rows,
            test_preds,
            persona_table,
            condition_id=condition_id,
            seed=seed,
        )
        mixed_all = evaluate_cohort_mixed_frozen(
            train_rows,
            test_rows,
            test_preds,
            persona_table,
            condition_id=condition_id,
            seed=seed,
            feature_mode="all",
        )
        mixed_shared = evaluate_cohort_mixed_frozen(
            train_rows,
            test_rows,
            test_preds,
            persona_table,
            condition_id=condition_id,
            seed=seed,
            feature_mode="shared",
        )
        export_all = evaluate_cohort_export_symmetric(
            train_rows,
            test_rows,
            persona_table,
            condition_id=condition_id,
            seed=seed,
            feature_mode="all",
        )
        export_no_ec = evaluate_cohort_export_symmetric(
            train_rows,
            test_rows,
            persona_table,
            condition_id=condition_id,
            seed=seed,
            feature_mode="no_event_count",
        )
        export_ec_only = evaluate_cohort_export_symmetric(
            train_rows,
            test_rows,
            persona_table,
            condition_id=condition_id,
            seed=seed,
            feature_mode="event_count_only",
        )
        # Event-count-only is condition-invariant (same event lists); keep one copy.
        results[condition_id] = {
            "family": CONDITION_FAMILIES.get(condition_id, "other"),
            "frozen_reported": ctx["frozen_analytics"]["conditions"][condition_id]
            .get("tier1_cohort", {})
            .get("cohort_segment_macro_f1"),
            "frozen_export_cohort": ctx["frozen_analytics"]["conditions"][condition_id]
            .get("cohort", {})
            .get("cohort_segment_macro_f1"),
            "track_a_repro": frozen_a["cohort_segment_macro_f1"],
            "track_a_mixed_all": mixed_all["cohort_segment_macro_f1"],
            "track_a_shared_features": mixed_shared["cohort_segment_macro_f1"],
            "track_b_export_symmetric": export_all["cohort_segment_macro_f1"],
            "track_b_no_event_count": export_no_ec["cohort_segment_macro_f1"],
            "event_count_only": export_ec_only["cohort_segment_macro_f1"],
            "track_a_schema": mixed_all.get("schema"),
            "track_b_schema": export_all.get("schema"),
            "n_test_preds": len(test_preds),
            "reproduce_frozen_a": abs(
                frozen_a["cohort_segment_macro_f1"]
                - float(
                    ctx["frozen_analytics"]["conditions"][condition_id]["tier1_cohort"][
                        "cohort_segment_macro_f1"
                    ]
                )
            )
            < 1e-12,
        }
        # Verify evaluate_cohort_tasks matches Track B all-features.
        legacy_b = evaluate_cohort_tasks(
            train_rows,
            test_rows,
            persona_table,
            condition_id=condition_id,
            seed=seed,
        )
        results[condition_id]["track_b_matches_legacy_cohort"] = abs(
            legacy_b["cohort_segment_macro_f1"]
            - export_all["cohort_segment_macro_f1"]
        ) < 1e-12
    return results


def estimate_track_c(ctx: dict[str, Any]) -> dict[str, Any]:
    root: Path = ctx["root"]
    cfg = ctx["cfg"]
    model = ctx["model"]
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    audit_cache_root: Path = ctx["audit_cache_root"]
    per_condition = {}
    train_miss_total = 0
    test_hit_frozen = 0
    test_miss_frozen = 0
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        cond_dir = analytics_root / condition_id
        if not cond_dir.is_dir():
            continue
        exports = load_condition_exports(cond_dir)
        if not exports:
            continue
        train_rows = join_eval_rows(
            ctx["labels"], exports, ctx["persona_split"], split="train"
        )
        test_rows = join_eval_rows(
            ctx["labels"], exports, ctx["persona_split"], split="test"
        )
        frozen_stats = cache_stats_for_rows(
            test_rows, root=root, model=model, condition_id=condition_id
        )
        train_frozen = cache_stats_for_rows(
            train_rows, root=root, model=model, condition_id=condition_id
        )
        train_audit = cache_stats_for_rows(
            train_rows, root=audit_cache_root, model=model, condition_id=condition_id
        )
        # Hits in either cache count.
        train_need = [
            row
            for row in train_rows
            if load_cached_prediction(root, model, condition_id, row["event_id"]) is None
            and load_cached_prediction(
                audit_cache_root, model, condition_id, row["event_id"]
            )
            is None
        ]
        per_condition[condition_id] = {
            "n_train_events": len(train_rows),
            "n_test_events": len(test_rows),
            "test_frozen_cache": frozen_stats,
            "train_frozen_cache": train_frozen,
            "train_audit_cache": train_audit,
            "train_inferences_needed": len(train_need),
        }
        train_miss_total += len(train_need)
        test_hit_frozen += frozen_stats["hit"]
        test_miss_frozen += frozen_stats["miss"]
    tcfg = _tier1_cfg(cfg)
    batch = max(int(tcfg["batch_size"]), 1)
    n_batches = (train_miss_total + batch - 1) // batch if train_miss_total else 0
    return {
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "batch_size": batch,
        "train_inferences_needed": train_miss_total,
        "approx_batches": n_batches,
        "test_frozen_hits": test_hit_frozen,
        "test_frozen_misses": test_miss_frozen,
        "note": (
            "Train-side Qwen is not in the frozen analytics cache. "
            "Track C writes only to the audit cache root. "
            "Test predictions are read from the frozen cache and not re-run."
        ),
        "conditions": per_condition,
    }


def _merged_train_preds(
    rows: list[dict],
    *,
    model: str,
    condition_id: str,
    frozen_root: Path,
    audit_root: Path,
) -> dict[str, dict[str, str]]:
    preds: dict[str, dict[str, str]] = {}
    for row in rows:
        cached = load_cached_prediction(
            frozen_root, model, condition_id, row["event_id"]
        ) or load_cached_prediction(audit_root, model, condition_id, row["event_id"])
        if cached is not None:
            preds[row["event_id"]] = cached
    return preds


def run_track_c_inference(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run missing train-side Qwen analytics predictions into the audit cache."""
    root: Path = ctx["root"]
    cfg = ctx["cfg"]
    model = ctx["model"]
    audit_root: Path = ctx["audit_cache_root"]
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    vocab = load_analytics_vocab(root, cfg)
    system_prompt = build_analytics_system_prompt(vocab)
    tcfg = _tier1_cfg(cfg)
    seed = int(tcfg["eval_seeds"][0]) if tcfg["eval_seeds"] else 42
    stats: dict[str, Any] = {"seed": seed, "conditions": {}}
    started = datetime.now(UTC)
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        cond_dir = analytics_root / condition_id
        if not cond_dir.is_dir():
            continue
        exports = load_condition_exports(cond_dir)
        if not exports:
            continue
        train_rows = join_eval_rows(
            ctx["labels"], exports, ctx["persona_split"], split="train"
        )
        pending = [
            row
            for row in train_rows
            if load_cached_prediction(root, model, condition_id, row["event_id"]) is None
            and load_cached_prediction(audit_root, model, condition_id, row["event_id"])
            is None
        ]
        print(
            f"[track-c] {condition_id}: {len(pending)} train inferences needed "
            f"of {len(train_rows)}",
            file=sys.stderr,
        )
        if pending:
            predict_rows(
                pending,
                cfg=cfg,
                root=audit_root,
                model=model,
                seed=seed,
                condition_id=condition_id,
                vocab=vocab,
                system_prompt=system_prompt,
                use_cache=True,
            )
        after = cache_stats_for_rows(
            train_rows, root=audit_root, model=model, condition_id=condition_id
        )
        frozen_hits = cache_stats_for_rows(
            train_rows, root=root, model=model, condition_id=condition_id
        )
        stats["conditions"][condition_id] = {
            "pending_before": len(pending),
            "audit_cache_after": after,
            "frozen_train_hits": frozen_hits["hit"],
        }
    stats["elapsed_s"] = (datetime.now(UTC) - started).total_seconds()
    stats["train_qwen_newly_run"] = True
    return stats


def score_track_c(ctx: dict[str, Any]) -> dict[str, Any]:
    root: Path = ctx["root"]
    cfg = ctx["cfg"]
    model = ctx["model"]
    seed = ctx["seed"]
    audit_root: Path = ctx["audit_cache_root"]
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    out: dict[str, Any] = {}
    incomplete = []
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        cond_dir = analytics_root / condition_id
        if not cond_dir.is_dir():
            continue
        exports = load_condition_exports(cond_dir)
        if not exports:
            continue
        train_rows = join_eval_rows(
            ctx["labels"], exports, ctx["persona_split"], split="train"
        )
        test_rows = join_eval_rows(
            ctx["labels"], exports, ctx["persona_split"], split="test"
        )
        train_preds = _merged_train_preds(
            train_rows,
            model=model,
            condition_id=condition_id,
            frozen_root=root,
            audit_root=audit_root,
        )
        test_preds = _load_predictions(
            test_rows, model=model, condition_id=condition_id, root=root
        )
        coverage = {
            "train_preds": len(train_preds),
            "train_events": len(train_rows),
            "test_preds": len(test_preds),
            "test_events": len(test_rows),
        }
        if len(train_preds) < len(train_rows) or len(test_preds) < len(test_rows):
            incomplete.append({"condition_id": condition_id, **coverage})
            out[condition_id] = {
                "status": "incomplete",
                "coverage": coverage,
            }
            continue
        all_f1 = evaluate_cohort_from_assessor_predictions(
            train_rows,
            test_rows,
            train_preds,
            test_preds,
            ctx["persona_table"],
            seed=seed,
            feature_mode="all",
        )
        no_ec = evaluate_cohort_from_assessor_predictions(
            train_rows,
            test_rows,
            train_preds,
            test_preds,
            ctx["persona_table"],
            seed=seed,
            feature_mode="no_event_count",
        )
        out[condition_id] = {
            "status": "ok",
            "coverage": coverage,
            "track_c_assessor_symmetric": all_f1["cohort_segment_macro_f1"],
            "track_c_no_event_count": no_ec["cohort_segment_macro_f1"],
        }
    return {"conditions": out, "incomplete": incomplete}


def _patch_analytics_cohort(
    frozen: dict[str, Any], scores: dict[str, float]
) -> dict[str, Any]:
    patched = json.loads(json.dumps(frozen))
    for cid, score in scores.items():
        block = patched["conditions"].setdefault(cid, {})
        tier1c = dict(block.get("tier1_cohort") or {})
        tier1c["cohort_segment_macro_f1"] = score
        tier1c["source"] = "ta5_cohort_audit"
        block["tier1_cohort"] = tier1c
    return patched


def run_operative(ctx: dict[str, Any], tracks: dict[str, dict[str, float]]) -> dict[str, Any]:
    obs = ctx["frozen_obs"]
    frozen = ctx["frozen_analytics"]
    r_grid = [r for r in DEFAULT_R_MAX_GRID if r in FOCAL_R_MAX or r in (0.40, 0.45, 0.50, 0.55)]
    # Keep the paper grid subset requested, plus frozen full grid for comparison.
    r_grid = list(FOCAL_R_MAX)
    report: dict[str, Any] = {"r_max_grid": r_grid, "tracks": {}}

    frozen_points = build_condition_points(obs, frozen)
    frozen_winners = {
        r: next(
            (
                row["winner"]
                for row in risk_constrained_selection(
                    frozen_points, purpose="analytics_cohort", r_max_grid=[r]
                )
            ),
            None,
        )
        for r in r_grid
    }
    frozen_regret = build_cross_purpose_regret_matrix(
        obs, frozen, r_max=DEFAULT_R_MAX_FOCAL
    )
    frozen_bundles = task_bundle_feasibility(frozen_points, TASK_BUNDLES)

    for track_name, scores in tracks.items():
        patched = _patch_analytics_cohort(frozen, scores)
        points = build_condition_points(obs, patched)
        winners = {}
        for r in r_grid:
            row = risk_constrained_selection(
                points, purpose="analytics_cohort", r_max_grid=[r]
            )[0]
            winners[str(r)] = {
                "original_winner": frozen_winners[r],
                "new_winner": row["winner"],
                "new_utility": row["utility"],
                "changed": row["winner"] != frozen_winners[r],
            }
        regret = build_cross_purpose_regret_matrix(
            obs, patched, r_max=DEFAULT_R_MAX_FOCAL
        )
        # Compare Ta-5 row/col of regret matrices.
        purposes = regret["purposes"]
        idx = purposes.index("analytics_cohort")
        import numpy as np

        frozen_mat = frozen_regret["regret"]
        new_mat = regret["regret"]
        cohort_row_changed = True
        cohort_col_changed = True
        if frozen_mat.shape == new_mat.shape:
            cohort_row_changed = not np.allclose(
                frozen_mat[idx], new_mat[idx], equal_nan=True
            )
            cohort_col_changed = not np.allclose(
                frozen_mat[:, idx], new_mat[:, idx], equal_nan=True
            )
        bundles = task_bundle_feasibility(points, TASK_BUNDLES)
        report["tracks"][track_name] = {
            "winners": winners,
            "regret_cohort_row_changed": bool(cohort_row_changed),
            "regret_cohort_col_changed": bool(cohort_col_changed),
            "regret_winners": regret["winners"],
            "frozen_regret_winners": frozen_regret["winners"],
            "bundles_unchanged": bundles == frozen_bundles,
            "bundle_note": (
                "TASK_BUNDLES constraints are obs / med-class / composite / linkage / "
                "provenance. None include u_cohort. Dual-purpose bundle is unaffected "
                "by Ta-5 construction."
            ),
        }
    report["frozen_cohort_winners"] = {str(k): v for k, v in frozen_winners.items()}
    report["frozen_regret_winners"] = frozen_regret["winners"]
    report["purpose_labels"] = [lab for _, lab in REGRET_PURPOSES]
    return report


def build_summary_table(no_llm: dict[str, Any], track_c: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = []
    tc_cond = (track_c or {}).get("conditions", {})
    for cid, block in no_llm.items():
        frozen = block["frozen_reported"]
        tc = tc_cond.get(cid, {})
        row = {
            "condition_id": cid,
            "family": block["family"],
            "track_a_frozen": frozen,
            "track_a_repro": block["track_a_repro"],
            "track_b_export_symmetric": block["track_b_export_symmetric"],
            "track_c_assessor_symmetric": tc.get("track_c_assessor_symmetric"),
            "event_count_only": block["event_count_only"],
            "track_b_no_event_count": block["track_b_no_event_count"],
            "track_c_no_event_count": tc.get("track_c_no_event_count"),
            "track_a_shared_features": block["track_a_shared_features"],
        }
        for key in (
            "track_b_export_symmetric",
            "track_c_assessor_symmetric",
            "event_count_only",
            "track_b_no_event_count",
            "track_c_no_event_count",
            "track_a_shared_features",
        ):
            val = row[key]
            row[f"delta_{key}"] = (
                None if val is None or frozen is None else val - frozen
            )
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ta-5 cohort audit (no frozen writes)")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--skip-track-c", action="store_true")
    parser.add_argument(
        "--run-track-c",
        action="store_true",
        help="Run missing train-side Qwen inferences into the audit cache.",
    )
    parser.add_argument(
        "--score-track-c-only",
        action="store_true",
        help="Score Track C from existing audit cache without new inference.",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    proto = paper_protocol(cfg)
    out_dir = ta5_output_dir(cfg, root)
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_cache_root = out_dir / "cache_root"
    audit_cache_root.mkdir(parents=True, exist_ok=True)

    frozen_analytics_path = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2") / "analytics_metrics.json"
    frozen_obs_path = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2") / "metrics.json"
    frozen_analytics = json.loads(frozen_analytics_path.read_text(encoding="utf-8"))
    frozen_obs = json.loads(frozen_obs_path.read_text(encoding="utf-8"))

    tcfg = _tier1_cfg(cfg)
    ctx = {
        "root": root,
        "cfg": cfg,
        "model": tcfg["primary_model"],
        "seed": int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42)),
        "labels": load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl"),
        "persona_split": load_splits(root / cfg["paths"]["ground_truth"] / "splits.json"),
        "persona_table": {
            row["persona_id"]: row
            for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
        },
        "frozen_analytics": frozen_analytics,
        "frozen_obs": frozen_obs,
        "audit_cache_root": audit_cache_root,
    }

    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git": _git_meta(root),
        "config": str(args.config or "configs/cikm_v0.1.yaml"),
        "paper_protocol": proto,
        "seed": ctx["seed"],
        "model": ctx["model"],
        "prompt_version": PROMPT_VERSION,
        "classifier": "RandomForestClassifier(n_estimators=50, class_weight=balanced, random_state=seed)",
        "output_dir": str(out_dir),
        "audit_cache_root": str(audit_cache_root),
        "frozen_analytics": str(frozen_analytics_path),
        "frozen_obs": str(frozen_obs_path),
        "do_not_write": [
            "outputs/pilot_v2/**",
            "data/eval_cache_analytics/**",
            "paper/**/*.tex",
        ],
        "cohort_modes": [
            "mixed_frozen",
            "export_symmetric",
            "assessor_symmetric",
        ],
    }
    _dump(out_dir / "run_manifest.json", manifest)

    print("[audit] reconstructing frozen pipeline", file=sys.stderr)
    reconstruction = reconstruct(ctx)
    _dump(out_dir / "pipeline_reconstruction.json", reconstruction)

    print("[audit] running Tracks A/B + controls (no LLM)", file=sys.stderr)
    no_llm = run_no_llm_tracks(ctx)
    _dump(out_dir / "tracks_ab_controls.json", no_llm)

    print("[audit] estimating Track C", file=sys.stderr)
    estimate = estimate_track_c(ctx)
    _dump(out_dir / "track_c_estimate.json", estimate)

    track_c = None
    inference_stats = None
    if args.run_track_c and not args.skip_track_c:
        print("[audit] running Track C train-side Qwen into audit cache", file=sys.stderr)
        inference_stats = run_track_c_inference(ctx)
        _dump(out_dir / "track_c_inference.json", inference_stats)
    if (args.run_track_c or args.score_track_c_only) and not args.skip_track_c:
        track_c = score_track_c(ctx)
        _dump(out_dir / "track_c_scores.json", track_c)

    table = build_summary_table(no_llm, track_c)
    write_csv(out_dir / "condition_table.csv", table)
    _dump(out_dir / "condition_table.json", table)

    ranks = {
        "track_a_frozen": _rank(
            {cid: b["frozen_reported"] for cid, b in no_llm.items()}
        ),
        "track_b_export_symmetric": _rank(
            {cid: b["track_b_export_symmetric"] for cid, b in no_llm.items()}
        ),
        "event_count_only": _rank(
            {cid: b["event_count_only"] for cid, b in no_llm.items()}
        ),
        "track_b_no_event_count": _rank(
            {cid: b["track_b_no_event_count"] for cid, b in no_llm.items()}
        ),
        "track_a_shared_features": _rank(
            {cid: b["track_a_shared_features"] for cid, b in no_llm.items()}
        ),
    }
    if track_c and not track_c.get("incomplete"):
        ranks["track_c_assessor_symmetric"] = _rank(
            {
                cid: c["track_c_assessor_symmetric"]
                for cid, c in track_c["conditions"].items()
                if c.get("status") == "ok"
            }
        )
        ranks["track_c_no_event_count"] = _rank(
            {
                cid: c["track_c_no_event_count"]
                for cid, c in track_c["conditions"].items()
                if c.get("status") == "ok"
            }
        )
    _dump(out_dir / "ranks.json", ranks)

    track_scores = {
        "track_b": {
            cid: b["track_b_export_symmetric"] for cid, b in no_llm.items()
        },
        "event_count_only": {
            cid: b["event_count_only"] for cid, b in no_llm.items()
        },
        "track_b_no_event_count": {
            cid: b["track_b_no_event_count"] for cid, b in no_llm.items()
        },
        "track_a_shared": {
            cid: b["track_a_shared_features"] for cid, b in no_llm.items()
        },
    }
    if track_c and not track_c.get("incomplete"):
        track_scores["track_c"] = {
            cid: c["track_c_assessor_symmetric"]
            for cid, c in track_c["conditions"].items()
            if c.get("status") == "ok"
        }
        track_scores["track_c_no_event_count"] = {
            cid: c["track_c_no_event_count"]
            for cid, c in track_c["conditions"].items()
            if c.get("status") == "ok"
        }
    print("[audit] operative selection / regret (frozen everything else)", file=sys.stderr)
    operative = run_operative(ctx, track_scores)
    _dump(out_dir / "operative_impact.json", operative)

    manifest["track_c_ran"] = bool(inference_stats)
    manifest["track_c_scored"] = track_c is not None
    manifest["train_qwen_newly_run"] = bool(inference_stats)
    _dump(out_dir / "run_manifest.json", manifest)
    print(f"Wrote {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
