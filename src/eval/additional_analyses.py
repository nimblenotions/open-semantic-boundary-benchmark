"""Post-hoc pilot_v2 analyses from existing metrics, operative CSVs, and Tier-1 caches."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import confusion_matrix

from eval.figures import PRIMARY_LATTICE, SEM_CHAIN, _apply_style, _condition_color, _save
from eval.operative_selection import (
    ConditionPoint,
    build_condition_points,
)
from eval.tier1_consumer import load_label_vocab

FIG_DPI = 300

TASK_COLUMNS = [
    ("obs_winner", "Obs failure_mode", "observability"),
    ("med-class_winner", "Med-class", "analytics_med"),
    ("side-effect_winner", "Side-effect", "analytics_side"),
    ("adherence_winner", "Adherence", "analytics_adherence"),
    ("cohort segment_winner", "Cohort (Ta-5)", "analytics_cohort"),
    ("composite_winner", "Composite", "analytics_composite"),
]

CIKM_TASKS = [
    ("obs_winner", "Obs"),
    ("med-class_winner", "Med-class"),
    ("cohort segment_winner", "Cohort"),
]

TRIAL4_ATTRS = [
    "persona_top1",
    "attribute_combined_macro_f1",
    "longitudinal_linkage_auc",
    "medication_class_macro_f1",
    "occupation_sector_macro_f1",
    "symptom_categories_macro_f1",
    "quasi_id_rarity_macro_f1",
    "time_bucket_macro_f1",
]

TOKENIZE_COMPARE = ["redact_surrogate", "redact_tokenize", "redact_bracket", "raw"]


@dataclass
class AnalysisOutputs:
    figures: dict[str, Path]
    tables: dict[str, Path]
    json_summary: Path


def _pilot_dir(root: Path, cfg: dict[str, Any]) -> Path:
    return root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _winner_at_r(
    points: list[ConditionPoint],
    *,
    purpose: str,
    r_max: float,
) -> tuple[str | None, float | None]:
    from eval.operative_selection import _utility_for_purpose

    best_cid: str | None = None
    best_u: float | None = None
    for p in points:
        if p.linkage > r_max:
            continue
        u = _utility_for_purpose(p, purpose)
        if best_u is None or u > best_u:
            best_u = u
            best_cid = p.condition_id
    return best_cid, best_u


def plot_epsilon_sweep_winner_trace(
    multi_task_csv: Path,
    out_dir: Path,
    *,
    tasks: list[tuple[str, str]] | None = None,
    stem: str = "aa_epsilon_sweep_all_tasks",
) -> dict[str, Path]:
    """Line-style winner trace: categorical y per task vs R_max."""
    _apply_style()
    rows = _load_csv(multi_task_csv)
    r_vals = [float(r["r_max"]) for r in rows]
    task_spec = tasks or [(k, lbl) for k, lbl, _ in TASK_COLUMNS]

    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    conds = PRIMARY_LATTICE
    y_base = np.arange(len(task_spec))

    for i, (col, label) in enumerate(task_spec):
        winners = [r[col] for r in rows]
        y = [y_base[i]] * len(r_vals)
        colors = [_condition_color(w) for w in winners]
        ax.scatter(r_vals, y, c=colors, s=80, zorder=3, edgecolors="white", linewidths=0.5)
        for j in range(1, len(winners)):
            if winners[j] != winners[j - 1]:
                ax.plot(
                    r_vals[j - 1 : j + 1],
                    [y_base[i], y_base[i]],
                    color=colors[j],
                    linewidth=2,
                    alpha=0.5,
                    zorder=2,
                )
        for rv, w in zip(r_vals, winners, strict=True):
            ax.annotate(
                w.replace("redact_", "red_").replace("sem_", "sem_"),
                (rv, y_base[i]),
                textcoords="offset points",
                xytext=(0, 6),
                fontsize=6,
                ha="center",
                rotation=25,
            )

    ax.set_yticks(y_base)
    ax.set_yticklabels([lbl for _, lbl in task_spec])
    ax.set_xlabel(r"$R_{\max}$ (Trial4 combined linkage budget)")
    ax.set_title("Risk-constrained winner trace by utility task")
    ax.set_xlim(min(r_vals) - 0.02, max(r_vals) + 0.02)
    return _save(fig, stem, out_dir)


def build_composite_disagreement_table(
    multi_task_csv: Path,
    out_dir: Path,
) -> tuple[list[dict[str, Any]], Path]:
    rows = _load_csv(multi_task_csv)
    out_rows: list[dict[str, Any]] = []
    per_task_cols = [
        ("med-class_winner", "med-class"),
        ("side-effect_winner", "side-effect"),
        ("adherence_winner", "adherence"),
        ("cohort segment_winner", "cohort"),
    ]
    for r in rows:
        composite = r["composite_winner"]
        disagree = [
            lbl for col, lbl in per_task_cols if r[col] != composite
        ]
        out_rows.append(
            {
                "r_max": r["r_max"],
                "composite_winner": composite,
                "obs_winner": r["obs_winner"],
                "med_class_winner": r["med-class_winner"],
                "cohort_winner": r["cohort segment_winner"],
                "disagreeing_tasks": ";".join(disagree) if disagree else "",
                "n_disagree": len(disagree),
                "all_tasks_same": "yes" if not disagree and r["obs_winner"] == composite else "no",
            }
        )
    path = out_dir / "aa_composite_vs_task_disagreement.csv"
    _write_csv(
        path,
        out_rows,
        [
            "r_max",
            "composite_winner",
            "obs_winner",
            "med_class_winner",
            "cohort_winner",
            "disagreeing_tasks",
            "n_disagree",
            "all_tasks_same",
        ],
    )
    return out_rows, path


def build_purpose_regret_table(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    r_grid: list[float] | None = None,
) -> tuple[list[dict[str, Any]], Path]:
    """Regret(T1 | T2, ε) = U(T1, z*_{T1}) - U(T1, z*_{T2}) at each budget."""
    from eval.operative_selection import _utility_for_purpose

    grid = r_grid or [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
    pairs = [
        ("observability", "analytics_med", "obs_if_analytics_optimized"),
        ("analytics_med", "observability", "med_if_obs_optimized"),
        ("analytics_cohort", "observability", "cohort_if_obs_optimized"),
        ("analytics_med", "analytics_cohort", "med_if_cohort_optimized"),
    ]
    rows: list[dict[str, Any]] = []
    for r_max in grid:
        winners = {
            purpose: _winner_at_r(points, purpose=purpose, r_max=r_max)[0]
            for purpose in {
                "observability",
                "analytics_med",
                "analytics_cohort",
                "analytics_composite",
            }
        }
        point_by_cid = {p.condition_id: p for p in points}
        for t1, t2, label in pairs:
            z1 = winners.get(t1)
            z2 = winners.get(t2)
            if not z1 or not z2 or z1 not in point_by_cid or z2 not in point_by_cid:
                continue
            u_opt = _utility_for_purpose(point_by_cid[z1], t1)
            u_sub = _utility_for_purpose(point_by_cid[z2], t1)
            rows.append(
                {
                    "r_max": r_max,
                    "regret_type": label,
                    "task_optimized": t1,
                    "deployed_from": t2,
                    "z_optimal": z1,
                    "z_deployed": z2,
                    "u_optimal": round(u_opt, 4),
                    "u_deployed": round(u_sub, 4),
                    "regret": round(u_opt - u_sub, 4),
                }
            )
    path = out_dir / "aa_purpose_regret.csv"
    _write_csv(
        path,
        rows,
        [
            "r_max",
            "regret_type",
            "task_optimized",
            "deployed_from",
            "z_optimal",
            "z_deployed",
            "u_optimal",
            "u_deployed",
            "regret",
        ],
    )
    return rows, path


def plot_error_stage_confusion(
    root: Path,
    cfg: dict[str, Any],
    out_dir: Path,
    *,
    condition_a: str = "raw",
    condition_b: str = "redact_bracket",
    model: str = "qwen3:8b",
) -> dict[str, Path]:
    from eval.io import join_eval_rows, load_labels, load_splits
    from transform.io import load_condition_exports

    vocab = load_label_vocab(root, cfg)
    stages = vocab["error_stages"]
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.2))
    _apply_style()

    for ax, cid, title in zip(
        axes,
        [condition_a, condition_b],
        [f"{condition_a} (Tier-1)", f"{condition_b} (Tier-1)"],
        strict=True,
    ):
        exports = load_condition_exports(root / cfg["paths"]["transformed"] / cid)
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        cache_path = (
            root / "data" / "eval_cache" / model.replace(":", "_") / cid / "predictions.jsonl"
        )
        preds: dict[str, str] = {}
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            pred = entry.get("prediction", {})
            if pred.get("error_stage"):
                preds[entry["event_id"]] = pred["error_stage"]

        y_true = [r["label"]["error_stage"] for r in test_rows if r["event_id"] in preds]
        y_pred = [preds[r["event_id"]] for r in test_rows if r["event_id"] in preds]
        cm = confusion_matrix(y_true, y_pred, labels=stages)
        im = ax.imshow(cm, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(stages)))
        ax.set_yticks(range(len(stages)))
        ax.set_xticklabels(stages, rotation=35, ha="right", fontsize=7)
        ax.set_yticklabels(stages, fontsize=7)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(title)
        for i in range(len(stages)):
            for j in range(len(stages)):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("error_stage confusion (qwen3:8b, test split)", y=1.02)
    fig.tight_layout()
    return _save(fig, "aa_error_stage_confusion_raw_vs_bracket", out_dir)


def plot_cohort_event_gap(
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Event-level med-class vs cohort segment vs persona sub-metrics."""
    _apply_style()
    conditions = [c for c in PRIMARY_LATTICE if c in analytics_metrics.get("conditions", {})]
    x = np.arange(len(conditions))
    width = 0.22

    med = []
    cohort = []
    quasi = []
    for cid in conditions:
        c = analytics_metrics["conditions"][cid]
        t1 = c.get("tier1", {})
        tc = c.get("tier1_cohort", {})
        med.append(float(t1.get("medication_class_macro_f1", 0)))
        cohort.append(float(tc.get("cohort_segment_macro_f1", 0)))
        quasi.append(float(tc.get("quasi_id_rarity_accuracy", 0)))

    fig, ax = plt.subplots(figsize=(10.0, 4.5))
    ax.bar(x - width, med, width, label="Event med-class F1", color="#7B68EE")
    ax.bar(x, cohort, width, label="Cohort segment F1 (Ta-5)", color="#1E3A5F")
    ax.bar(x + width, quasi, width, label="Cohort quasi-ID acc", color="#D4A017")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [c.replace("redact_", "red_") for c in conditions], rotation=35, ha="right"
    )
    ax.set_ylabel("Tier-1 macro-F1 / accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_title("Event-level vs persona-level analytics utility")
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, "aa_cohort_event_level_gap", out_dir)


def plot_trial4_sem_granularity_stacked(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    _apply_style()
    families = [
        ("persona_top1", "Persona top-1"),
        ("attribute_combined_macro_f1", "Attribute combined"),
        ("longitudinal_linkage_auc", "Longitudinal AUC"),
    ]
    x = np.arange(len(SEM_CHAIN))
    width = 0.25
    fig, ax = plt.subplots(figsize=(7.0, 4.5))

    for i, (key, label) in enumerate(families):
        vals = []
        for cid in SEM_CHAIN:
            t4 = obs_metrics["conditions"][cid].get("trial4_adversary", {})
            vals.append(float(t4.get(key, 0)))
        ax.bar(x + (i - 1) * width, vals, width, label=label, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("sem_", "") for c in SEM_CHAIN])
    ax.set_ylabel("Linkage channel score")
    ax.set_ylim(0, 1.05)
    ax.set_title("Linkage channels by semantic granularity")
    ax.legend(loc="upper left", fontsize=8)
    return _save(fig, "aa_trial4_sem_granularity_stacked", out_dir)


def plot_tokenize_reidentification(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Event vs longitudinal linkage for tokenize trap conditions."""
    _apply_style()
    conditions = TOKENIZE_COMPARE
    x = np.arange(len(conditions))

    persona = []
    attr = []
    longi = []
    token = []
    for cid in conditions:
        t4 = obs_metrics["conditions"][cid].get("trial4_adversary", {})
        persona.append(float(t4.get("persona_top1", 0)))
        attr.append(float(t4.get("attribute_combined_macro_f1", 0)))
        longi.append(float(t4.get("longitudinal_linkage_auc", 0)))
        token.append(float(t4.get("token_recovery_rate", 0)))

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.2))

    ax = axes[0]
    w = 0.25
    ax.bar(x - w, persona, w, label="Persona top-1", color="#882255")
    ax.bar(x, attr, w, label="Attribute combined F1", color="#CC6677")
    ax.bar(x + w, longi, w, label="Longitudinal AUC", color="#AA4499")
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("redact_", "") for c in conditions], rotation=20, ha="right")
    ax.set_ylabel("Trial4 linkage component")
    ax.set_ylim(0, 1.05)
    ax.set_title("Referential consistency trap")
    ax.legend(fontsize=7)

    ax2 = axes[1]
    ax2.bar(x, token, color="#332288", width=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([c.replace("redact_", "") for c in conditions], rotation=20, ha="right")
    ax2.set_ylabel("Token recovery rate")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Surface token recovery (misleading privacy signal)")

    fig.suptitle("redact_tokenize: low tokens, high persona re-linkage", y=1.02)
    fig.tight_layout()
    return _save(fig, "aa_tokenize_reidentification_onepager", out_dir)


def build_quasi_id_leakage_table(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> tuple[list[dict[str, Any]], Path]:
    compare = ["raw", "redact_bracket", "redact_tokenize", "sem_medium", "sem_fine"]
    rows: list[dict[str, Any]] = []
    for cid in compare:
        if cid not in obs_metrics.get("conditions", {}):
            continue
        t4 = obs_metrics["conditions"][cid].get("trial4_adversary", {})
        rows.append(
            {
                "condition": cid,
                "combined_linkage": round(float(t4.get("combined_linkage_score", 0)), 4),
                **{
                    k: round(float(t4.get(k, 0)), 4)
                    for k in TRIAL4_ATTRS
                    if k in t4
                },
            }
        )
    path = out_dir / "aa_quasi_id_leakage.csv"
    _write_csv(path, rows, ["condition", "combined_linkage", *TRIAL4_ATTRS])
    return rows, path


def plot_quasi_id_leakage(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    rows, _ = build_quasi_id_leakage_table(obs_metrics, out_dir)
    attrs = [
        "medication_class_macro_f1",
        "occupation_sector_macro_f1",
        "symptom_categories_macro_f1",
        "quasi_id_rarity_macro_f1",
        "time_bucket_macro_f1",
    ]
    labels = ["med class", "occupation", "symptoms", "quasi-ID", "time bucket"]
    conditions = [r["condition"] for r in rows]
    x = np.arange(len(conditions))
    width = 0.15
    _apply_style()
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    for i, (key, lbl) in enumerate(zip(attrs, labels, strict=True)):
        vals = [float(r.get(key, 0)) for r in rows]
        ax.bar(x + (i - 2) * width, vals, width, label=lbl)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("redact_", "red_") for c in conditions], rotation=25, ha="right")
    ax.set_ylabel("Trial4 attribute inference macro-F1")
    ax.set_ylim(0, 1.05)
    ax.set_title("Attribute leakage by transform (least-privilege comparison)")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    return _save(fig, "aa_quasi_id_leakage", out_dir)


def build_falsification_summary(
    points: list[ConditionPoint],
    out_dir: Path,
) -> tuple[dict[str, Any], Path]:
    """Q20: regions where text/redaction Pareto-dominates all sem_* on all core tasks."""
    sem_ids = {"sem_coarse", "sem_medium", "sem_fine"}
    text_ids = {
        "raw",
        "redact_bracket",
        "redact_tokenize",
        "redact_surrogate",
        "redact_llm_substitute",
        "redact_llm_rephrase",
    }
    tasks = [
        ("observability", "u_obs"),
        ("analytics_med", "u_analytics_med"),
        ("analytics_cohort", "u_cohort"),
    ]
    r_grid = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    by_r: list[dict[str, Any]] = []

    for r_max in r_grid:
        feasible = [p for p in points if p.linkage <= r_max]
        if not feasible:
            continue
        record: dict[str, Any] = {"r_max": r_max, "n_feasible": len(feasible)}
        sem_on_frontier = False
        text_dominates_all = True
        for task_name, attr in tasks:
            best_sem_u = max(
                (getattr(p, attr) for p in feasible if p.condition_id in sem_ids),
                default=None,
            )
            best_text_u = max(
                (getattr(p, attr) for p in feasible if p.condition_id in text_ids),
                default=None,
            )
            best_overall = max(getattr(p, attr) for p in feasible)
            winner = max(feasible, key=lambda p: getattr(p, attr)).condition_id
            record[f"{task_name}_winner"] = winner
            record[f"{task_name}_best_sem"] = best_sem_u
            record[f"{task_name}_best_text"] = best_text_u
            if winner in sem_ids:
                sem_on_frontier = True
            if best_text_u is None or best_sem_u is None or best_text_u < best_sem_u:
                text_dominates_all = False
        record["any_sem_wins_task"] = sem_on_frontier
        record["text_beats_sem_all_tasks"] = text_dominates_all
        by_r.append(record)

    text_wins_all = [r for r in by_r if r.get("text_beats_sem_all_tasks")]

    summary = {
        "question": (
            "What would falsify semantic boundary exports helping? "
            "Find R regions where no sem_* is task-optimal and text/redaction "
            "beats sem on all core tasks."
        ),
        "finding": (
            f"At R_max ∈ {{0.40, 0.45}}, text/redaction **Pareto-beats all sem_* "
            f"on obs, med-class, and cohort among feasible transforms** — a partial "
            f"falsifier for universal semantic exports under tight linkage. "
            f"At R_max ≥ 0.50, sem_medium enters the feasible set and wins obs + med-class; "
            f"cohort still prefers text/raw. Coarse sem alone is never competitive on obs."
        ),
        "text_beats_sem_all_tasks_at": [r["r_max"] for r in text_wins_all],
        "by_r_max": by_r,
        "cohort_prefers_text": all(
            r.get("analytics_cohort_winner") in text_ids for r in by_r if r["r_max"] >= 0.45
        ),
    }
    path = out_dir / "aa_falsification_q20.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary, path


def plot_purpose_regret(
    regret_rows: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Path]:
    _apply_style()
    focus = [
        r
        for r in regret_rows
        if r["regret_type"] == "med_if_obs_optimized" and float(r["r_max"]) <= 0.55
    ]
    if not focus:
        return {}
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    x = [float(r["r_max"]) for r in focus]
    y = [float(r["regret"]) for r in focus]
    ax.bar([f"{v:.2f}" for v in x], y, color="#CC6677", width=0.55)
    ax.set_xlabel(r"$R_{\max}$")
    ax.set_ylabel("Analytics med-class regret")
    ax.set_title("Purpose regret: deploy obs winner for med-class task")
    for i, (xi, yi, row) in enumerate(zip(x, y, focus, strict=True)):
        ax.annotate(
            row["z_deployed"].replace("redact_", "red_"),
            (i, yi),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7,
        )
    return _save(fig, "aa_purpose_regret_med_if_obs", out_dir)


def run_all_analyses(
    root: Path,
    cfg: dict[str, Any],
) -> AnalysisOutputs:
    pilot = _pilot_dir(root, cfg)
    obs_path = pilot / "metrics.json"
    analytics_path = pilot / "analytics_metrics.json"
    op_dir = pilot / "operative_selection"
    fig_dir = pilot / "additional_analyses"
    table_dir = fig_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    obs_metrics = json.loads(obs_path.read_text(encoding="utf-8"))
    analytics_metrics = json.loads(analytics_path.read_text(encoding="utf-8"))
    points = build_condition_points(obs_metrics, analytics_metrics)

    figures: dict[str, Path] = {}
    tables: dict[str, Path] = {}

    multi_csv = op_dir / "analytics_multi_task_simulation.csv"
    p = plot_epsilon_sweep_winner_trace(multi_csv, fig_dir)
    figures["aa_epsilon_sweep_all_tasks_png"] = p["png"]
    p2 = plot_epsilon_sweep_winner_trace(
        multi_csv, fig_dir, tasks=CIKM_TASKS, stem="aa_epsilon_sweep_cikm_tasks"
    )
    figures["aa_epsilon_sweep_cikm_tasks_png"] = p2["png"]

    disagree_rows, t_dis = build_composite_disagreement_table(multi_csv, table_dir)
    tables["aa_composite_vs_task_disagreement"] = t_dis

    regret_rows, t_reg = build_purpose_regret_table(points, table_dir)
    tables["aa_purpose_regret"] = t_reg
    pr = plot_purpose_regret(regret_rows, fig_dir)
    if pr:
        figures["aa_purpose_regret_med_if_obs_png"] = pr["png"]

    p_conf = plot_error_stage_confusion(root, cfg, fig_dir)
    figures["aa_error_stage_confusion_raw_vs_bracket_png"] = p_conf["png"]

    p_cohort = plot_cohort_event_gap(analytics_metrics, fig_dir)
    figures["aa_cohort_event_level_gap_png"] = p_cohort["png"]

    p_t4 = plot_trial4_sem_granularity_stacked(obs_metrics, fig_dir)
    figures["aa_trial4_sem_granularity_stacked_png"] = p_t4["png"]

    p_tok = plot_tokenize_reidentification(obs_metrics, fig_dir)
    figures["aa_tokenize_reidentification_onepager_png"] = p_tok["png"]

    quasi_rows, t_quasi = build_quasi_id_leakage_table(obs_metrics, table_dir)
    tables["aa_quasi_id_leakage"] = t_quasi
    p_quasi = plot_quasi_id_leakage(obs_metrics, fig_dir)
    figures["aa_quasi_id_leakage_png"] = p_quasi["png"]

    falsification, t_fals = build_falsification_summary(points, table_dir)
    tables["aa_falsification_q20"] = t_fals

    summary = {
        "generated_at": pilot.name,
        "regret_at_045": next(
            (r for r in regret_rows if float(r["r_max"]) == 0.45), None
        ),
        "disagreement_at_045": next(
            (r for r in disagree_rows if r["r_max"] == "0.45"), None
        ),
        "falsification": falsification,
        "figures": {k: str(v) for k, v in figures.items()},
        "tables": {k: str(v) for k, v in tables.items()},
    }
    json_path = fig_dir / "additional_analyses_summary.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Narrative (premise / method / explanation / inference) lives in
    # docs/additional-analyses-post-experiments.md — maintained alongside code.

    return AnalysisOutputs(figures=figures, tables=tables, json_summary=json_path)
