"""Run embedding retention diagnostic (Option D appendix metric)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.embeddings import DEFAULT_MODEL, MockEmbedder, SentenceTransformerEmbedder  # noqa: E402
from eval.figures import load_metrics, plot_retention_vs_utility  # noqa: E402
from eval.retention import run_retention  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open SBB-Obs retention diagnostic")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock embedder")
    parser.add_argument("--sample", type=int, default=None, help="Limit to N event IDs (dev)")
    parser.add_argument("--figure", action="store_true", help="Write retention vs F1 scatter")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = repo_root()

    metrics_path = args.metrics
    metrics = None
    if metrics_path and metrics_path.is_file():
        metrics = load_metrics(metrics_path)
    else:
        default_pilot = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v1")
        default_metrics = default_pilot / "metrics.json"
        if default_metrics.is_file():
            metrics = load_metrics(default_metrics)

    if args.mock:
        embedder = MockEmbedder()
        model_label = "mock"
    else:
        embedder = SentenceTransformerEmbedder(args.model)
        model_label = args.model

    event_ids = None
    if args.sample is not None:
        raw_path = root / cfg["paths"]["raw"] / "events.jsonl"
        from transform.io import load_jsonl

        all_ids = [row["event_id"] for row in load_jsonl(raw_path)]
        event_ids = sorted(all_ids)[: args.sample]

    result = run_retention(cfg, root, embedder, event_ids=event_ids, metrics=metrics)
    result["embedding_model"] = model_label

    out_dir = root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output or (out_dir / "retention.json")
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)

    for cid, row in sorted(result["conditions"].items()):
        print(
            f"  {cid}: mean={row['cosine_mean']:.4f} median={row['cosine_median']:.4f} "
            f"n={row['n_events']}",
            file=sys.stderr,
        )

    if args.figure and metrics:
        fig_dir = out_dir / "figures"
        paths = plot_retention_vs_utility(result, metrics, fig_dir)
        print(f"Wrote {paths['png']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
