"""Bootstrap 95% CIs for headline pilot_v2 metrics (no new inference)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import f1_score

from eval.adversary_trial4 import (
    DEFAULT_SIMILARITY_THRESHOLD,
    _attribute_inference,
    _export_texts,
    _longitudinal_linkage_auc,
    _persona_inference,
    combined_linkage_score,
    resolve_embedder,
)
from eval.analytics_task import ground_truth_medication_class
from eval.eval_cache_io import load_eval_cache_entries
from eval.io import join_eval_rows, load_condition_exports, load_labels, load_raw_events, load_splits
from eval.study import resolve_eval_conditions
from transform.io import load_jsonl


@dataclass
class BootstrapOutputs:
    json_path: Path
    tex_path: Path
    figure_path: Path


def _percentile_ci(samples: np.ndarray, alpha: float = 0.05) -> tuple[float, float, float]:
    lo, hi = np.percentile(samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(np.mean(samples)), float(lo), float(hi)


def _load_obs_predictions(
    root: Path, model: str, condition_id: str
) -> dict[str, dict[str, str]]:
    from eval.eval_cache_io import eval_condition_cache_dir

    cache_dir = eval_condition_cache_dir(root, model, condition_id, analytics=False)
    entries = load_eval_cache_entries(cache_dir)
    out: dict[str, dict[str, str]] = {}
    for event_id, row in entries.items():
        pred = row.get("prediction") or {}
        if pred.get("failure_mode") and pred.get("error_stage"):
            out[event_id] = {
                "failure_mode": pred["failure_mode"],
                "error_stage": pred["error_stage"],
            }
    return out


def _load_analytics_predictions(
    root: Path, model: str, condition_id: str
) -> dict[str, dict[str, str]]:
    from eval.eval_cache_io import eval_condition_cache_dir

    cache_dir = eval_condition_cache_dir(root, model, condition_id, analytics=True)
    entries = load_eval_cache_entries(cache_dir)
    out: dict[str, dict[str, str]] = {}
    for event_id, row in entries.items():
        pred = row.get("prediction") or {}
        if pred.get("medication_class"):
            out[event_id] = {"medication_class": pred["medication_class"]}
    return out


def _event_bootstrap_macro_f1(
    y_true: list[str],
    y_pred: list[str],
    *,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> np.ndarray:
    n = len(y_true)
    if n == 0:
        return np.zeros(n_bootstrap)
    idx = np.arange(n)
    samples = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        draw = rng.choice(idx, size=n, replace=True)
        yt = [y_true[i] for i in draw]
        yp = [y_pred[i] for i in draw]
        samples[b] = f1_score(yt, yp, average="macro", zero_division=0)
    return samples


def _linkage_score_on_test_rows(
    train_rows: list[dict[str, Any]],
    boot_test_rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    resolved: Any,
    embeddings_train: np.ndarray,
    seed: int,
) -> float:
    """Trial4 combined linkage on a test subset (train + embedder cached)."""
    if not boot_test_rows:
        return 0.0
    embeddings_test = resolved.embed(_export_texts(boot_test_rows))
    persona_metrics = _persona_inference(
        train_rows,
        boot_test_rows,
        embeddings_train,
        embeddings_test,
        similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
    )
    attr_metrics = _attribute_inference(
        train_rows,
        boot_test_rows,
        embeddings_train,
        embeddings_test,
        persona_table,
        seed=seed,
    )
    linkage_metrics = _longitudinal_linkage_auc(boot_test_rows, embeddings_test, seed=seed)
    merged = {
        **{k: float(v) for k, v in persona_metrics.items() if isinstance(v, (int, float))},
        **{k: float(v) for k, v in attr_metrics.items() if isinstance(v, (int, float))},
        **{k: float(v) for k, v in linkage_metrics.items() if isinstance(v, (int, float))},
    }
    return combined_linkage_score(merged)


def _persona_block_bootstrap_linkage(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    seed: int,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> np.ndarray:
    by_persona: dict[str, list[dict[str, Any]]] = {}
    for row in test_rows:
        by_persona.setdefault(row["persona_id"], []).append(row)
    persona_ids = sorted(by_persona)
    if not persona_ids:
        return np.zeros(n_bootstrap)

    all_texts = _export_texts(train_rows) + _export_texts(test_rows)
    resolved = resolve_embedder(None, fit_texts=all_texts)
    embeddings_train = resolved.embed(_export_texts(train_rows))

    samples = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        drawn = rng.choice(persona_ids, size=len(persona_ids), replace=True)
        boot_rows: list[dict[str, Any]] = []
        for pid in drawn:
            boot_rows.extend(by_persona[pid])
        samples[b] = _linkage_score_on_test_rows(
            train_rows,
            boot_rows,
            raw_by_id,
            persona_table,
            resolved=resolved,
            embeddings_train=embeddings_train,
            seed=seed,
        )
    return samples


def run_bootstrap_cis(
    root: Path,
    cfg: dict[str, Any],
    *,
    n_bootstrap: int = 2000,
    seed: int = 42,
    model: str = "qwen3:8b",
) -> BootstrapOutputs:
    """Bootstrap headline Tier-1 F1 (event-level) and Trial4 linkage (persona-block)."""
    pilot_dir = cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    out_dir = root / pilot_dir / "bootstrap_cis"
    out_dir.mkdir(parents=True, exist_ok=True)

    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    raw_by_id = load_raw_events(root / cfg["paths"]["raw"] / "events.jsonl")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    eval_seed = int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42))
    rng = np.random.default_rng(seed)

    conditions = [cid for cid, _ in resolve_eval_conditions(cfg, root)]
    rows_out: list[dict[str, Any]] = []

    for condition_id in conditions:
        obs_exports = load_condition_exports(
            root / cfg["paths"]["transformed"] / condition_id
        )
        analytics_exports = load_condition_exports(
            root / cfg["paths"]["transformed_analytics"] / condition_id
        )
        if not obs_exports:
            continue

        train_rows = join_eval_rows(labels, obs_exports, persona_split, split="train")
        test_rows = join_eval_rows(labels, obs_exports, persona_split, split="test")
        obs_preds = _load_obs_predictions(root, model, condition_id)
        scored = [r for r in test_rows if r["event_id"] in obs_preds]
        y_fail = [r["label"]["failure_mode"] for r in scored]
        pred_fail = [obs_preds[r["event_id"]]["failure_mode"] for r in scored]
        obs_samples = _event_bootstrap_macro_f1(
            y_fail, pred_fail, n_bootstrap=n_bootstrap, rng=rng
        )
        obs_mean, obs_lo, obs_hi = _percentile_ci(obs_samples)

        med_mean, med_lo, med_hi = (0.0, 0.0, 0.0)
        if analytics_exports:
            analytics_test = join_eval_rows(
                labels, analytics_exports, persona_split, split="test"
            )
            med_preds = _load_analytics_predictions(root, model, condition_id)
            med_scored = [r for r in analytics_test if r["event_id"] in med_preds]
            y_med = [ground_truth_medication_class(r["label"]) for r in med_scored]
            pred_med = [med_preds[r["event_id"]]["medication_class"] for r in med_scored]
            med_samples = _event_bootstrap_macro_f1(
                y_med, pred_med, n_bootstrap=n_bootstrap, rng=rng
            )
            med_mean, med_lo, med_hi = _percentile_ci(med_samples)

        link_n = min(n_bootstrap, 100)
        print(f"bootstrap: {condition_id} (linkage draws={link_n})", flush=True)
        link_samples = _persona_block_bootstrap_linkage(
            train_rows,
            test_rows,
            raw_by_id,
            persona_table,
            seed=eval_seed,
            n_bootstrap=link_n,
            rng=rng,
        )
        link_mean, link_lo, link_hi = _percentile_ci(link_samples)

        rows_out.append(
            {
                "condition_id": condition_id,
                "n_test_events": len(scored),
                "n_test_personas": len({r["persona_id"] for r in test_rows}),
                "obs_failure_mode_macro_f1": {
                    "point": obs_mean,
                    "ci95_lo": obs_lo,
                    "ci95_hi": obs_hi,
                    "bootstrap": "event_resample_n630",
                },
                "analytics_med_class_macro_f1": {
                    "point": med_mean,
                    "ci95_lo": med_lo,
                    "ci95_hi": med_hi,
                    "bootstrap": "event_resample_n630",
                },
                "combined_linkage_score": {
                    "point": link_mean,
                    "ci95_lo": link_lo,
                    "ci95_hi": link_hi,
                    "bootstrap": "persona_block_resample_n20",
                },
            }
        )

    summary = {
        "study": cfg.get("study", {}).get("name", "pilot_v2"),
        "model": model,
        "n_bootstrap_utility": n_bootstrap,
        "n_bootstrap_linkage": min(n_bootstrap, 100),
        "seed": seed,
        "conditions": rows_out,
    }
    json_path = out_dir / "bootstrap_cis.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    tex_path = out_dir / "bootstrap_cis.tex"
    tex_path.write_text(_render_latex_table(rows_out), encoding="utf-8")

    figure_path = out_dir / "bootstrap_cis.pdf"
    _plot_figure(rows_out, figure_path)

    return BootstrapOutputs(json_path=json_path, tex_path=tex_path, figure_path=figure_path)


def _render_latex_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "% Auto-generated by eval/run_bootstrap_cis.py — do not edit by hand",
        "\\begin{table}[t]",
        "\\caption{Bootstrap 95\\% CIs on the held-out test split (primary consumer qwen3:8b). "
        "Utility: event resampling ($n{=}630$). Linkage: persona-block resampling ($n{=}20$ personas). "
        "CIs quantify sampling uncertainty on a fixed generator seed; they do not replace multi-seed robustness.}",
        "\\label{tab:bootstrap-cis}",
        "\\centering",
        "\\small",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\begin{tabular}{@{}lrrr@{}}",
        "\\toprule",
        "Condition & $U(T_o)$ F1 & Ta-1 med-class & $R(z)$ \\\\",
        "\\midrule",
    ]
    for row in rows:
        cid = row["condition_id"].replace("_", "\\_")
        obs = row["obs_failure_mode_macro_f1"]
        med = row["analytics_med_class_macro_f1"]
        link = row["combined_linkage_score"]
        lines.append(
            f"\\texttt{{{cid}}} & "
            f"{obs['point']:.2f} [{obs['ci95_lo']:.2f}, {obs['ci95_hi']:.2f}] & "
            f"{med['point']:.2f} [{med['ci95_lo']:.2f}, {med['ci95_hi']:.2f}] & "
            f"{link['point']:.2f} [{link['ci95_lo']:.2f}, {link['ci95_hi']:.2f}] \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def _plot_figure(rows: list[dict[str, Any]], path: Path) -> None:
    import matplotlib.pyplot as plt

    labels = [r["condition_id"].replace("redact_", "red\\_") for r in rows]
    x = np.arange(len(rows))
    obs = [r["obs_failure_mode_macro_f1"]["point"] for r in rows]
    obs_err = [
        (
            r["obs_failure_mode_macro_f1"]["point"] - r["obs_failure_mode_macro_f1"]["ci95_lo"],
            r["obs_failure_mode_macro_f1"]["ci95_hi"] - r["obs_failure_mode_macro_f1"]["point"],
        )
        for r in rows
    ]
    link = [r["combined_linkage_score"]["point"] for r in rows]
    link_err = [
        (
            r["combined_linkage_score"]["point"] - r["combined_linkage_score"]["ci95_lo"],
            r["combined_linkage_score"]["ci95_hi"] - r["combined_linkage_score"]["point"],
        )
        for r in rows
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharex=True)
    obs_lo, obs_hi = zip(*obs_err)
    axes[0].bar(x, obs, yerr=[obs_lo, obs_hi], capsize=2, color="#2a6f97", alpha=0.85)
    axes[0].set_title("$T_o$ failure-mode macro-F1")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=45, ha="right", fontsize=7)

    link_lo, link_hi = zip(*link_err)
    axes[1].bar(x, link, yerr=[link_lo, link_hi], capsize=2, color="#9b2226", alpha=0.85)
    axes[1].set_title("Combined linkage $R(z)$")
    axes[1].set_ylim(0, 1.05)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=45, ha="right", fontsize=7)

    fig.suptitle("Bootstrap 95% CIs (test split; utility=event, linkage=persona-block)", y=1.02)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
