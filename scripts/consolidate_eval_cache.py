"""Consolidate Tier-1 eval per-event cache sprawl into predictions.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.eval_cache_io import consolidate_all_eval_caches
from sbb.config import repo_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Merge data/eval_cache and data/eval_cache_analytics "
            "evt_*.json into predictions.jsonl"
        )
    )
    parser.add_argument(
        "--analytics-only",
        action="store_true",
        help="Only consolidate data/eval_cache_analytics/",
    )
    parser.add_argument(
        "--obs-only",
        action="store_true",
        help="Only consolidate data/eval_cache/",
    )
    parser.add_argument(
        "--keep-per-event",
        action="store_true",
        help="Keep evt_*.json files after consolidating",
    )
    args = parser.parse_args()

    if args.analytics_only and args.obs_only:
        print("Cannot use --analytics-only and --obs-only together", file=sys.stderr)
        return 1

    root = repo_root()
    remove = not args.keep_per_event
    stats: dict[str, object] = {}

    if not args.analytics_only:
        stats["obs"] = consolidate_all_eval_caches(
            root, analytics=False, remove_per_event=remove
        )
    if not args.obs_only:
        stats["analytics"] = consolidate_all_eval_caches(
            root, analytics=True, remove_per_event=remove
        )

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
