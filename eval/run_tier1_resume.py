"""Resume Tier-1 eval per condition; merge into existing metrics.json."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.io import (  # noqa: E402
    join_eval_rows,
    load_condition_exports,
    load_labels,
    load_splits,
)
from eval.study import _evaluate_hypotheses, resolve_eval_conditions  # noqa: E402
from eval.tier1_consumer import (  # noqa: E402
    _tier1_cfg,
    cache_stats_for_rows,
    evaluate_tier1,
)
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resume Tier-1 Ollama eval")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="Subset of condition ids (default: all frozen lattice)",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    cfg["eval"]["tier1"]["sensitivity_models"] = []
    cfg["eval"]["tier1"]["eval_seeds"] = [42]

    out_path = args.output or (
        root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2") / "metrics.json"
    )
    if out_path.is_file():
        metrics = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        metrics = {
            "study": cfg.get("study", {}).get("name", "sbb-obs"),
            "primary_metric": cfg.get("metrics", {}).get("primary", "failure_mode_macro_f1"),
            "conditions": {},
            "notes": {},
        }

    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    eval_conditions = resolve_eval_conditions(cfg, root)
    tcfg = _tier1_cfg(cfg)

    target = set(args.conditions) if args.conditions else None
    t0 = time.time()

    print(
        f"[tier1-resume] primary_model={tcfg['primary_model']} "
        f"batch_size={tcfg['batch_size']}",
        file=sys.stderr,
    )

    for condition_id, role in eval_conditions:
        if target and condition_id not in target:
            continue
        exports = load_condition_exports(
            root / cfg["paths"]["transformed"] / condition_id
        )
        if not exports:
            continue
        train_rows = join_eval_rows(labels, exports, persona_split, split="train")
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        stats = cache_stats_for_rows(
            test_rows,
            model=tcfg["primary_model"],
            condition_id=condition_id,
            root=root,
        )
        print(
            f"[tier1-resume] {condition_id}: cache_hit={stats['hit']} "
            f"cache_miss={stats['miss']} total={stats['total']}",
            file=sys.stderr,
        )

        cond0 = time.time()
        tier1 = evaluate_tier1(
            train_rows,
            test_rows,
            cfg,
            root=root,
        )
        elapsed = time.time() - cond0
        print(
            f"[tier1-resume] {condition_id}: done in {elapsed:.1f}s "
            f"f1={tier1.get('failure_mode_macro_f1')} "
            f"parsed={tier1.get('n_parsed')}/{tier1.get('n_test')}",
            file=sys.stderr,
        )

        cond_metrics = metrics["conditions"].setdefault(condition_id, {"role": role})
        cond_metrics["tier1"] = tier1

        metrics["generated_at_utc"] = datetime.now(UTC).isoformat()
        metrics["tier"] = "all"
        metrics.setdefault("notes", {})
        metrics["notes"]["tier1_consumer"] = "active"
        metrics["notes"]["tier1_runtime_s"] = round(time.time() - t0, 1)
        metrics["notes"]["tier1_primary_only"] = True

        primary = {
            cid: m
            for cid, m in metrics["conditions"].items()
            if m.get("role") in ("primary", "frozen")
            and ("tier0" in m or "trial4_adversary" in m or "tier1" in m)
        }
        if primary:
            metrics["hypotheses"] = _evaluate_hypotheses(primary)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        print(f"[tier1-resume] wrote {out_path}", file=sys.stderr)

    total = time.time() - t0
    print(f"[tier1-resume] finished in {total:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
