"""Consolidate LLM per-event cache sprawl into cache.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sbb.config import load_config, repo_root
from transform.lattice import LLM_CONDITIONS
from transform.llm_cache_io import consolidate_llm_cache, llm_cache_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge data/llm_transform_cache/*/evt_*.json into cache.jsonl"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="LLM appendix conditions (default: all LLM arms)",
    )
    parser.add_argument(
        "--keep-per-event",
        action="store_true",
        help="Keep evt_*.json files after consolidating",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = repo_root()
    cache_root = llm_cache_root(root, cfg)
    selected = args.conditions or list(LLM_CONDITIONS)
    unknown = [c for c in selected if c not in LLM_CONDITIONS]
    if unknown:
        print(f"Unknown LLM conditions: {unknown}", file=sys.stderr)
        return 1

    stats: dict[str, object] = {"conditions": {}}
    for condition_id in selected:
        cond_dir = cache_root / condition_id
        if not cond_dir.is_dir():
            print(f"skip missing cache dir: {cond_dir}", file=sys.stderr)
            continue
        stats["conditions"][condition_id] = consolidate_llm_cache(
            cond_dir,
            remove_per_event=not args.keep_per_event,
        )

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
