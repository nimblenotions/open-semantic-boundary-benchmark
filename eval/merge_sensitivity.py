"""Merge Tier-1 sensitivity from eval cache into pilot_v2 metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.sensitivity_merge import write_sensitivity_artifacts  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge llama/gemma Tier-1 sensitivity from eval cache into metrics"
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--obs-metrics", type=Path, default=None)
    parser.add_argument("--analytics-metrics", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    pilot_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    obs_path = args.obs_metrics or (pilot_dir / "metrics.json")
    analytics_path = args.analytics_metrics or (pilot_dir / "analytics_metrics.json")

    for path in (obs_path, analytics_path):
        if not path.is_file():
            print(f"Missing metrics: {path}", file=sys.stderr)
            return 1

    paths = write_sensitivity_artifacts(obs_path, analytics_path, cfg, root, pilot_dir)
    print(f"Merged sensitivity into {paths['obs_metrics']}", file=sys.stderr)
    print(f"Merged sensitivity into {paths['analytics_metrics']}", file=sys.stderr)
    print(f"Wrote {paths['report_md']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
