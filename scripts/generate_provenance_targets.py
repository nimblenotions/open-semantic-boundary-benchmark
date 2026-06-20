#!/usr/bin/env python3
"""Generate provenance_targets.jsonl and exemplars.json for Sikkim reviewers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate.provenance_targets import write_provenance_targets  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build data/ground_truth/provenance_targets.jsonl + exemplars.json"
    )
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = repo_root()
    stats = write_provenance_targets(cfg, root)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
