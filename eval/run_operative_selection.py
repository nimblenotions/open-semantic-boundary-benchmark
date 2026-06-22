"""Run operative selection analyses on pilot_v2 metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.operative_figures import generate_operative_figures  # noqa: E402
from eval.operative_selection import run_operative_selection  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operative selection (risk, dominance, bundles)")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--analytics-metrics", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    config_path = args.config or (root / "configs" / "pilot_v0.1.1.yaml")
    cfg = load_config(config_path)

    pilot_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    metrics_path = args.metrics or (pilot_dir / "metrics.json")
    analytics_path = args.analytics_metrics or (pilot_dir / "analytics_metrics.json")

    if not metrics_path.is_file():
        print(f"Missing metrics: {metrics_path}", file=sys.stderr)
        return 1
    if not analytics_path.is_file():
        print(f"Missing analytics metrics: {analytics_path}", file=sys.stderr)
        return 1

    obs_metrics = _load_json(metrics_path)
    analytics_metrics = _load_json(analytics_path)
    out_dir = args.output_dir or (pilot_dir / "operative_selection")

    result = run_operative_selection(obs_metrics, analytics_metrics, cfg, out_dir)
    figure_paths = generate_operative_figures(obs_metrics, analytics_metrics, out_dir)
    result["figures"] = {k: str(v) for k, v in figure_paths.items()}
    print(json.dumps(result, indent=2))
    print(f"Wrote operative selection to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
