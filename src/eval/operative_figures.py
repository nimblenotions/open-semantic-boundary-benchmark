"""Operative selection figures and table exports (primary + supplementary analyses)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from eval.figures import FIG_DPI, PRIMARY_LATTICE, _apply_style, _condition_color
from eval.operative_selection import (
    DEFAULT_R_MAX_GRID,
    ConditionPoint,
    build_condition_points,
    dominance_analysis,
    risk_constrained_selection,
    task_bundle_feasibility,
)

PURPOSE_SPECS = [
    ("observability", "u_obs", "Observability $T_o$", "#117733"),
    ("analytics_med", "u_analytics_med", "Analytics $T_a$ (med-class)", "#882255"),
]

# Paper-friendly subset of ε grid for table figures
TABLE_R_MAX_SUBSET = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

PROVENANCE_TAU_GRID = [0.8, 0.9, 1.0]


@dataclass(frozen=True)
class EpsilonSweepPoint:
    epsilon: float
    winner: str | None
    winner_utility: float | None
    n_feasible: int
    feasible: list[str]


def _save(fig: plt.Figure, stem: str, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def _short_label(condition_id: str) -> str:
    return (
        condition_id.replace("redact_", "red_")
        .replace("sem_", "sem_")
        .replace("redact_llm_", "llm_")
    )


def _latex_escape(text: str) -> str:
    escaped = text.replace("\\", r"\textbackslash{}")
    for char, repl in (("_", r"\_"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#")):
        escaped = escaped.replace(char, repl)
    return escaped


def _utility_for_purpose(point: ConditionPoint, util_attr: str) -> float:
    return float(getattr(point, util_attr))


def _matplotlib_table_figure(
    title: str,
    col_labels: list[str],
    rows: list[list[str]],
    out_dir: Path,
    stem: str,
    *,
    figsize: tuple[float, float] | None = None,
    col_widths: list[float] | None = None,
) -> dict[str, Path]:
    """Render a publication-style table as a figure (PNG/PDF)."""
    _apply_style()
    n_rows = len(rows)
    height = max(3.0, 0.38 * (n_rows + 2))
    width = figsize[0] if figsize else max(8.0, 1.2 * len(col_labels))
    if figsize is None:
        figsize = (width, height)
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
        colWidths=col_widths,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.35)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F2F2F2")
        cell.set_edgecolor("#CCCCCC")
    ax.set_title(title, fontsize=11, pad=14, weight="bold")
    fig.tight_layout()
    return _save(fig, stem, out_dir)


def plot_tier_a_risk_constrained_heatmap(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    epsilon_grid: list[float] | None = None,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Heatmap: winner utility by ($R_{max}$, purpose); cell text = winner."""
    _apply_style()
    grid = epsilon_grid or DEFAULT_R_MAX_GRID
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)

    for ax, (purpose, util_attr, title, cmap_base) in zip(axes, PURPOSE_SPECS):
        rows = risk_constrained_selection(
            points, purpose=purpose, r_max_grid=grid, provenance_min=provenance_min
        )
        utils = np.array(
            [r["utility"] if r["utility"] is not None else np.nan for r in rows]
        ).reshape(-1, 1)
        im = ax.imshow(
            utils,
            aspect="auto",
            origin="upper",
            cmap="YlGn",
            vmin=0,
            vmax=1.0,
            extent=[-0.5, 0.5, len(grid) - 0.5, -0.5],
        )
        ax.set_xticks([0])
        ax.set_xticklabels(["Winner"])
        ax.set_yticks(range(len(grid)))
        ax.set_yticklabels([f"{e:.2f}" for e in grid])
        ax.set_ylabel("$R_{\\max}$ ($R \\leq \\varepsilon$)")
        ax.set_title(title)

        for i, r in enumerate(rows):
            winner = _short_label(r["winner"]) if r["winner"] else "—"
            u_txt = f"{r['utility']:.2f}" if r["utility"] is not None else "—"
            ax.text(
                0,
                i,
                f"{winner}\n$U$={u_txt}\n(n={r['n_feasible']})",
                ha="center",
                va="center",
                fontsize=7,
                color="black" if (r["utility"] or 0) < 0.55 else "white",
            )

        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Utility")

    fig.suptitle(
        "Primary analysis: risk-constrained selection ($\\arg\\max U$ s.t. $R \\leq R_{\\max}$, $\\tau \\geq 0.9$)",
        y=1.02,
        fontsize=11,
    )
    fig.tight_layout()
    return _save(fig, "tier_a_risk_constrained_heatmap", out_dir)


def plot_tier_a_risk_constrained_table(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    r_subset: list[float] | None = None,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Side-by-side table figure for paper (subset of $R_{max}$)."""
    subset = r_subset or TABLE_R_MAX_SUBSET
    col_labels = ["$R_{max}$", "Obs winner", "$U_{obs}$", "Ana winner", "$U_{med}$", "# feas (obs/ana)"]
    table_rows: list[list[str]] = []

    obs_rows = {
        r["r_max"]: r
        for r in risk_constrained_selection(
            points, purpose="observability", r_max_grid=subset, provenance_min=provenance_min
        )
    }
    ana_rows = {
        r["r_max"]: r
        for r in risk_constrained_selection(
            points, purpose="analytics_med", r_max_grid=subset, provenance_min=provenance_min
        )
    }

    for eps in subset:
        o = obs_rows[eps]
        a = ana_rows[eps]
        same = "✓" if o["winner"] == a["winner"] and o["winner"] else "≠"
        table_rows.append(
            [
                f"{eps:.2f}",
                _short_label(o["winner"]) if o["winner"] else "—",
                f"{o['utility']:.3f}" if o["utility"] is not None else "—",
                _short_label(a["winner"]) if a["winner"] else "—",
                f"{a['utility']:.3f}" if a["utility"] is not None else "—",
                f"{o['n_feasible']}/{a['n_feasible']} {same}",
            ]
        )

    paths = _matplotlib_table_figure(
        "Risk-constrained winners by linkage budget (primary analysis)",
        col_labels,
        table_rows,
        out_dir,
        "tier_a_risk_constrained_table",
        figsize=(11, max(3.5, 0.42 * (len(table_rows) + 2))),
        col_widths=[0.08, 0.14, 0.08, 0.14, 0.08, 0.12],
    )

    # LaTeX tabular snippet for paper authors
    tex_lines = [
        "% Primary analysis risk-constrained table (paste into main.tex)",
        "\\begin{table}[t]",
        "\\caption{Risk-constrained winners: $\\arg\\max U$ subject to $R \\leq R_{\\max}$ ($\\tau \\geq 0.9$).}",
        "\\label{tab:risk-constrained}",
        "\\small",
        "\\begin{tabular}{@{}rrrrrr@{}}",
        "\\toprule",
        "$R_{\\max}$ & Obs winner & $U_{obs}$ & Ana winner & $U_{med}$ & Feas. \\\\",
        "\\midrule",
    ]
    for row in table_rows:
        tex_lines.append(" & ".join(row) + " \\\\")
    tex_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    tex_path = out_dir / "tier_a_risk_constrained_table.tex"
    tex_path.write_text("\n".join(tex_lines), encoding="utf-8")
    paths["tex"] = tex_path
    return paths


def plot_tier_a_dominance(
    points: list[ConditionPoint],
    out_dir: Path,
) -> dict[str, Path]:
    """Bar chart + table: Pareto frontier vs dominated strategies."""
    _apply_style()
    dom_obs = dominance_analysis(points, purpose="observability")
    dom_ana = dominance_analysis(points, purpose="analytics_med")

    ordered_ids = [p.condition_id for p in points if p.condition_id in PRIMARY_LATTICE]
    id_to_obs = {r["condition_id"]: r for r in dom_obs}
    id_to_ana = {r["condition_id"]: r for r in dom_ana}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    status_colors = {"frontier": "#44AA99", "dominated": "#CC6677", "other": "#DDCC77"}

    for ax, dom_map, title in zip(
        axes,
        [id_to_obs, id_to_ana],
        ["Observability dominance", "Analytics med-class dominance"],
    ):
        x = np.arange(len(ordered_ids))
        colors = []
        for cid in ordered_ids:
            r = dom_map[cid]
            if r["on_pareto_frontier"]:
                colors.append(status_colors["frontier"])
            elif r["never_deploy"]:
                colors.append(status_colors["dominated"])
            else:
                colors.append(status_colors["other"])

        n_dom = [dom_map[cid]["n_dominators"] for cid in ordered_ids]
        bars = ax.bar(x, n_dom, color=colors, width=0.65, edgecolor="white", linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels([_short_label(c) for c in ordered_ids], rotation=35, ha="right")
        ax.set_ylabel("# dominators")
        ax.set_title(title)
        ax.set_ylim(0, max(n_dom) + 0.8)

        for bar, cid in zip(bars, ordered_ids):
            r = dom_map[cid]
            label = "F" if r["on_pareto_frontier"] else ("×" if r["never_deploy"] else "·")
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                label,
                ha="center",
                va="bottom",
                fontsize=8,
                weight="bold",
            )

    legend = [
        Patch(facecolor=status_colors["frontier"], label="On Pareto frontier (F)"),
        Patch(facecolor=status_colors["dominated"], label="Never deploy (×)"),
        Patch(facecolor=status_colors["other"], label="Dominated but not extreme (·)"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Primary analysis: Pareto dominance (# conditions that dominate each arm)", y=1.02)
    fig.tight_layout()
    paths = _save(fig, "tier_a_dominance_chart", out_dir)

    # Table figure
    table_rows = []
    for cid in ordered_ids:
        r = id_to_obs[cid]
        ra = id_to_ana[cid]
        table_rows.append(
            [
                _short_label(cid),
                "yes" if r["on_pareto_frontier"] else "no",
                ", ".join(_short_label(d) for d in r["dominated_by"]) or "—",
                "yes" if r["never_deploy"] else "no",
                "yes" if ra["on_pareto_frontier"] else "no",
                ", ".join(_short_label(d) for d in ra["dominated_by"]) or "—",
            ]
        )
    table_paths = _matplotlib_table_figure(
        "Dominance summary (primary analysis)",
        ["Condition", "Obs F?", "Obs dominated by", "Obs ×", "Ana F?", "Ana dominated by"],
        table_rows,
        out_dir,
        "tier_a_dominance_table",
        figsize=(12, max(4.0, 0.38 * (len(table_rows) + 2))),
    )
    paths.update({f"dominance_table_{k}": v for k, v in table_paths.items()})
    return paths


def plot_tier_a_task_bundles(
    points: list[ConditionPoint],
    out_dir: Path,
) -> dict[str, Path]:
    """Task-bundle feasibility: bar count + condition×bundle matrix."""
    _apply_style()
    bundles = task_bundle_feasibility(points)
    n_feas = [b["n_feasible"] for b in bundles]
    labels = [b["bundle_id"].replace("_", "\n") for b in bundles]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1, 1.4]})

    # Bar chart
    ax0 = axes[0]
    colors = ["#CC6677" if b["empty"] else "#44AA99" for b in bundles]
    x = np.arange(len(bundles))
    ax0.bar(x, n_feas, color=colors, width=0.6, edgecolor="white")
    ax0.set_xticks(x)
    ax0.set_xticklabels(labels, fontsize=7)
    ax0.set_ylabel("# feasible conditions")
    ax0.set_title("Task-bundle feasibility")
    ax0.set_ylim(0, len(points) + 0.5)
    for i, b in enumerate(bundles):
        txt = ", ".join(_short_label(c) for c in b["feasible_conditions"]) or "none"
        ax0.text(i, n_feas[i] + 0.15, str(n_feas[i]), ha="center", fontsize=9, weight="bold")
        ax0.text(i, -0.9, txt, ha="center", va="top", fontsize=6, rotation=0, wrap=True)

    # Matrix heatmap
    ax1 = axes[1]
    cond_ids = [p.condition_id for p in points if p.condition_id in PRIMARY_LATTICE]
    mat = np.zeros((len(bundles), len(cond_ids)))
    for i, b in enumerate(bundles):
        for j, cid in enumerate(cond_ids):
            mat[i, j] = 1.0 if cid in b["feasible_conditions"] else 0.0

    cmap = ListedColormap(["#F5F5F5", "#117733"])
    ax1.imshow(mat, aspect="auto", cmap=cmap, vmin=0, vmax=1)
    ax1.set_xticks(range(len(cond_ids)))
    ax1.set_xticklabels([_short_label(c) for c in cond_ids], rotation=45, ha="right", fontsize=7)
    ax1.set_yticks(range(len(bundles)))
    ax1.set_yticklabels([b["bundle_id"] for b in bundles], fontsize=7)
    ax1.set_title("Feasible (green) vs excluded (gray)")
    for i in range(len(bundles)):
        for j in range(len(cond_ids)):
            sym = "✓" if mat[i, j] else "·"
            ax1.text(j, i, sym, ha="center", va="center", fontsize=9, color="#333333")

    fig.suptitle("Primary analysis: multi-constraint task bundles", y=1.02)
    fig.tight_layout()
    paths = _save(fig, "tier_a_task_bundles", out_dir)

    # Table figure
    table_rows = [
        [
            b["bundle_id"],
            str(b["n_feasible"]),
            ", ".join(_short_label(c) for c in b["feasible_conditions"]) or "*(empty)*",
        ]
        for b in bundles
    ]
    table_paths = _matplotlib_table_figure(
        "Task-bundle constraints and feasible sets",
        ["Bundle", "# feas.", "Feasible conditions"],
        table_rows,
        out_dir,
        "tier_a_task_bundles_table",
        figsize=(10, max(3.5, 0.45 * (len(table_rows) + 2))),
        col_widths=[0.22, 0.08, 0.55],
    )
    paths.update({f"task_bundles_table_{k}": v for k, v in table_paths.items()})

    tex_lines = [
        "% Primary analysis task bundles",
        "\\begin{table}[t]",
        "\\caption{Task-bundle feasibility under registered multi-purpose constraints.}",
        "\\label{tab:task-bundles}",
        "\\small",
        "\\begin{tabular}{@{}lll@{}}",
        "\\toprule",
        "Bundle & \\# feas. & Conditions \\\\",
        "\\midrule",
    ]
    for row in table_rows:
        tex_lines.append(
            f"{_latex_escape(row[0])} & {row[1]} & {_latex_escape(row[2])} \\\\"
        )
    tex_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    tex_path = out_dir / "tier_a_task_bundles_table.tex"
    tex_path.write_text("\n".join(tex_lines), encoding="utf-8")
    paths["task_bundles_tex"] = tex_path
    return paths


def plot_tier_a_perspective_summary(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    r_focus: float = 0.45,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Single figure: different winners at focal $R_{max}$ + dual-purpose bundle."""
    _apply_style()
    obs_row = next(
        r
        for r in risk_constrained_selection(
            points, purpose="observability", r_max_grid=[r_focus], provenance_min=provenance_min
        )
    )
    ana_row = next(
        r
        for r in risk_constrained_selection(
            points, purpose="analytics_med", r_max_grid=[r_focus], provenance_min=provenance_min
        )
    )
    balanced = next(b for b in task_bundle_feasibility(points) if b["bundle_id"] == "dual_purpose_balanced")

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axis("off")

    same = obs_row["winner"] == ana_row["winner"]
    summary = [
        f"Focal linkage budget: $R_{{max}} = {r_focus:.2f}$  (provenance $\\tau \\geq {provenance_min}$)",
        "",
        f"Observability winner:     {_short_label(obs_row['winner'])}  ($U_{{obs}} = {obs_row['utility']:.3f}$)",
        f"Analytics med-class winner: {_short_label(ana_row['winner'])}  ($U_{{med}} = {ana_row['utility']:.3f}$)",
        f"Same winner? {'YES' if same else 'NO — purpose conflict'}",
        "",
        f"Dual-purpose balanced bundle: {balanced['n_feasible']} feasible",
        f"  → {', '.join(_short_label(c) for c in balanced['feasible_conditions']) or 'none'}",
        "",
        "Recommendation: purpose-split exports or pick from bundle — not one global redaction pipeline.",
    ]
    ax.text(
        0.05,
        0.95,
        "\n".join(summary),
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="#F8F8F8", edgecolor="#CCCCCC"),
    )
    ax.set_title("Primary analysis: perspective-dependent selection at $R_{max}=0.45$", fontsize=11, weight="bold")
    fig.tight_layout()
    return _save(fig, "tier_a_perspective_summary", out_dir)


def plot_tier_a_operative_overview(
    points: list[ConditionPoint],
    out_dir: Path,
) -> dict[str, Path]:
    """2×2 panel: utility vs linkage scatter with frontier highlight + bundle inset."""
    _apply_style()
    dom_obs = {r["condition_id"]: r for r in dominance_analysis(points, purpose="observability")}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, util_attr, ylabel, title in zip(
        axes,
        ["u_obs", "u_analytics_med"],
        ["$U_{obs}$", "$U_{med}$"],
        ["Observability", "Analytics med-class"],
    ):
        for pt in points:
            u = _utility_for_purpose(pt, util_attr)
            dom = dom_obs.get(pt.condition_id, {})
            on_f = dom.get("on_pareto_frontier", False)
            marker = "o" if on_f else ("x" if dom.get("never_deploy") else "s")
            size = 90 if on_f else 55
            ax.scatter(
                pt.linkage,
                u,
                c=_condition_color(pt.condition_id),
                s=size,
                marker=marker,
                edgecolors="white",
                linewidths=0.5,
                zorder=3,
            )
            ax.annotate(
                _short_label(pt.condition_id),
                (pt.linkage, u),
                fontsize=7,
                xytext=(4, 4),
                textcoords="offset points",
            )
        ax.set_xlabel("Combined linkage score ($R$)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_xlim(0.25, 0.82)
        ax.set_ylim(0, 1.08)

    fig.suptitle("Primary analysis: utility–linkage scatter (○ frontier, × never deploy)", y=1.02)
    fig.tight_layout()
    return _save(fig, "tier_a_operative_overview", out_dir)


def generate_tier_a_figures(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Generate all Primary analysis operative selection figures and table exports."""
    outputs: dict[str, Path] = {}
    for stem, paths in [
        ("risk_heatmap", plot_tier_a_risk_constrained_heatmap(points, out_dir, provenance_min=provenance_min)),
        ("risk_table", plot_tier_a_risk_constrained_table(points, out_dir, provenance_min=provenance_min)),
        ("dominance", plot_tier_a_dominance(points, out_dir)),
        ("task_bundles", plot_tier_a_task_bundles(points, out_dir)),
        ("perspective", plot_tier_a_perspective_summary(points, out_dir, provenance_min=provenance_min)),
        ("overview", plot_tier_a_operative_overview(points, out_dir)),
    ]:
        for k, v in paths.items():
            outputs[f"tier_a_{stem}_{k}"] = v
    return outputs


def build_epsilon_sweep_series(
    points: list[ConditionPoint],
    *,
    purpose: str,
    util_attr: str,
    epsilon_grid: list[float] | None = None,
    provenance_min: float = 0.9,
) -> list[EpsilonSweepPoint]:
    rows = risk_constrained_selection(
        points,
        purpose=purpose,
        r_max_grid=epsilon_grid,
        provenance_min=provenance_min,
    )
    return [
        EpsilonSweepPoint(
            epsilon=r["r_max"],
            winner=r["winner"],
            winner_utility=r["utility"],
            n_feasible=r["n_feasible"],
            feasible=r["feasible_conditions"],
        )
        for r in rows
    ]


def plot_epsilon_sweep_winner_trace(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    epsilon_grid: list[float] | None = None,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Best feasible utility vs linkage budget ε (step trace + winner labels)."""
    _apply_style()
    grid = epsilon_grid or DEFAULT_R_MAX_GRID
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)

    for ax, (purpose, util_attr, title, color) in zip(axes, PURPOSE_SPECS):
        series = build_epsilon_sweep_series(
            points, purpose=purpose, util_attr=util_attr, epsilon_grid=grid,
            provenance_min=provenance_min,
        )
        eps = [s.epsilon for s in series]
        utils = [s.winner_utility if s.winner_utility is not None else np.nan for s in series]
        ax.step(eps, utils, where="post", color=color, linewidth=2.2, zorder=3)
        ax.scatter(eps, utils, color=color, s=36, zorder=4, edgecolors="white", linewidths=0.6)

        for s in series:
            if s.winner is None:
                continue
            ax.annotate(
                _short_label(s.winner),
                (s.epsilon, s.winner_utility),
                textcoords="offset points",
                xytext=(4, 6),
                fontsize=7,
                color=color,
                alpha=0.95,
            )

        ax.set_title(title)
        ax.set_ylabel("Best feasible utility")
        ax.set_ylim(0, 1.08)
        ax.set_xlabel("Linkage budget $\\varepsilon$ ($R \\leq \\varepsilon$)")

    fig.suptitle(
        f"ε-sweep: risk-constrained winner trace (provenance $\\tau \\geq {provenance_min}$)",
        y=1.02,
        fontsize=11,
    )
    fig.tight_layout()
    return _save(fig, "epsilon_sweep_winner_trace", out_dir)


def plot_epsilon_sweep_condition_bands(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    epsilon_grid: list[float] | None = None,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Horizontal segments: each condition active when $\\varepsilon \\geq R(z_c)$."""
    _apply_style()
    grid = epsilon_grid or DEFAULT_R_MAX_GRID
    eps_min, eps_max = min(grid), max(grid)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)

    ordered = [p for cid in PRIMARY_LATTICE if (p := next((x for x in points if x.condition_id == cid), None))]

    for ax, (purpose, util_attr, title, _) in zip(axes, PURPOSE_SPECS):
        for yi, pt in enumerate(ordered):
            if pt.provenance_completeness < provenance_min:
                continue
            u = _utility_for_purpose(pt, util_attr)
            # Feasible for all epsilon >= linkage (up to plot max)
            x_start = max(pt.linkage, eps_min)
            if x_start > eps_max:
                continue
            ax.hlines(
                u,
                x_start,
                eps_max,
                colors=_condition_color(pt.condition_id),
                linewidth=3.5,
                alpha=0.85,
            )
            ax.plot(
                pt.linkage,
                u,
                marker="|",
                markersize=12,
                color=_condition_color(pt.condition_id),
                markeredgewidth=1.5,
            )
            ax.text(
                eps_min - 0.008,
                u,
                _short_label(pt.condition_id),
                ha="right",
                va="center",
                fontsize=7,
            )

        # Winner step overlay (dashed)
        series = build_epsilon_sweep_series(
            points, purpose=purpose, util_attr=util_attr, epsilon_grid=grid,
            provenance_min=provenance_min,
        )
        winner_eps = [s.epsilon for s in series if s.winner_utility is not None]
        winner_u = [s.winner_utility for s in series if s.winner_utility is not None]
        ax.step(
            winner_eps,
            winner_u,
            where="post",
            color="#222222",
            linewidth=1.5,
            linestyle="--",
            alpha=0.7,
            label="Winner trace",
        )

        ax.set_title(title)
        ax.set_xlabel("Linkage budget $\\varepsilon$")
        ax.set_xlim(eps_min - 0.02, eps_max + 0.02)
        ax.set_ylim(0, 1.08)
        if purpose == "observability":
            ax.set_ylabel("Utility")
        ax.legend(loc="lower right", fontsize=7)

    fig.suptitle(
        f"ε-sweep: condition bands (segment start = $R(z_c)$; dashed = winner; $\\tau \\geq {provenance_min}$)",
        y=1.01,
        fontsize=10,
    )
    fig.tight_layout()
    return _save(fig, "epsilon_sweep_condition_bands", out_dir)


def provenance_gate_ablation(
    points: list[ConditionPoint],
    *,
    epsilon_grid: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Feasible counts and winners across τ grid (provenance gate ablation)."""
    grid = epsilon_grid or DEFAULT_R_MAX_GRID
    rows: list[dict[str, Any]] = []
    for tau in PROVENANCE_TAU_GRID:
        for purpose, util_attr, _, _ in PURPOSE_SPECS:
            series = build_epsilon_sweep_series(
                points,
                purpose=purpose,
                util_attr=util_attr,
                epsilon_grid=grid,
                provenance_min=tau,
            )
            for s in series:
                rows.append(
                    {
                        "provenance_tau": tau,
                        "purpose": purpose,
                        "epsilon": s.epsilon,
                        "winner": s.winner,
                        "winner_utility": s.winner_utility,
                        "n_feasible": s.n_feasible,
                        "feasible_conditions": s.feasible,
                        "provenance_gate_active": any(
                            p.provenance_completeness < tau for p in points
                        ),
                    }
                )
    return rows


def plot_provenance_gate_ablation(
    points: list[ConditionPoint],
    out_dir: Path,
    *,
    epsilon_grid: list[float] | None = None,
) -> dict[str, Path]:
    """Heatmap: # feasible conditions vs (ε, τ); highlights vacuous gate when all prov=1."""
    _apply_style()
    grid = epsilon_grid or DEFAULT_R_MAX_GRID
    ablation = provenance_gate_ablation(points, epsilon_grid=grid)

    any_filtered = any(p.provenance_completeness < 1.0 for p in points)
    min_prov = min(p.provenance_completeness for p in points)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)

    for ax, purpose in zip(axes, ["observability", "analytics_med"]):
        data = np.zeros((len(PROVENANCE_TAU_GRID), len(grid)))
        for i, tau in enumerate(PROVENANCE_TAU_GRID):
            for j, eps in enumerate(grid):
                row = next(
                    r
                    for r in ablation
                    if r["purpose"] == purpose
                    and r["provenance_tau"] == tau
                    and r["epsilon"] == eps
                )
                data[i, j] = row["n_feasible"]

        ax.imshow(
            data,
            aspect="auto",
            origin="lower",
            cmap="YlGn",
            vmin=0,
            vmax=len(points),
            extent=[grid[0] - 0.025, grid[-1] + 0.025, -0.5, len(PROVENANCE_TAU_GRID) - 0.5],
        )
        ax.set_yticks(range(len(PROVENANCE_TAU_GRID)))
        ax.set_yticklabels([f"$\\tau={t}$" for t in PROVENANCE_TAU_GRID])
        ax.set_xticks(grid)
        ax.set_xticklabels([f"{e:.2f}" for e in grid], rotation=45, ha="right")
        title = "Observability" if purpose == "observability" else "Analytics med-class"
        ax.set_title(f"{title}: # feasible conditions")
        ax.set_xlabel("Linkage budget $\\varepsilon$")

        for i in range(len(PROVENANCE_TAU_GRID)):
            for j, eps in enumerate(grid):
                ax.text(
                    eps,
                    i,
                    int(data[i, j]),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black" if data[i, j] < len(points) * 0.6 else "white",
                )

    note = (
        f"All conditions have provenance completeness = {min_prov:.2f}; "
        "rows identical → gate vacuous at $\\tau \\leq 1.0$ (protocol still required)."
        if not any_filtered
        else "Provenance gate filters conditions below $\\tau$."
    )
    fig.suptitle(f"Provenance gate ablation\n{note}", y=1.05, fontsize=10)
    fig.tight_layout()
    paths = _save(fig, "provenance_gate_ablation", out_dir)

    # Markdown summary
    md_lines = [
        "# Provenance gate ablation — supplementary analysis",
        "",
        f"Minimum provenance completeness across lattice: **{min_prov:.3f}**",
        "",
    ]
    if not any_filtered:
        md_lines.extend(
            [
                "At $\\tau \\in \\{0.8, 0.9, 1.0\\}$, **no condition is excluded** — the gate is",
                "vacuous for the v0.1.1 published run but remains part of the operative selection protocol",
                "(decision after verify).",
                "",
            ]
        )
    md_lines.append("## Winners at $\\varepsilon=0.45$ by $\\tau$")
    md_lines.append("")
    md_lines.append("| τ | Purpose | Winner | # feasible |")
    md_lines.append("|---|---------|--------|------------|")
    purpose_labels = {
        "observability": "observability",
        "analytics_med": "analytics (medication-class task)",
    }
    for tau in PROVENANCE_TAU_GRID:
        for purpose in ["observability", "analytics_med"]:
            row = next(
                r
                for r in ablation
                if r["provenance_tau"] == tau
                and r["purpose"] == purpose
                and r["epsilon"] == 0.45
            )
            md_lines.append(
                f"| {tau} | {purpose_labels[purpose]} | {row['winner'] or '—'} | {row['n_feasible']} |"
            )
    md_path = out_dir / "provenance_gate_ablation.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    paths["md"] = md_path

    json_path = out_dir / "provenance_gate_ablation.json"
    json_path.write_text(json.dumps(ablation, indent=2) + "\n", encoding="utf-8")
    paths["json"] = json_path

    return paths


def generate_operative_figures(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    epsilon_grid: list[float] | None = None,
    provenance_min: float = 0.9,
) -> dict[str, Path]:
    """Generate operative selection figures (primary and supplementary analyses)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    points = build_condition_points(obs_metrics, analytics_metrics)
    outputs: dict[str, Path] = {}

    for k, v in generate_tier_a_figures(points, out_dir, provenance_min=provenance_min).items():
        outputs[k] = v

    for key, path in plot_epsilon_sweep_winner_trace(
        points, out_dir, epsilon_grid=epsilon_grid, provenance_min=provenance_min
    ).items():
        outputs[f"epsilon_sweep_winner_trace_{key}"] = path

    for key, path in plot_epsilon_sweep_condition_bands(
        points, out_dir, epsilon_grid=epsilon_grid, provenance_min=provenance_min
    ).items():
        outputs[f"epsilon_sweep_condition_bands_{key}"] = path

    for key, path in plot_provenance_gate_ablation(points, out_dir, epsilon_grid=epsilon_grid).items():
        outputs[f"provenance_gate_ablation_{key}"] = path

    manifest = {
        "tier_a": [k for k in outputs if k.startswith("tier_a_")],
        "tier_b": [k for k in outputs if not k.startswith("tier_a_")],
    }
    (out_dir / "operative_figures_manifest.json").write_text(
        json.dumps({**manifest, "paths": {k: str(v.name) for k, v in outputs.items()}}, indent=2)
        + "\n",
        encoding="utf-8",
    )

    return outputs
