"""Compute bootstrap 95% CIs for headline pilot_v2 metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.bootstrap_cis import run_bootstrap_cis  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap CIs for pilot_v2 headline metrics")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    outputs = run_bootstrap_cis(
        root, cfg, n_bootstrap=args.n_bootstrap, seed=args.seed
    )
    print(f"Wrote {outputs.json_path}", file=sys.stderr)
    print(f"Wrote {outputs.tex_path}", file=sys.stderr)
    print(f"Wrote {outputs.figure_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
