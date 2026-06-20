#!/usr/bin/env python3
"""Run up to N parallel Tier-1 Ollama jobs on disjoint cache targets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.ollama_pool import plan_tier1_jobs, run_jobs_parallel  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parallel Tier-1 Ollama eval (disjoint model×condition×purpose)"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--purpose",
        choices=["obs", "analytics", "both"],
        default="obs",
        help="Eval purpose (default: obs)",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Models to run (default: primary + sensitivity from config)",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="Lattice subset (default: all primary conditions with exports)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Max concurrent jobs (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned jobs without calling Ollama",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = repo_root()
    jobs = plan_tier1_jobs(
        cfg,
        root,
        purpose=args.purpose,
        models=args.models,
        conditions=args.conditions,
    )
    print(json.dumps({"job_count": len(jobs), "jobs": [j.cache_key() for j in jobs]}, indent=2))

    if args.dry_run:
        return 0

    results = run_jobs_parallel(jobs, cfg, root, max_workers=args.max_workers)
    print(json.dumps({"results": results}, indent=2))
    failed = [r for r in results if r.get("status") != "ok"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
