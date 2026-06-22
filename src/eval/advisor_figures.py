"""Advisor-consolidation figures: utility matrix, linkage decomposition, regret matrix."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from eval.figures import PRIMARY_LATTICE
from eval.operative_selection import (
    DEFAULT_PROVENANCE_MIN,
    build_condition_points,
    risk_constrained_selection,
    _utility_for_purpose,
)
from eval.granular_figures import (
    _analytics_cohort,
    _analytics_tier1,
    _obs_tier1,
    _trial4_block,
    condition_family,
)

FIG_DPI = 300

# Paper heatmap typography (em relative to rcParams["font.size"], typically 10pt).
HEATMAP_CELL_EM = 1.0
HEATMAP_TICK_EM = 1.0
HEATMAP_AXIS_EM = 1.2
HEATMAP_TITLE_EM = 1.2
HEATMAP_CBAR_EM = 1.0

# Registered pilot tasks (primary qwen3:8b consumer); excludes composite scalars.
UTILITY_COLUMNS: list[tuple[str, str, str]] = [
    ("T_o-1", "failure\nmode", "obs_failure_mode"),
    ("T_o-2", "error\nstage", "obs_error_stage"),
    ("Ta-1", "med\nclass", "analytics_med_class"),
    ("Ta-2", "side\neffect", "analytics_side_effect"),
    ("Ta-3", "adher\nence", "analytics_adherence"),
    ("Ta-5", "cohort\nsegment", "analytics_cohort"),
]

LINKAGE_COLUMNS: list[tuple[str, str]] = [
    ("Persona", "persona_top1"),
    ("Attribute", "attribute_combined_macro_f1"),
    ("Longitudinal", "longitudinal_linkage_auc"),
    ("Token", "token_recovery_rate"),
]

# Registered purposes for cross-purpose regret (risk-constrained winners per purpose).
REGRET_PURPOSES: list[tuple[str, str]] = [
    ("observability", "T_o"),
    ("analytics_med", "Ta-1 med-class"),
    ("analytics_side", "Ta-2 side-effect"),
    ("analytics_adherence", "Ta-3 adherence"),
    ("analytics_cohort", "Ta-5 cohort"),
]

DEFAULT_R_MAX_FOCAL = 0.45

PAPER_LABELS: dict[str, str] = {
    "raw": "raw",
    "redact_bracket": "red_bracket",
    "redact_tokenize": "red_tokenize",
    "redact_surrogate": "red_surrogate",
    "redact_llm_substitute": "red_llm_sub",
    "redact_llm_rephrase": "red_llm_reph",
    "sem_coarse": "sem_coarse",
    "sem_medium": "sem_medium",
    "sem_fine": "sem_fine",
}

FAMILY_EDGE_COLORS = {
    "raw": "#332288",
    "redact": "#CC6677",
    "semantic": "#44AA99",
    "llm": "#DDCC77",
}


def _utility_value(
    obs: dict[str, Any],
    analytics: dict[str, Any],
    condition_id: str,
    task_key: str,
) -> float | None:
    if task_key == "obs_failure_mode":
        v = _obs_tier1(obs, condition_id).get("failure_mode_macro_f1")
    elif task_key == "obs_error_stage":
        v = _obs_tier1(obs, condition_id).get("error_stage_accuracy")
    elif task_key == "analytics_med_class":
        v = _analytics_tier1(analytics, condition_id).get("medication_class_macro_f1")
    elif task_key == "analytics_side_effect":
        v = _analytics_tier1(analytics, condition_id).get("side_effect_signal_macro_f1")
    elif task_key == "analytics_adherence":
        v = _analytics_tier1(analytics, condition_id).get("adherence_signal_macro_f1")
    elif task_key == "analytics_cohort":
        v = _analytics_cohort(analytics, condition_id).get("cohort_segment_macro_f1")
    else:
        return None
    return float(v) if v is not None else None


def _linkage_value(obs: dict[str, Any], condition_id: str, metric_key: str) -> float | None:
    v = _trial4_block(obs, condition_id).get(metric_key)
    return float(v) if v is not None else None


def _conditions(
    obs: dict[str, Any], analytics: dict[str, Any]
) -> list[str]:
    return [
        c
        for c in PRIMARY_LATTICE
        if c in obs.get("conditions", {}) and c in analytics.get("conditions", {})
    ]


def _save(fig: plt.Figure, stem: str, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _winner_for_purpose_at_r_max(
    points: list[Any],
    purpose: str,
    r_max: float,
    *,
    provenance_min: float = DEFAULT_PROVENANCE_MIN,
) -> str | None:
    rows = risk_constrained_selection(
        points,
        purpose=purpose,
        r_max_grid=[r_max],
        provenance_min=provenance_min,
    )
    if not rows or rows[0].get("winner") is None:
        return None
    return str(rows[0]["winner"])


def _annotate_heatmap(
    ax: plt.Axes,
    matrix: np.ndarray,
    *,
    fmt: str = ".2f",
    text_color_threshold: float = 0.55,
    cell_fontsize: float | None = None,
) -> None:
    """Place value labels at imshow cell centers (integer coordinates)."""
    if cell_fontsize is None:
        cell_fontsize = 0.7 * plt.rcParams["font.size"]
    n_rows, n_cols = matrix.shape
    for i in range(n_rows):
        for j in range(n_cols):
            val = matrix[i, j]
            if np.isnan(val):
                continue
            color = "white" if val >= text_color_threshold else "#222222"
            ax.text(
                j,
                i,
                format(val, fmt),
                ha="center",
                va="center",
                fontsize=cell_fontsize,
                color=color,
            )


def plot_utility_matrix_heatmap(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Rows = lattice arms; columns = registered utility tasks under T_o and T_a."""
    cids = _conditions(obs_metrics, analytics_metrics)
    n_rows = len(cids)
    n_cols = len(UTILITY_COLUMNS)

    matrix = np.full((n_rows, n_cols), np.nan)
    for i, cid in enumerate(cids):
        for j, (_, _, task_key) in enumerate(UTILITY_COLUMNS):
            matrix[i, j] = _utility_value(obs_metrics, analytics_metrics, cid, task_key)

    cmap = LinearSegmentedColormap.from_list(
        "utility",
        ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
    )

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    _fs = plt.rcParams["font.size"]
    _annotate_heatmap(ax, matrix, cell_fontsize=HEATMAP_CELL_EM * _fs)

    ax.set_xticks(np.arange(n_cols))
    col_labels = [f"{task_id}\n{label}" for task_id, label, _ in UTILITY_COLUMNS]
    ax.set_xticklabels(col_labels, fontsize=HEATMAP_TICK_EM * _fs)
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels([PAPER_LABELS.get(c, c) for c in cids], fontsize=HEATMAP_TICK_EM * _fs)

    for i, cid in enumerate(cids):
        fam = condition_family(cid)
        ax.add_patch(
            Rectangle(
                (-0.55, i - 0.42),
                0.35,
                0.84,
                facecolor=FAMILY_EDGE_COLORS.get(fam, "#888888"),
                clip_on=False,
                transform=ax.transData,
            )
        )

    ax.axvline(x=1.5, color="white", linewidth=2.5)
    _group_y = -0.86
    ax.text(
        0.5,
        _group_y,
        "Observability ($T_o$)",
        ha="center",
        va="top",
        fontsize=HEATMAP_TICK_EM * _fs,
        fontweight="bold",
    )
    ax.text(
        3.5,
        _group_y,
        "Analytics ($T_a$)",
        ha="center",
        va="top",
        fontsize=HEATMAP_TICK_EM * _fs,
        fontweight="bold",
    )

    ax.set_xlabel(
        "Registered consumer task (macro-F1 / accuracy, qwen3:8b)",
        fontsize=HEATMAP_AXIS_EM * _fs,
    )
    ax.set_ylabel("Export lattice arm", fontsize=HEATMAP_AXIS_EM * _fs)
    ax.set_title(
        "Export utility matrix: no single arm maximizes every registered task",
        fontsize=HEATMAP_TITLE_EM * _fs,
        fontweight="bold",
        pad=28,
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Utility", fontsize=HEATMAP_CBAR_EM * _fs)

    fig.tight_layout()
    paths = _save(fig, "utility_matrix_heatmap", out_dir)
    return {f"utility_matrix_{k}": v for k, v in paths.items()}


def plot_linkage_decomposition(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Rows = lattice arms; columns = linkage channels (persona, attribute, longitudinal, token)."""
    cids = [c for c in PRIMARY_LATTICE if c in obs_metrics.get("conditions", {})]
    n_rows = len(cids)
    n_cols = len(LINKAGE_COLUMNS)

    matrix = np.full((n_rows, n_cols), np.nan)
    for i, cid in enumerate(cids):
        for j, (_, metric_key) in enumerate(LINKAGE_COLUMNS):
            matrix[i, j] = _linkage_value(obs_metrics, cid, metric_key)

    cmap = LinearSegmentedColormap.from_list(
        "linkage",
        ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
    )

    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    _fs = plt.rcParams["font.size"]
    _annotate_heatmap(
        ax,
        matrix,
        text_color_threshold=0.5,
        cell_fontsize=HEATMAP_CELL_EM * _fs,
    )

    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(
        [label for label, _ in LINKAGE_COLUMNS],
        fontsize=HEATMAP_TICK_EM * _fs,
    )
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(
        [PAPER_LABELS.get(c, c) for c in cids],
        fontsize=HEATMAP_TICK_EM * _fs,
    )

    for i, cid in enumerate(cids):
        fam = condition_family(cid)
        ax.add_patch(
            Rectangle(
                (-0.55, i - 0.42),
                0.35,
                0.84,
                facecolor=FAMILY_EDGE_COLORS.get(fam, "#888888"),
                clip_on=False,
                transform=ax.transData,
            )
        )

    ax.set_xlabel("Linkage channel", fontsize=HEATMAP_AXIS_EM * _fs)
    ax.set_ylabel("Export lattice arm", fontsize=HEATMAP_AXIS_EM * _fs)
    ax.set_title(
        "Linkage decomposition: lexical suppression $\\neq$ behavioural privacy",
        fontsize=HEATMAP_TITLE_EM * _fs,
        fontweight="bold",
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Risk score", fontsize=HEATMAP_CBAR_EM * _fs)

    fig.tight_layout()
    paths = _save(fig, "linkage_decomposition", out_dir)
    return {f"linkage_decomposition_{k}": v for k, v in paths.items()}


def write_utility_matrix_table(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    table_dir: Path,
) -> Path:
    cids = _conditions(obs_metrics, analytics_metrics)
    rows: list[dict[str, Any]] = []
    for cid in cids:
        row: dict[str, Any] = {"condition_id": cid}
        for task_id, _, task_key in UTILITY_COLUMNS:
            val = _utility_value(obs_metrics, analytics_metrics, cid, task_key)
            row[task_id] = round(val, 4) if val is not None else ""
        rows.append(row)
    fieldnames = ["condition_id"] + [task_id for task_id, _, _ in UTILITY_COLUMNS]
    return _write_csv(table_dir / "utility_matrix.csv", rows, fieldnames)


def write_linkage_decomposition_table(
    obs_metrics: dict[str, Any],
    table_dir: Path,
) -> Path:
    cids = [c for c in PRIMARY_LATTICE if c in obs_metrics.get("conditions", {})]
    rows: list[dict[str, Any]] = []
    for cid in cids:
        row: dict[str, Any] = {"condition_id": cid}
        for label, metric_key in LINKAGE_COLUMNS:
            val = _linkage_value(obs_metrics, cid, metric_key)
            row[label.lower()] = round(val, 4) if val is not None else ""
        rows.append(row)
    fieldnames = ["condition_id"] + [label.lower() for label, _ in LINKAGE_COLUMNS]
    return _write_csv(table_dir / "linkage_decomposition.csv", rows, fieldnames)


def build_cross_purpose_regret_matrix(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    *,
    r_max: float = DEFAULT_R_MAX_FOCAL,
    provenance_min: float = DEFAULT_PROVENANCE_MIN,
) -> dict[str, Any]:
    """Regret[i,j] = U(purpose_j, z*_j) - U(purpose_j, z*_i) at linkage budget r_max."""
    points = build_condition_points(obs_metrics, analytics_metrics)
    point_by_cid = {p.condition_id: p for p in points}
    purposes = [p for p, _ in REGRET_PURPOSES]

    winners: dict[str, str | None] = {
        purpose: _winner_for_purpose_at_r_max(
            points, purpose, r_max, provenance_min=provenance_min
        )
        for purpose in purposes
    }

    n = len(purposes)
    regret = np.full((n, n), np.nan)
    deployed_utility = np.full((n, n), np.nan)
    for i, p_row in enumerate(purposes):
        z_row = winners.get(p_row)
        if not z_row or z_row not in point_by_cid:
            continue
        pt_row = point_by_cid[z_row]
        for j, p_col in enumerate(purposes):
            u_deployed = _utility_for_purpose(pt_row, p_col)
            deployed_utility[i, j] = u_deployed
            z_col = winners.get(p_col)
            if not z_col or z_col not in point_by_cid:
                continue
            u_optimal = _utility_for_purpose(point_by_cid[z_col], p_col)
            regret[i, j] = u_optimal - u_deployed

    return {
        "r_max": r_max,
        "provenance_min": provenance_min,
        "purposes": purposes,
        "purpose_labels": [label for _, label in REGRET_PURPOSES],
        "winners": winners,
        "regret": regret,
        "deployed_utility": deployed_utility,
    }


def write_cross_purpose_regret_table(
    matrix: dict[str, Any],
    table_dir: Path,
) -> Path:
    purposes = matrix["purposes"]
    labels = matrix["purpose_labels"]
    regret = matrix["regret"]
    winners = matrix["winners"]

    rows: list[dict[str, Any]] = []
    for i, (purpose, label) in enumerate(zip(purposes, labels, strict=True)):
        row: dict[str, Any] = {
            "winner_for": purpose,
            "winner_for_label": label,
            "winner_condition": winners.get(purpose, ""),
        }
        for j, p_col in enumerate(purposes):
            val = regret[i, j]
            row[f"regret_on_{p_col}"] = round(float(val), 4) if not np.isnan(val) else ""
        rows.append(row)

    fieldnames = ["winner_for", "winner_for_label", "winner_condition"]
    for p_col in purposes:
        fieldnames.append(f"regret_on_{p_col}")

    meta_path = table_dir / "cross_purpose_regret_meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "r_max": matrix["r_max"],
                "provenance_min": matrix["provenance_min"],
                "winners": winners,
                "column_labels": labels,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return _write_csv(table_dir / "cross_purpose_regret_matrix.csv", rows, fieldnames)


def plot_cross_purpose_regret_matrix(
    matrix: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    regret = matrix["regret"]
    labels = matrix["purpose_labels"]
    winners = matrix["winners"]
    r_max = matrix["r_max"]
    n = len(labels)

    cmap = LinearSegmentedColormap.from_list(
        "regret",
        ["#ffffff", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
    )
    vmax = float(np.nanmax(regret)) if np.any(~np.isnan(regret)) else 0.5
    vmax = max(vmax, 0.05)

    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    im = ax.imshow(regret, aspect="auto", cmap=cmap, vmin=0.0, vmax=vmax)
    _fs = plt.rcParams["font.size"]
    _annotate_heatmap(
        ax,
        regret,
        text_color_threshold=vmax * 0.55,
        cell_fontsize=HEATMAP_CELL_EM * _fs,
    )

    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(labels, fontsize=HEATMAP_TICK_EM * _fs, rotation=25, ha="right")
    ax.set_yticks(np.arange(n))
    ylabels = []
    for purpose, label in REGRET_PURPOSES:
        w = winners.get(purpose) or "—"
        w_short = PAPER_LABELS.get(w, w.replace("redact_", "red_"))
        ylabels.append(f"{label}\n→ {w_short}")

    ax.set_yticklabels(ylabels, fontsize=HEATMAP_TICK_EM * _fs)
    ax.set_xlabel(
        "Utility regret on registered purpose (macro-F1 / accuracy loss)",
        fontsize=HEATMAP_AXIS_EM * _fs,
    )
    ax.set_ylabel(
        f"Risk-constrained winner selected for ($R_{{max}}$={r_max:.2f})",
        fontsize=HEATMAP_AXIS_EM * _fs,
    )
    ax.set_title(
        "Cross-purpose regret: one export cannot serve every stakeholder",
        fontsize=HEATMAP_TITLE_EM * _fs,
        fontweight="bold",
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Regret (optimal − deployed)", fontsize=HEATMAP_CBAR_EM * _fs)

    fig.tight_layout()
    paths = _save(fig, "cross_purpose_regret_matrix", out_dir)
    return {f"cross_purpose_regret_{k}": v for k, v in paths.items()}


def run_advisor_figures(
    obs_metrics_path: Path,
    analytics_metrics_path: Path,
    out_dir: Path,
    *,
    r_max: float = DEFAULT_R_MAX_FOCAL,
) -> dict[str, Any]:
    obs_metrics = json.loads(obs_metrics_path.read_text(encoding="utf-8"))
    analytics_metrics = json.loads(analytics_metrics_path.read_text(encoding="utf-8"))
    table_dir = out_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    figures: dict[str, Path] = {}
    tables: dict[str, Path] = {}

    figures.update(
        plot_utility_matrix_heatmap(obs_metrics, analytics_metrics, out_dir)
    )
    figures.update(plot_linkage_decomposition(obs_metrics, out_dir))
    tables["utility_matrix"] = write_utility_matrix_table(
        obs_metrics, analytics_metrics, table_dir
    )
    tables["linkage_decomposition"] = write_linkage_decomposition_table(
        obs_metrics, table_dir
    )

    regret_matrix = build_cross_purpose_regret_matrix(
        obs_metrics, analytics_metrics, r_max=r_max
    )
    figures.update(plot_cross_purpose_regret_matrix(regret_matrix, out_dir))
    tables["cross_purpose_regret_matrix"] = write_cross_purpose_regret_table(
        regret_matrix, table_dir
    )

    return {
        "conditions": _conditions(obs_metrics, analytics_metrics),
        "r_max": r_max,
        "regret_winners": regret_matrix["winners"],
        "figures": {k: str(v) for k, v in figures.items()},
        "tables": {k: str(v) for k, v in tables.items()},
    }
