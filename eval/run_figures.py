"""Generate Phase 4 figures and boundary bundle from eval metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.boundary_bundle import write_boundary_bundle  # noqa: E402
from eval.dual_purpose import run_dual_purpose  # noqa: E402
from eval.figures import generate_all_figures, load_metrics, write_config_snapshot  # noqa: E402
from eval.exemplar_figures import generate_exemplar_figures  # noqa: E402
from eval.granular_figures import generate_granular_figures, load_metrics as load_json  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open SBB figure generation (Phase 4)")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--analytics-metrics", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    config_path = args.config or (root / "configs" / "pilot_v0.1.1.yaml")
    cfg = load_config(config_path)

    default_pilot = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    metrics_path = args.metrics or (default_pilot / "metrics.json")
    if not metrics_path.is_file():
        print(f"Missing metrics: {metrics_path}", file=sys.stderr)
        return 1

    metrics = load_metrics(metrics_path)
    pilot_dir = metrics_path.parent
    out_dir = args.output_dir or (pilot_dir / "figures")

    analytics_path = args.analytics_metrics or (pilot_dir / "analytics_metrics.json")
    analytics = load_json(analytics_path) if analytics_path.is_file() else None

    figure_paths = generate_all_figures(
        metrics, out_dir, analytics_metrics=analytics
    )

    if analytics is not None:
        granular = generate_granular_figures(metrics, analytics, out_dir)
        figure_paths.update({k: v for k, v in granular.items()})
        dual = run_dual_purpose(metrics_path, analytics_path, out_dir)
        for key, path in dual.get("figures", {}).items():
            figure_paths[f"dual_{key}"] = Path(path)
        (pilot_dir / "dual_purpose_snapshot.json").write_text(
            json.dumps(dual, indent=2) + "\n", encoding="utf-8"
        )

    obs_root = root / cfg["paths"]["transformed"]
    exemplar_paths = generate_exemplar_figures(obs_root, out_dir)
    figure_paths.update(exemplar_paths)

    bundle_path = write_boundary_bundle(metrics, cfg, pilot_dir / "boundary_bundle_v0.json")
    snapshot_dir = write_config_snapshot(cfg, config_path, pilot_dir)
    write_boundary_bundle(metrics, cfg, snapshot_dir / "boundary_bundle_v0.json")

    manifest = {
        "metrics": str(metrics_path.relative_to(root) if metrics_path.is_relative_to(root) else metrics_path),
        "analytics_metrics": str(analytics_path) if analytics_path.is_file() else None,
        "figures_dir": str(out_dir.relative_to(root) if out_dir.is_relative_to(root) else out_dir),
        "boundary_bundle": str(bundle_path.relative_to(root) if bundle_path.is_relative_to(root) else bundle_path),
        "config_snapshot": str(snapshot_dir.relative_to(root) if snapshot_dir.is_relative_to(root) else snapshot_dir),
        "figure_files": {k: str(v.name) for k, v in figure_paths.items()},
    }
    (pilot_dir / "figures_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote figures to {out_dir}", file=sys.stderr)
    print(f"Wrote {bundle_path}", file=sys.stderr)
    print(f"Wrote config snapshot to {snapshot_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
