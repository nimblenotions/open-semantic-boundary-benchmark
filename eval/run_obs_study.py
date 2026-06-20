"""Run H1–H4 observability study (Phase 3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.study import merge_obs_metrics, run_study  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402

TIER_CHOICES = ("0", "1", "linkage", "1-linkage", "all")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open SBB-Obs evaluation")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--tier", choices=TIER_CHOICES, default="0")
    parser.add_argument(
        "--max-tier1-events",
        type=int,
        default=None,
        help="Limit Tier-1 eval to first N test events (smoke runs)",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Do not merge with existing metrics.json in pilot_dir",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = repo_root()
    out_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output or (out_dir / "metrics.json")

    existing: dict | None = None
    if not args.no_merge and out_path.is_file() and args.tier in ("0", "1", "linkage"):
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    result = run_study(
        cfg,
        root,
        tier=args.tier,
        max_tier1_events=args.max_tier1_events,
    )
    if existing is not None:
        result = merge_obs_metrics(existing, result)
        if args.tier in ("linkage", "1-linkage") or (
            args.tier == "1" and existing.get("conditions")
        ):
            from eval.study import _evaluate_hypotheses

            primary = {
                cid: m
                for cid, m in result.get("conditions", {}).items()
                if m.get("role") in ("primary", "frozen")
            }
            if primary:
                result["hypotheses"] = _evaluate_hypotheses(primary)

    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_path}", file=sys.stderr)
    if result.get("hypotheses"):
        for hid, h in result["hypotheses"].items():
            if hid.startswith("H"):
                mark = "yes" if h["supported"] else "no"
                print(f"  {hid}: {mark} — {h['detail']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
