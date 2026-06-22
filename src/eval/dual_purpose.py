"""Opt 7: dual-purpose Pareto — U_obs vs U_analytics on same z lattice."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eval.advisor_figures import run_advisor_figures
from eval.analytics_task import composite_utility
from eval.figures import PRIMARY_LATTICE
from eval.granular_figures import (
    FAMILY_MARKERS,
    TASK_COLORS,
    condition_family,
    extract_risk,
    utility_specs,
)

PRIMARY_LATTICE_9 = PRIMARY_LATTICE
FROZEN_LATTICE = PRIMARY_LATTICE[:7]

PALETTE = {
    "raw": "#332288",
    "redact": "#CC6677",
    "sem": "#44AA99",
    "obs": "#117733",
    "analytics": "#882255",
    "llm": "#DDCC77",
}

FRONTIER_LINE = "#555555"


@dataclass(frozen=True)
class _ScatterPoint:
    cid: str
    x: float
    y: float


def pareto_frontier_ids(points: Sequence[_ScatterPoint]) -> set[str]:
    """Non-dominated arms: maximize utility, minimize linkage."""
    frontier: set[str] = set()
    for i, pi in enumerate(points):
        dominated = any(
            i != j
            and pj.y >= pi.y
            and pj.x <= pi.x
            and (pj.y > pi.y or pj.x < pi.x)
            for j, pj in enumerate(points)
        )
        if not dominated:
            frontier.add(pi.cid)
    return frontier


def _cross(o: _ScatterPoint, a: _ScatterPoint, b: _ScatterPoint) -> float:
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)


def pareto_hull_curve(
    points: Sequence[_ScatterPoint], frontier: set[str]
) -> list[_ScatterPoint]:
    """Upper convex hull of Pareto-optimal points (outer left/top envelope)."""
    frontier_pts = [p for p in points if p.cid in frontier]
    if len(frontier_pts) <= 1:
        return frontier_pts
    sorted_pts = sorted(frontier_pts, key=lambda p: (p.x, p.y))
    hull: list[_ScatterPoint] = []
    for p in sorted_pts:
        while len(hull) >= 2 and _cross(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    return hull


def _panel_scatter_points(
    cids: list[str],
    getter: Callable[[str], float | None],
    obs_metrics: dict[str, Any],
) -> list[_ScatterPoint]:
    pts: list[_ScatterPoint] = []
    for cid in cids:
        x = extract_risk(obs_metrics, cid, "combined_linkage_score")
        y = getter(cid)
        if x is None or y is None:
            continue
        pts.append(_ScatterPoint(cid=cid, x=x, y=y))
    return pts


def _trial4_linkage(obs_metrics: dict[str, Any], condition_id: str) -> float:
    cond = obs_metrics.get("conditions", {}).get(condition_id, {})
    t4 = cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})
    return float(t4.get("combined_linkage_score", t4.get("persona_top1", 0.0)))


def _obs_utility(obs_metrics: dict[str, Any], condition_id: str) -> float:
    cond = obs_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("failure_mode_macro_f1") is not None:
        return float(tier1["failure_mode_macro_f1"])
    return float(cond["tier0"]["utility"]["failure_mode_macro_f1"])


def _analytics_utility(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("medication_class_macro_f1") is not None:
        return composite_utility(tier1)
    utility = cond.get("tier0", {}).get("utility", {})
    return composite_utility(utility)


def _condition_color(condition_id: str) -> str:
    fam = condition_family(condition_id)
    if fam == "raw":
        return PALETTE["raw"]
    if fam == "redact":
        return PALETTE["redact"]
    if fam == "llm":
        return PALETTE["llm"]
    return PALETTE["sem"]


def _short_label(condition_id: str) -> str:
    return condition_id.replace("redact_", "red_").replace("sem_", "sem_")


def _conditions_9(
    obs_metrics: dict[str, Any], analytics_metrics: dict[str, Any]
) -> list[str]:
    return [
        c
        for c in PRIMARY_LATTICE_9
        if c in obs_metrics.get("conditions", {})
        and c in analytics_metrics.get("conditions", {})
    ]


def build_dual_pareto_points(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    *,
    conditions: list[str] | None = None,
) -> list[dict[str, Any]]:
    cids = conditions or _conditions_9(obs_metrics, analytics_metrics)
    points: list[dict[str, Any]] = []
    for condition_id in cids:
        points.append(
            {
                "condition_id": condition_id,
                "linkage": _trial4_linkage(obs_metrics, condition_id),
                "u_obs": _obs_utility(obs_metrics, condition_id),
                "u_analytics": _analytics_utility(analytics_metrics, condition_id),
            }
        )
    return points


def plot_dual_pareto(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cids = conditions or _conditions_9(obs_metrics, analytics_metrics)
    points = build_dual_pareto_points(
        obs_metrics, analytics_metrics, conditions=cids
    )

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
    for panel_idx, (ylabel, key) in enumerate(
        [("U_obs (failure_mode F1)", "u_obs"), ("U_analytics (Ta mean F1)", "u_analytics")]
    ):
        ax = axes[panel_idx]
        for pt in points:
            cid = pt["condition_id"]
            ax.scatter(
                pt["linkage"],
                pt[key],
                s=70,
                color=_condition_color(cid),
                marker=FAMILY_MARKERS[condition_family(cid)],
                edgecolors="white",
                linewidths=0.6,
                zorder=3,
            )
            ax.annotate(
                _short_label(cid),
                (pt["linkage"], pt[key]),
                textcoords="offset points",
                xytext=(4, 4),
                fontsize=7,
            )
        ax.set_xlabel("Trial4 combined linkage")
        ax.set_ylabel(ylabel)
        ax.set_xlim(left=-0.02)
        ax.set_ylim(bottom=-0.02, top=1.05)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle("Dual-purpose Pareto (9 conditions, Tier-1 qwen)", fontsize=11)
    fig.tight_layout()
    png = out_dir / "dual_pareto.png"
    pdf = out_dir / "dual_pareto.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"aggregate_png": png, "aggregate_pdf": pdf}


# Linkage-budget bands for triptych (operative-selection grid subset).
R_MAX_BAND_EDGES = [0.0, 0.35, 0.40, 0.45, 0.50, 0.55, 1.05]
R_MAX_BAND_FILL = ["#fdecea", "#fff3e0", "#fffde7", "#e8f5e9", "#e3f2fd", "#f3e5f5"]
R_MAX_BAND_LABELS = [
    r"$R \leq 0.35$",
    r"$\leq 0.40$",
    r"$\leq 0.45$",
    r"$\leq 0.50$",
    r"$\leq 0.55$",
    r"$> 0.55$",
]


def _getter_by_task_id(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    task_id: str,
) -> tuple[str, Callable[[str], float | None]] | None:
    for tid, label, getter in utility_specs(obs_metrics, analytics_metrics):
        if tid == task_id:
            return label, getter
    return None


def _draw_frontier_polyline(ax: plt.Axes, points: Sequence[_ScatterPoint], frontier: set[str]) -> None:
    hull = pareto_hull_curve(points, frontier)
    if len(hull) < 2:
        return
    xs = [p.x for p in hull]
    ys = [p.y for p in hull]
    ax.plot(
        xs,
        ys,
        color=FRONTIER_LINE,
        linestyle="--",
        linewidth=1.4,
        alpha=0.85,
        zorder=2,
        label="_nolegend_",
    )


def _scatter_lattice_arm(
    ax: plt.Axes,
    cids: list[str],
    getter: Callable[[str], float | None],
    obs_metrics: dict[str, Any],
    *,
    point_size: int = 85,
    label_font: int = 8,
    mark_frontier: bool = True,
) -> set[str]:
    pts = _panel_scatter_points(cids, getter, obs_metrics)
    frontier = pareto_frontier_ids(pts) if mark_frontier else {p.cid for p in pts}
    if mark_frontier:
        _draw_frontier_polyline(ax, pts, frontier)

    hull_ids = {p.cid for p in pareto_hull_curve(pts, frontier)} if mark_frontier else frontier

    for p in pts:
        on_hull = p.cid in hull_ids
        ax.scatter(
            p.x,
            p.y,
            s=point_size,
            color=_condition_color(p.cid),
            marker=FAMILY_MARKERS[condition_family(p.cid)],
            edgecolors="white",
            linewidths=0.7,
            alpha=1.0 if on_hull or not mark_frontier else 0.5,
            zorder=3,
        )
        ax.annotate(
            _short_label(p.cid),
            (p.x, p.y),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=label_font,
            alpha=1.0 if on_hull or not mark_frontier else 0.7,
        )
    return frontier


def _style_pareto_axis(ax: plt.Axes, ylabel: str, *, title: str | None = None) -> None:
    ax.set_xlabel("Combined linkage $R(z)$")
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.25, linestyle="--", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _add_rmax_bands(ax: plt.Axes) -> None:
    for i in range(len(R_MAX_BAND_EDGES) - 1):
        lo, hi = R_MAX_BAND_EDGES[i], R_MAX_BAND_EDGES[i + 1]
        ax.axvspan(
            lo,
            hi,
            facecolor=R_MAX_BAND_FILL[i],
            alpha=0.55,
            zorder=0,
            linewidth=0,
        )
        mid = (lo + hi) / 2
        ax.text(
            mid,
            -0.14,
            R_MAX_BAND_LABELS[i],
            ha="center",
            va="top",
            fontsize=7,
            transform=ax.get_xaxis_transform(),
            clip_on=False,
        )
    for edge in R_MAX_BAND_EDGES[1:-1]:
        ax.axvline(edge, color="#555555", linestyle=":", linewidth=0.9, alpha=0.75, zorder=1)


def _add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        0.03,
        0.97,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8),
        zorder=5,
    )


def _plot_task_panel(
    ax: plt.Axes,
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    task_id: str,
    *,
    title: str,
    ylabel: str | None = None,
    rmax_bands: bool = False,
    mark_frontier: bool = True,
    panel_label: str | None = None,
) -> set[str]:
    cids = _conditions_9(obs_metrics, analytics_metrics)
    spec = _getter_by_task_id(obs_metrics, analytics_metrics, task_id)
    if spec is None:
        return set()
    label, getter = spec
    if rmax_bands:
        _add_rmax_bands(ax)
    frontier = _scatter_lattice_arm(
        ax, cids, getter, obs_metrics, mark_frontier=mark_frontier
    )
    _style_pareto_axis(ax, ylabel or label, title=title)
    if panel_label:
        _add_panel_label(ax, panel_label)
    return frontier


def _save_figure(fig: plt.Figure, stem: str, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def _plot_panel_grid(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    stem: str,
    panels: list[tuple[str, str, str]],
    suptitle: str,
    ncols: int,
    figsize: tuple[float, float],
    rmax_bands: bool = False,
    bottom_margin: float = 0.0,
    label_panels: bool = False,
) -> dict[str, Path]:
    n = len(panels)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)
    axes_flat = axes.flat
    panel_labels = [f"({chr(ord('A') + i)})" for i in range(n)] if label_panels else [None] * n
    for ax, (task_id, title, ylabel), plabel in zip(
        axes_flat, panels, panel_labels, strict=True
    ):
        _plot_task_panel(
            ax,
            obs_metrics,
            analytics_metrics,
            task_id,
            title=title,
            ylabel=ylabel,
            rmax_bands=rmax_bands,
            panel_label=plabel,
        )
    for ax in axes_flat[n:]:
        ax.set_visible(False)
    fig.suptitle(suptitle, fontsize=11, y=1.02 if not rmax_bands else 1.03)
    if bottom_margin:
        fig.subplots_adjust(bottom=bottom_margin)
    fig.tight_layout()
    paths = _save_figure(fig, stem, out_dir)
    return {f"{stem}_{k}": v for k, v in paths.items()}


def plot_dual_pareto_main_threepanel(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Main-text figure: (A) observability, (B) med-class, (C) analytics composite."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_main_threepanel",
        panels=[
            ("obs_failure_mode", r"Observability ($T_o$)", r"Failure-mode macro-F1"),
            ("analytics_med_class", r"Med-class ($T_a$)", r"Medication-class macro-F1"),
            (
                "analytics_composite",
                r"Analytics composite ($T_a$)",
                r"Mean Ta-1/2/3 macro-F1",
            ),
        ],
        suptitle="Purpose-specific utility--linkage frontiers (Tier-1 qwen, nine lattice arms)",
        ncols=3,
        figsize=(13.8, 4.3),
        label_panels=True,
    )


def plot_dual_pareto_hero(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Two-panel figure: observability triage vs analytics med-class (Pareto marked)."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_hero",
        panels=[
            ("obs_failure_mode", r"Observability ($T_o$)", r"Failure-mode macro-F1"),
            ("analytics_med_class", r"Analytics med-class ($T_a$)", r"Medication-class macro-F1"),
        ],
        suptitle="Purpose-specific utility--linkage frontiers with Pareto hull (Tier-1 qwen)",
        ncols=2,
        figsize=(9.5, 4.2),
    )


def plot_dual_pareto_obs_vs_analytics_composite(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Observability failure-mode vs analytics event composite (mean Ta-1/2/3)."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_obs_vs_analytics_composite",
        panels=[
            ("obs_failure_mode", r"Observability ($T_o$)", r"Failure-mode macro-F1"),
            (
                "analytics_composite",
                r"Analytics composite ($T_a$)",
                r"Mean Ta-1/2/3 macro-F1",
            ),
        ],
        suptitle="Cross-purpose view: triage task vs pooled analytics utility",
        ncols=2,
        figsize=(9.5, 4.2),
    )


def plot_dual_pareto_composite_purposes(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Mean observability tasks vs mean analytics event tasks."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_composite_purposes",
        panels=[
            (
                "obs_composite",
                r"Observability composite ($T_o$)",
                r"Mean failure-mode F1 + error-stage acc",
            ),
            (
                "analytics_composite",
                r"Analytics composite ($T_a$)",
                r"Mean Ta-1/2/3 macro-F1",
            ),
        ],
        suptitle="Purpose-level composites: $T_o$ vs $T_a$ pooled scores",
        ncols=2,
        figsize=(9.5, 4.2),
    )


def plot_dual_pareto_triptych(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Obs / med-class / cohort with $R_{\\max}$ bands and Pareto hulls."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_triptych",
        panels=[
            ("obs_failure_mode", r"Observability ($T_o$)", r"Failure-mode macro-F1"),
            ("analytics_med_class", r"Med-class analytics", r"Medication-class macro-F1"),
            ("analytics_cohort", r"Cohort analytics (Ta-5)", r"Cohort segment macro-F1"),
        ],
        suptitle="Registered tasks vs linkage with operative $R_{\\max}$ bands",
        ncols=3,
        figsize=(13.5, 4.5),
        rmax_bands=True,
        bottom_margin=0.18,
    )


def plot_dual_pareto_triptych_obs_med_side(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Observability, med-class, and side-effect frontiers."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_triptych_obs_med_side",
        panels=[
            ("obs_failure_mode", r"Observability ($T_o$)", r"Failure-mode macro-F1"),
            ("analytics_med_class", r"Med-class (Ta-1)", r"Medication-class macro-F1"),
            ("analytics_side_effect", r"Side-effect (Ta-2)", r"Side-effect macro-F1"),
        ],
        suptitle="Cross-purpose conflict: observability vs pharmacologic analytics tasks",
        ncols=3,
        figsize=(13.5, 4.5),
    )


def plot_dual_pareto_triptych_analytics_internal(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Within-$T_a$ heterogeneity: med-class, side-effect, cohort segment."""
    return _plot_panel_grid(
        obs_metrics,
        analytics_metrics,
        out_dir,
        stem="dual_pareto_triptych_analytics_internal",
        panels=[
            ("analytics_med_class", r"Med-class (Ta-1)", r"Medication-class macro-F1"),
            ("analytics_side_effect", r"Side-effect (Ta-2)", r"Side-effect macro-F1"),
            ("analytics_cohort", r"Cohort segment (Ta-5)", r"Cohort segment macro-F1"),
        ],
        suptitle="Within-analytics Pareto heterogeneity: policy must register per task",
        ncols=3,
        figsize=(13.5, 4.5),
    )


def plot_dual_pareto_per_task(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """One panel per utility task: linkage (x) vs task utility (y), 9 conditions."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cids = _conditions_9(obs_metrics, analytics_metrics)
    tasks = utility_specs(obs_metrics, analytics_metrics)
    n = len(tasks)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 3.5, nrows * 3.2))
    axes_flat = np.array(axes).flat

    for ax, (task_id, task_label, getter) in zip(axes_flat, tasks, strict=False):
        pts = _panel_scatter_points(cids, getter, obs_metrics)
        frontier = pareto_frontier_ids(pts)
        _draw_frontier_polyline(ax, pts, frontier)
        hull_ids = {p.cid for p in pareto_hull_curve(pts, frontier)}
        for p in pts:
            on_hull = p.cid in hull_ids
            ax.scatter(
                p.x,
                p.y,
                s=55,
                c=TASK_COLORS.get(task_id, "#888888"),
                marker=FAMILY_MARKERS[condition_family(p.cid)],
                edgecolors="white",
                linewidths=0.5,
                alpha=1.0 if on_hull else 0.5,
                zorder=3,
            )
            ax.annotate(
                _short_label(p.cid),
                (p.x, p.y),
                textcoords="offset points",
                xytext=(3, 3),
                fontsize=6,
                alpha=1.0 if on_hull else 0.7,
            )
        ax.set_xlabel("Combined linkage")
        ax.set_ylabel(task_label)
        ax.set_title(task_label, fontsize=8)
        ax.set_xlim(-0.02, 1.05)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    for ax in axes_flat[len(tasks) :]:
        ax.set_visible(False)

    fig.suptitle("Per-task utility vs combined linkage (shape = transform family)", y=1.01)
    fig.tight_layout()
    png = out_dir / "dual_pareto_per_task.png"
    pdf = out_dir / "dual_pareto_per_task.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"per_task_png": png, "per_task_pdf": pdf}


def plot_operative_winner_mismatch(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    r_focus: float = 0.45,
) -> dict[str, Path]:
    """Per-task risk-constrained winners at focal $R_{\\max}$ when Pareto alone is ambiguous."""
    from eval.operative_selection import build_condition_points, risk_constrained_selection

    points = build_condition_points(obs_metrics, analytics_metrics)
    purposes = [
        ("observability", "Obs failure-mode", "u_obs"),
        ("analytics_med", "Med-class", "u_analytics_med"),
        ("analytics_side", "Side-effect", "u_analytics_side"),
        ("analytics_composite", "Analytics composite", "u_analytics_composite"),
        ("analytics_cohort", "Cohort segment", "u_cohort"),
    ]
    winners: list[tuple[str, str, float]] = []
    for purpose, label, _ in purposes:
        row = next(
            r
            for r in risk_constrained_selection(
                points, purpose=purpose, r_max_grid=[r_focus]
            )
        )
        winners.append((label, row["winner"] or "—", float(row["utility"] or 0.0)))

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    y_pos = np.arange(len(winners))
    labels = [w[0] for w in winners]
    colors = [_condition_color(w[1]) if w[1] != "—" else "#AAAAAA" for w in winners]
    ax.barh(y_pos, [w[2] for w in winners], color=colors, alpha=0.85, height=0.55)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Winner utility at feasible set")
    ax.set_xlim(0, 1.08)
    for i, (label, winner, util) in enumerate(winners):
        ax.text(
            util + 0.02,
            i,
            f"{_short_label(winner)}  ({util:.2f})",
            va="center",
            fontsize=8,
        )
    unique = {w[1] for w in winners if w[1] != "—"}
    conflict = "YES" if len(unique) > 1 else "no"
    ax.set_title(
        f"Operative winners at $R_{{max}}={r_focus:.2f}$ — purpose conflict: {conflict}",
        fontsize=10,
        fontweight="bold",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    paths = _save_figure(fig, "operative_winner_mismatch", out_dir)
    return {f"winner_mismatch_{k}": v for k, v in paths.items()}


def plot_operative_regret_focal(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    r_focus: float = 0.45,
) -> dict[str, Path]:
    """Purpose-regret when one task's winner is forced on another (focal budget)."""
    from eval.operative_selection import (
        _utility_for_purpose,
        build_condition_points,
        risk_constrained_selection,
    )

    points = build_condition_points(obs_metrics, analytics_metrics)
    point_by = {p.condition_id: p for p in points}

    def winner(purpose: str) -> str | None:
        row = next(
            r
            for r in risk_constrained_selection(
                points, purpose=purpose, r_max_grid=[r_focus]
            )
        )
        return row["winner"]

    pairs = [
        ("analytics_med", "observability", "Med-class if $T_o$ winner deployed"),
        ("observability", "analytics_med", "Obs if med-class winner deployed"),
    ]
    labels: list[str] = []
    regrets: list[float] = []
    deployed: list[str] = []
    for t1, t2, label in pairs:
        z1, z2 = winner(t1), winner(t2)
        if not z1 or not z2 or z1 not in point_by or z2 not in point_by:
            continue
        u_opt = _utility_for_purpose(point_by[z1], t1)
        u_sub = _utility_for_purpose(point_by[z2], t1)
        labels.append(label)
        regrets.append(max(0.0, u_opt - u_sub))
        deployed.append(z2)

    fig, ax = plt.subplots(figsize=(3.6, 4.0))
    x = np.arange(len(labels))
    bars = ax.bar(x, regrets, color="#CC6677", width=0.5, alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("Utility loss (F1 / acc)")
    ax.set_title(
        f"Purpose regret at $R_{{max}}={r_focus:.2f}$ when Pareto winners disagree",
        fontsize=10,
        fontweight="bold",
    )
    for bar, reg, dep in zip(bars, regrets, deployed, strict=True):
        ax.annotate(
            f"{reg:.3f}\n({_short_label(dep)})",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            textcoords="offset points",
            xytext=(0, 4),
            ha="center",
            fontsize=7,
        )
    ax.set_ylim(0, max(regrets) * 1.35 if regrets else 0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    paths = _save_figure(fig, "operative_regret_focal", out_dir)
    return {f"regret_focal_{k}": v for k, v in paths.items()}


def plot_linkage_channels_dual(
    obs_metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Two-panel: token recovery vs persona linkage; quasi-ID attribute leakage."""
    cids = [
        c
        for c in PRIMARY_LATTICE_9
        if c in obs_metrics.get("conditions", {})
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5))

    ax = axes[0]
    for cid in cids:
        t4 = obs_metrics["conditions"][cid].get("trial4_adversary") or obs_metrics[
            "conditions"
        ][cid].get("tier0", {}).get("trial4_adversary", {})
        tx = float(t4.get("token_recovery_rate", 0.0))
        py = float(t4.get("persona_top1", 0.0))
        ax.scatter(
            tx,
            py,
            s=85,
            color=_condition_color(cid),
            marker=FAMILY_MARKERS[condition_family(cid)],
            edgecolors="white",
            linewidths=0.7,
            zorder=3,
        )
        ax.annotate(
            _short_label(cid),
            (tx, py),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=8,
        )
    ax.set_xlabel("Token recovery rate")
    ax.set_ylabel("Persona top-1 linkage")
    ax.set_title(r"(A) Lexical vs. longitudinal linkage", fontweight="bold")
    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-0.02, 1.05)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax2 = axes[1]
    x = np.arange(len(cids))
    width = 0.35
    quasi = []
    occup = []
    for cid in cids:
        t4 = obs_metrics["conditions"][cid].get("trial4_adversary") or obs_metrics[
            "conditions"
        ][cid].get("tier0", {}).get("trial4_adversary", {})
        quasi.append(float(t4.get("quasi_id_rarity_macro_f1", 0.0)))
        occup.append(float(t4.get("occupation_sector_macro_f1", 0.0)))
    ax2.bar(x - width / 2, quasi, width, label="Quasi-ID rarity F1", color="#D4A017")
    ax2.bar(x + width / 2, occup, width, label="Occupation sector F1", color="#7B68EE")
    ax2.set_xticks(x)
    ax2.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right", fontsize=7)
    ax2.set_ylabel("Attribute-inference macro-F1")
    ax2.set_title("(B) Quasi-identifier leakage", fontweight="bold")
    ax2.set_ylim(0, 1.08)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle(
        "Linkage channels decouple: span metrics miss persona and quasi-ID risk",
        fontsize=11,
        y=1.02,
    )
    fig.tight_layout()
    paths = _save_figure(fig, "linkage_channels_dual", out_dir)
    return {f"linkage_channels_{k}": v for k, v in paths.items()}


def knee_comparison(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify lattice knees: best U at lowest linkage per purpose."""
    if not points:
        return {}
    by_obs = max(points, key=lambda p: (p["u_obs"], -p["linkage"]))
    by_analytics = max(points, key=lambda p: (p["u_analytics"], -p["linkage"]))
    same_knee = by_obs["condition_id"] == by_analytics["condition_id"]
    return {
        "obs_knee": by_obs["condition_id"],
        "analytics_knee": by_analytics["condition_id"],
        "same_knee": same_knee,
        "obs_knee_u": by_obs["u_obs"],
        "analytics_knee_u": by_analytics["u_analytics"],
        "obs_knee_linkage": by_obs["linkage"],
        "analytics_knee_linkage": by_analytics["linkage"],
    }


def plot_frontier_epsilon_merged(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    out_dir: Path,
    *,
    points: list[Any] | None = None,
) -> dict[str, Path]:
    """Main-text F6: dual-purpose Pareto (obs + med-class) + ε-sweep winner trace."""
    from eval.operative_figures import (
        DEFAULT_R_MAX_GRID,
        PURPOSE_SPECS,
        _short_label,
        build_epsilon_sweep_series,
    )
    from eval.operative_selection import build_condition_points

    pts = points or build_condition_points(obs_metrics, analytics_metrics)
    grid = [x for x in DEFAULT_R_MAX_GRID if 0.35 <= x <= 0.75]

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.4))

    for ax, (task_id, title, ylabel, panel) in zip(
        axes[0],
        [
            ("obs_failure_mode", r"$T_o$ failure-mode", r"Macro-F1", "(A)"),
            ("analytics_med_class", r"Ta-1 med-class", r"Macro-F1", "(B)"),
        ],
    ):
        _plot_task_panel(
            ax,
            obs_metrics,
            analytics_metrics,
            task_id,
            title=title,
            ylabel=ylabel,
            mark_frontier=True,
            panel_label=panel,
        )

    for ax, (purpose, util_attr, title, color, panel) in zip(
        axes[1],
        [
            (*PURPOSE_SPECS[0], "(C)"),
            (*PURPOSE_SPECS[1], "(D)"),
        ],
    ):
        series = build_epsilon_sweep_series(
            pts, purpose=purpose, util_attr=util_attr, epsilon_grid=grid
        )
        eps = [s.epsilon for s in series]
        utils = [
            s.winner_utility if s.winner_utility is not None else np.nan for s in series
        ]
        ax.step(eps, utils, where="post", color=color, linewidth=1.8, zorder=3)
        ax.scatter(
            eps, utils, color=color, s=28, zorder=4, edgecolors="white", linewidths=0.5
        )
        for s in series:
            if s.winner is None:
                continue
            ax.annotate(
                _short_label(s.winner),
                (s.epsilon, s.winner_utility),
                textcoords="offset points",
                xytext=(3, 4),
                fontsize=6,
                color=color,
            )
        for focal in (0.40, 0.45, 0.50, 0.55):
            ax.axvline(focal, color="#888888", linestyle=":", linewidth=0.7, alpha=0.7)
        ax.set_title(f"{panel} {title}", fontsize=9, fontweight="bold")
        ax.set_ylabel("Best feasible $U$")
        ax.set_ylim(0, 1.08)
        ax.set_xlabel(r"$R_{\max}$")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Purpose frontiers and risk-constrained winners (Tier-1 qwen)",
        fontsize=10,
        y=1.01,
    )
    fig.tight_layout()
    return _save_figure(fig, "frontier_epsilon_merged", out_dir)


def run_dual_purpose(
    obs_metrics_path: Path,
    analytics_metrics_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    obs_metrics = json.loads(obs_metrics_path.read_text(encoding="utf-8"))
    analytics_metrics = json.loads(analytics_metrics_path.read_text(encoding="utf-8"))
    cids = _conditions_9(obs_metrics, analytics_metrics)
    points = build_dual_pareto_points(
        obs_metrics, analytics_metrics, conditions=cids
    )
    figure_paths = plot_dual_pareto(
        obs_metrics, analytics_metrics, out_dir, conditions=cids
    )
    all_paths: dict[str, Path] = dict(figure_paths)
    all_paths.update(plot_dual_pareto_per_task(obs_metrics, analytics_metrics, out_dir))
    from eval.operative_selection import build_condition_points

    cond_points = build_condition_points(obs_metrics, analytics_metrics)
    all_paths.update(
        plot_frontier_epsilon_merged(
            obs_metrics, analytics_metrics, out_dir, points=cond_points
        )
    )
    for plot_fn in (
        plot_dual_pareto_main_threepanel,
        plot_dual_pareto_hero,
        plot_dual_pareto_obs_vs_analytics_composite,
        plot_dual_pareto_composite_purposes,
        plot_dual_pareto_triptych,
        plot_dual_pareto_triptych_obs_med_side,
        plot_dual_pareto_triptych_analytics_internal,
        plot_operative_winner_mismatch,
        plot_operative_regret_focal,
    ):
        all_paths.update(plot_fn(obs_metrics, analytics_metrics, out_dir))
    all_paths.update(plot_linkage_channels_dual(obs_metrics, out_dir))
    advisor = run_advisor_figures(obs_metrics_path, analytics_metrics_path, out_dir)
    for key, path in advisor.get("figures", {}).items():
        all_paths[key] = Path(path)
    return {
        "points": points,
        "conditions": cids,
        "knees": knee_comparison(points),
        "advisor_figures": advisor,
        "figures": {k: str(v) for k, v in all_paths.items()},
    }
