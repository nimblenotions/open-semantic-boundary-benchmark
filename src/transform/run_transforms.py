"""Apply export lattice transforms (Phase 2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sbb.config import load_config, repo_root
from transform.lattice import run_lattice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transform raw → lattice exports")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=None,
        help="Subset of lattice conditions to regenerate (default: all in config)",
    )
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    root = repo_root()
    stats = run_lattice(cfg, root, conditions=args.conditions)
    print(json.dumps(stats, indent=2))
    if stats.get("verify_failures", 0) > 0:
        print(
            f"warning: {stats['verify_failures']} exports failed verify",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
