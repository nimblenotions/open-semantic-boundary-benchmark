"""Materialize LLM cache into observability and analytics events.jsonl bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sbb.config import load_config, repo_root
from transform.lattice import LLM_CONDITIONS
from transform.llm_materialize import materialize_llm_conditions


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write data/transformed/{llm}/events.jsonl and "
            "data/transformed_analytics/{llm}/events.jsonl from LLM cache"
        )
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="LLM appendix conditions (default: eval.appendix_conditions in config)",
    )
    parser.add_argument(
        "--consolidate-cache",
        action="store_true",
        help="Merge evt_*.json sprawl to cache.jsonl before materializing",
    )
    parser.add_argument(
        "--require-full-corpus",
        action="store_true",
        help="Fail if any raw event lacks a cache entry",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = repo_root()
    conditions = args.conditions
    if conditions:
        unknown = [c for c in conditions if c not in LLM_CONDITIONS]
        if unknown:
            print(f"Unknown LLM conditions: {unknown}", file=sys.stderr)
            return 1

    stats = materialize_llm_conditions(
        cfg,
        root,
        conditions=conditions,
        consolidate_cache=args.consolidate_cache,
        require_full_corpus=args.require_full_corpus,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
