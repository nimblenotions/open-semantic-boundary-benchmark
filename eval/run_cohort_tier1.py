"""Compute Tier-1-derived cohort metrics from analytics eval cache; merge into analytics_metrics.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.analytics_cohort import evaluate_cohort_from_tier1_predictions  # noqa: E402
from eval.io import join_eval_rows, load_labels, load_splits  # noqa: E402
from eval.study import resolve_eval_conditions  # noqa: E402
from eval.tier1_analytics_consumer import (  # noqa: E402
    _tier1_cfg,
    load_cached_prediction,
)
from sbb.config import load_config, repo_root  # noqa: E402
from transform.io import load_condition_exports, load_jsonl  # noqa: E402


def _load_predictions(
    rows: list[dict], *, model: str, condition_id: str, root: Path
) -> dict[str, dict[str, str]]:
    preds: dict[str, dict[str, str]] = {}
    for row in rows:
        cached = load_cached_prediction(root, model, condition_id, row["event_id"])
        if cached is not None:
            preds[row["event_id"]] = cached
    return preds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cohort Tier-1 from analytics Tier-1 cache")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    out_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    out_path = args.output or (out_dir / "analytics_metrics.json")
    if not out_path.is_file():
        print(f"Missing {out_path}", file=sys.stderr)
        return 1

    metrics = json.loads(out_path.read_text(encoding="utf-8"))
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    tcfg = _tier1_cfg(cfg)
    model = tcfg["primary_model"]
    seed = int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42))

    for condition_id, role in resolve_eval_conditions(cfg, root):
        if not (analytics_root / condition_id).is_dir():
            continue
        exports = load_condition_exports(analytics_root / condition_id)
        if not exports:
            continue
        train_rows = join_eval_rows(labels, exports, persona_split, split="train")
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        test_preds = _load_predictions(
            test_rows, model=model, condition_id=condition_id, root=root
        )
        if not test_preds:
            print(f"[cohort-tier1] {condition_id}: no cached predictions", file=sys.stderr)
            continue
        cohort = evaluate_cohort_from_tier1_predictions(
            train_rows,
            test_rows,
            test_preds,
            persona_table,
            condition_id=condition_id,
            seed=seed,
        )
        block = metrics["conditions"].setdefault(condition_id, {"role": role})
        block["tier1_cohort"] = cohort
        print(
            f"[cohort-tier1] {condition_id}: segment_f1={cohort['cohort_segment_macro_f1']:.3f} "
            f"({cohort['n_test_personas']} test personas, {len(test_preds)} test preds)",
            file=sys.stderr,
        )

    metrics["generated_at_utc"] = datetime.now(UTC).isoformat()
    metrics.setdefault("notes", {})["tier1_cohort"] = "derived_from_tier1_event_predictions"
    out_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
