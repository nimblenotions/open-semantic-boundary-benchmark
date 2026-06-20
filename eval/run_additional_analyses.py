"""Run post-hoc pilot_v2 analyses from existing metrics (no new inference)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.additional_analyses import run_all_analyses  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Additional pilot_v2 post-hoc analyses")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    outputs = run_all_analyses(root, cfg)
    print(f"Wrote {len(outputs.figures)} figures", file=sys.stderr)
    print(f"Wrote {len(outputs.tables)} tables", file=sys.stderr)
    print(f"Summary: {outputs.json_summary}", file=sys.stderr)
    print(f"Doc: {root / 'docs' / 'additional-analyses-post-experiments.md'} (narrative)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
