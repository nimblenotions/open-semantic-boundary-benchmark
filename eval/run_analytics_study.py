"""Run analytics-purpose Tier-0/1 study (RQ-F1 appendix)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.analytics_cohort import evaluate_cohort_tasks  # noqa: E402
from eval.analytics_task import (  # noqa: E402
    composite_utility,
    evaluate_analytics_tier0,
    evaluate_analytics_transfer,
)
from eval.io import join_eval_rows, load_labels, load_splits  # noqa: E402
from eval.provenance_score import evaluate_provenance  # noqa: E402
from eval.study import resolve_eval_conditions  # noqa: E402
from eval.tier1_analytics_consumer import (  # noqa: E402
    _tier1_cfg,
    cache_stats_for_rows,
    evaluate_tier1_analytics,
)
from sbb.config import load_config, repo_root  # noqa: E402
from transform.io import load_condition_exports, load_jsonl  # noqa: E402


def run_analytics_study(
    cfg: dict[str, Any],
    root: Path,
    *,
    tier: str = "0",
    max_tier1_events: int | None = None,
) -> dict[str, Any]:
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    eval_conditions = [
        (cid, role)
        for cid, role in resolve_eval_conditions(cfg, root)
        if (analytics_root / cid).is_dir()
    ]
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    seed = int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42))

    raw_exports = load_condition_exports(analytics_root / "raw")
    raw_train_rows = (
        join_eval_rows(labels, raw_exports, persona_split, split="train")
        if raw_exports
        else []
    )

    condition_metrics: dict[str, dict[str, Any]] = {}
    tier1_cfg_logged = False
    for condition_id, role in eval_conditions:
        exports = load_condition_exports(analytics_root / condition_id)
        if not exports:
            continue
        train_rows = join_eval_rows(labels, exports, persona_split, split="train")
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")

        metrics: dict[str, Any] = {
            "role": role,
            "purpose_id": "analytics",
            "consumer_id": "analytics_vendor",
            "provenance": evaluate_provenance(exports),
        }
        if tier in ("0", "all"):
            utility = evaluate_analytics_tier0(train_rows, test_rows, seed=seed)
            metrics["tier0"] = {
                "utility": utility,
                "composite_utility": composite_utility(utility),
            }
            metrics["transfer"] = evaluate_analytics_transfer(
                raw_train_rows,
                test_rows,
                condition_id,
                seed=seed,
            )
            metrics["cohort"] = evaluate_cohort_tasks(
                train_rows,
                test_rows,
                persona_table,
                condition_id=condition_id,
                seed=seed,
            )
        if tier in ("1", "1-linkage", "all"):
            tcfg = _tier1_cfg(cfg)
            if not tier1_cfg_logged:
                print(
                    f"[tier1-analytics] batch_size={tcfg['batch_size']} "
                    f"batch_by_persona=True primary_model={tcfg['primary_model']}",
                    file=sys.stderr,
                )
                tier1_cfg_logged = True
            stats = cache_stats_for_rows(
                test_rows[:max_tier1_events] if max_tier1_events else test_rows,
                model=tcfg["primary_model"],
                condition_id=condition_id,
                root=root,
            )
            print(
                f"[tier1-analytics] {condition_id}: cache_hit={stats['hit']} "
                f"cache_miss={stats['miss']} total={stats['total']}",
                file=sys.stderr,
            )
            tier1_result = evaluate_tier1_analytics(
                train_rows,
                test_rows,
                cfg,
                root=root,
                max_events=max_tier1_events,
            )
            metrics["tier1"] = tier1_result
            print(
                f"[tier1-analytics] {condition_id}: done "
                f"med={tier1_result.get('medication_class_macro_f1')}",
                file=sys.stderr,
            )

        condition_metrics[condition_id] = metrics

    result: dict[str, Any] = {
        "study": cfg.get("analytics_study", {}).get("name", "sbb-analytics-v0.1"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "tier": tier,
        "purpose_id": "analytics",
        "consumer_id": "analytics_vendor",
        "policy_id": "analytics_policy_v1",
        "primary_metric": "medication_class_macro_f1",
        "composite_metric": "composite_utility",
        "conditions": condition_metrics,
        "notes": {
            "eval_split": "test",
            "train_split": "train",
            "tasks": ["ta_med_class", "ta_side_effect", "ta_adherence", "ta_cohort_segment"],
            "transform_root": str(cfg["paths"]["transformed_analytics"]),
            "tier1_consumer": "active"
            if tier in ("1", "1-linkage", "all")
            else "tier0_only",
        },
    }

    return result


def merge_analytics_metrics(
    existing: dict[str, Any] | None, new: dict[str, Any]
) -> dict[str, Any]:
    """Merge per-condition blocks so tier0 + tier1 compose into one analytics_metrics.json."""
    if not existing:
        return new

    merged = dict(new)
    existing_conds = existing.get("conditions", {})
    new_conds = merged.setdefault("conditions", {})
    all_ids = set(existing_conds) | set(new_conds)
    for cid in all_ids:
        new_conds[cid] = {**existing_conds.get(cid, {}), **new_conds.get(cid, {})}

    if existing.get("dual_purpose") and not merged.get("dual_purpose"):
        merged["dual_purpose"] = existing["dual_purpose"]
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analytics-purpose evaluation (T_a)")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--tier", choices=["0", "1", "1-linkage", "all"], default="0"
    )
    parser.add_argument(
        "--max-tier1-events",
        type=int,
        default=None,
        help="Limit Tier-1 eval to first N test events (smoke runs)",
    )
    parser.add_argument(
        "--obs-metrics",
        type=Path,
        default=None,
        help="Observability metrics.json for dual-purpose Pareto (Opt 7)",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Do not merge with existing analytics_metrics.json in pilot_dir",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = repo_root()
    out_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output or (out_dir / "analytics_metrics.json")

    obs_path = args.obs_metrics or (out_dir / "metrics.json")
    existing: dict | None = None
    if not args.no_merge and out_path.is_file() and args.tier in ("0", "1"):
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    result = run_analytics_study(
        cfg,
        root,
        tier=args.tier,
        max_tier1_events=args.max_tier1_events,
    )
    if existing:
        result = merge_analytics_metrics(existing, result)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if obs_path.is_file():
        from eval.dual_purpose import run_dual_purpose

        out_fig = out_dir / "figures"
        dual = run_dual_purpose(obs_path, out_path, out_fig)
        result["dual_purpose"] = dual
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)

    for cid, m in result.get("conditions", {}).items():
        if "tier0" in m:
            u = m["tier0"]["utility"]
            print(
                f"  {cid} [tier0]: med={u.get('medication_class_macro_f1', 0):.3f} "
                f"se={u.get('side_effect_signal_macro_f1', 0):.3f} "
                f"adh={u.get('adherence_signal_macro_f1', 0):.3f}",
                file=sys.stderr,
            )
        if "tier1" in m:
            t1 = m["tier1"]
            print(
                f"  {cid} [tier1]: med={t1.get('medication_class_macro_f1', 0):.3f} "
                f"se={t1.get('side_effect_signal_macro_f1', 0):.3f} "
                f"adh={t1.get('adherence_signal_macro_f1', 0):.3f}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
