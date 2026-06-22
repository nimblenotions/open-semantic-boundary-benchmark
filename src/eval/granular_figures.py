"""Granular utility×risk figures from obs + analytics metrics (no recompute)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eval.analytics_task import composite_utility
from eval.figures import FROZEN_LATTICE, LLM_CONDITIONS, PRIMARY_LATTICE

FIG_DPI = 300

PRIMARY_LATTICE_9 = PRIMARY_LATTICE

TASK_COLORS = {
    "obs_failure_mode": "#117733",
    "obs_error_stage": "#44AA99",
    "obs_composite": "#117733",
    "analytics_med_class": "#882255",
    "analytics_side_effect": "#CC6677",
    "analytics_adherence": "#DDCC77",
    "analytics_cohort": "#332288",
    "analytics_composite": "#AA4499",
}

FAMILY_MARKERS = {
    "raw": "o",
    "redact": "s",
    "semantic": "^",
    "llm": "D",
}

FAMILY_LABELS = {
    "raw": "raw",
    "redact": "redaction",
    "semantic": "semantic",
    "llm": "LLM transform",
}


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def condition_family(condition_id: str) -> str:
    if condition_id == "raw":
        return "raw"
    if condition_id in LLM_CONDITIONS:
        return "llm"
    if condition_id.startswith("redact"):
        return "redact"
    return "semantic"


def _trial4_block(obs: dict[str, Any], condition_id: str) -> dict[str, Any]:
    cond = obs.get("conditions", {}).get(condition_id, {})
    if cond.get("trial4_adversary"):
        return cond["trial4_adversary"]
    return cond.get("tier0", {}).get("trial4_adversary", {})


def _obs_tier1(obs: dict[str, Any], condition_id: str) -> dict[str, Any]:
    return obs.get("conditions", {}).get(condition_id, {}).get("tier1", {})


def _analytics_tier1(analytics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    return analytics.get("conditions", {}).get(condition_id, {}).get("tier1", {})


def _analytics_cohort(analytics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    cond = analytics.get("conditions", {}).get(condition_id, {})
    if cond.get("tier1_cohort"):
        return cond["tier1_cohort"]
    return cond.get("cohort", {})


RISK_SPECS: list[tuple[str, str, str]] = [
    ("combined_linkage", "Combined linkage", "combined_linkage_score"),
    ("persona_top1", "Persona top-1", "persona_top1"),
    ("persona_top5", "Persona top-5", "persona_top5"),
    ("attr_med_class", "Attr. med-class F1", "medication_class_macro_f1"),
    ("attr_occupation", "Attr. occupation F1", "occupation_sector_macro_f1"),
    ("attr_symptoms", "Attr. symptoms F1", "symptom_categories_macro_f1"),
    ("attr_quasi_id", "Attr. quasi-ID F1", "quasi_id_rarity_macro_f1"),
    ("attr_time", "Attr. time bucket F1", "time_bucket_macro_f1"),
    ("attr_combined", "Attr. combined F1", "attribute_combined_macro_f1"),
    ("longitudinal_auc", "Longitudinal AUC", "longitudinal_linkage_auc"),
    ("token_recovery", "Token recovery", "token_recovery_rate"),
]


def utility_specs(
    obs: dict[str, Any], analytics: dict[str, Any]
) -> list[tuple[str, str, Callable[[str], float | None]]]:
    """Return (task_id, label, getter) for each utility axis."""

    def obs_f1(cid: str) -> float | None:
        t1 = _obs_tier1(obs, cid)
        v = t1.get("failure_mode_macro_f1")
        return float(v) if v is not None else None

    def obs_stage(cid: str) -> float | None:
        t1 = _obs_tier1(obs, cid)
        v = t1.get("error_stage_accuracy")
        return float(v) if v is not None else None

    def obs_comp(cid: str) -> float | None:
        t1 = _obs_tier1(obs, cid)
        fm = t1.get("failure_mode_macro_f1")
        es = t1.get("error_stage_accuracy")
        if fm is None or es is None:
            return None
        return (float(fm) + float(es)) / 2.0

    def ana_med(cid: str) -> float | None:
        t1 = _analytics_tier1(analytics, cid)
        v = t1.get("medication_class_macro_f1")
        return float(v) if v is not None else None

    def ana_se(cid: str) -> float | None:
        t1 = _analytics_tier1(analytics, cid)
        v = t1.get("side_effect_signal_macro_f1")
        return float(v) if v is not None else None

    def ana_adh(cid: str) -> float | None:
        t1 = _analytics_tier1(analytics, cid)
        v = t1.get("adherence_signal_macro_f1")
        return float(v) if v is not None else None

    def ana_comp(cid: str) -> float | None:
        t1 = _analytics_tier1(analytics, cid)
        if t1.get("status") == "ok":
            return composite_utility(t1)
        u = analytics.get("conditions", {}).get(cid, {}).get("tier0", {}).get("utility", {})
        return composite_utility(u) if u else None

    def ana_cohort(cid: str) -> float | None:
        c = _analytics_cohort(analytics, cid)
        v = c.get("cohort_segment_macro_f1")
        return float(v) if v is not None else None

    return [
        ("obs_failure_mode", "Obs failure_mode F1", obs_f1),
        ("obs_error_stage", "Obs error_stage acc", obs_stage),
        ("obs_composite", "Obs composite (mean F1/acc)", obs_comp),
        ("analytics_med_class", "Analytics med-class F1", ana_med),
        ("analytics_side_effect", "Analytics side-effect F1", ana_se),
        ("analytics_adherence", "Analytics adherence F1", ana_adh),
        ("analytics_composite", "Analytics composite F1", ana_comp),
        ("analytics_cohort", "Analytics cohort segment F1", ana_cohort),
    ]


def extract_risk(obs: dict[str, Any], condition_id: str, key: str) -> float | None:
    t4 = _trial4_block(obs, condition_id)
    v = t4.get(key)
    return float(v) if v is not None else None


def _short_label(condition_id: str) -> str:
    return condition_id.replace("redact_", "r_").replace("sem_", "s_")


def _save(fig: plt.Figure, stem: str, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def plot_analytics_task_dedicated(
    analytics: dict[str, Any],
    out_dir: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Path]:
    """One standalone bar chart per analytics utility task (qwen3:8b)."""
    _apply_style()
    cids = conditions or [
        c for c in PRIMARY_LATTICE_9 if c in analytics.get("conditions", {})
    ]
    task_specs = [
        ("med_class", "medication_class_macro_f1", "Analytics: med-class F1 (qwen3:8b)"),
        ("side_effect", "side_effect_signal_macro_f1", "Analytics: side-effect F1 (qwen3:8b)"),
        ("adherence", "adherence_signal_macro_f1", "Analytics: adherence F1 (qwen3:8b)"),
    ]
    outputs: dict[str, Path] = {}
    x = np.arange(len(cids))
    colors = [
        {"raw": "#332288", "redact": "#CC6677", "semantic": "#44AA99", "llm": "#DDCC77"}[
            condition_family(cid)
        ]
        for cid in cids
    ]

    for stem, key, title in task_specs:
        vals = [
            float(_analytics_tier1(analytics, cid).get(key, 0.0) or 0.0) for cid in cids
        ]
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(x, vals, color=colors, width=0.65, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Macro-F1 (qwen3:8b)")
        ax.set_title(title)
        ax.grid(True, alpha=0.25, linestyle="--")
        fig.tight_layout()
        paths = _save(fig, f"analytics_task_{stem}", out_dir)
        outputs.update({f"analytics_task_{stem}_{k}": v for k, v in paths.items()})

    comp_vals = [
        composite_utility(_analytics_tier1(analytics, cid))
        if _analytics_tier1(analytics, cid).get("status") == "ok"
        else 0.0
        for cid in cids
    ]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x, comp_vals, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Composite F1 (qwen3:8b)")
    ax.set_title("Analytics: composite utility (mean Ta-1/2/3)")
    ax.grid(True, alpha=0.25, linestyle="--")
    fig.tight_layout()
    paths = _save(fig, "analytics_task_composite", out_dir)
    outputs.update({f"analytics_task_composite_{k}": v for k, v in paths.items()})

    cohort_vals = [
        float(_analytics_cohort(analytics, cid).get("cohort_segment_macro_f1", 0.0) or 0.0)
        for cid in cids
    ]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x, cohort_vals, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Cohort segment F1")
    ax.set_title("Analytics: cohort segment (qwen3:8b-derived)")
    ax.grid(True, alpha=0.25, linestyle="--")
    fig.tight_layout()
    paths = _save(fig, "analytics_task_cohort", out_dir)
    outputs.update({f"analytics_task_cohort_{k}": v for k, v in paths.items()})

    return outputs


def plot_analytics_by_transform(
    analytics: dict[str, Any],
    out_dir: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Path]:
    """Bar panels: med / side-effect / adherence / composite by transform (qwen3:8b)."""
    _apply_style()
    cids = conditions or [
        c for c in PRIMARY_LATTICE_9 if c in analytics.get("conditions", {})
    ]
    tasks = [
        ("medication_class_macro_f1", "Med class"),
        ("side_effect_signal_macro_f1", "Side effect"),
        ("adherence_signal_macro_f1", "Adherence"),
    ]
    x = np.arange(len(cids))
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    flat = axes.flat

    for ax, (key, title) in zip(flat[:3], tasks, strict=True):
        vals = []
        for cid in cids:
            t1 = _analytics_tier1(analytics, cid)
            vals.append(float(t1.get(key, 0.0) or 0.0))
        colors = [
            {"raw": "#332288", "redact": "#CC6677", "semantic": "#44AA99", "llm": "#DDCC77"}[
                condition_family(cid)
            ]
            for cid in cids
        ]
        ax.bar(x, vals, color=colors, width=0.65, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_title(title)
        ax.set_ylabel("macro-F1 (qwen3:8b)")
        ax.grid(True, alpha=0.25, linestyle="--")

    ax = flat[3]
    comp_vals = []
    for cid in cids:
        t1 = _analytics_tier1(analytics, cid)
        comp_vals.append(composite_utility(t1) if t1.get("status") == "ok" else 0.0)
    colors = [
        {"raw": "#332288", "redact": "#CC6677", "semantic": "#44AA99", "llm": "#DDCC77"}[
            condition_family(cid)
        ]
        for cid in cids
    ]
    ax.bar(x, comp_vals, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in cids], rotation=35, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title("Composite (mean Ta-1/2/3)")
    ax.set_ylabel("Composite F1 (qwen3:8b)")

    fig.suptitle("Analytics utility by transform (qwen3:8b, test split)", y=1.01)
    fig.tight_layout()
    return _save(fig, "analytics_by_transform", out_dir)


def plot_unified_task_scatter(
    obs: dict[str, Any],
    analytics: dict[str, Any],
    out_dir: Path,
    *,
    conditions: list[str] | None = None,
) -> dict[str, Path]:
    """One panel per risk metric: color=task, marker shape=transform family."""
    _apply_style()
    cids = conditions or [
        c for c in PRIMARY_LATTICE_9 if c in obs.get("conditions", {})
    ]
    tasks = utility_specs(obs, analytics)
    n_risk = len(RISK_SPECS)
    ncols = 4
    nrows = int(np.ceil(n_risk / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 3.2, nrows * 2.8))
    axes_flat = np.array(axes).flat

    for ax, (risk_id, risk_label, risk_key) in zip(axes_flat, RISK_SPECS, strict=False):
        for task_id, task_label, getter in tasks:
            for cid in cids:
                rv = extract_risk(obs, cid, risk_key)
                uv = getter(cid)
                if rv is None or uv is None:
                    continue
                ax.scatter(
                    rv,
                    uv,
                    s=36,
                    c=TASK_COLORS.get(task_id, "#888888"),
                    marker=FAMILY_MARKERS[condition_family(cid)],
                    edgecolors="white",
                    linewidths=0.4,
                    alpha=0.85,
                )
        ax.set_xlabel(risk_label, fontsize=7)
        ax.set_ylabel("Utility")
        ax.set_title(risk_label, fontsize=7)
        ax.set_xlim(-0.02, 1.05)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(True, alpha=0.2, linestyle="--")

    for ax in axes_flat[len(RISK_SPECS) :]:
        ax.set_visible(False)

    # Legend: tasks (color) + families (marker)
    task_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=TASK_COLORS[tid],
            markersize=7,
            label=label,
        )
        for tid, label, _ in tasks
    ]
    fam_handles = [
        plt.Line2D(
            [0],
            [0],
            marker=FAMILY_MARKERS[f],
            color="w",
            markerfacecolor="#666666",
            markersize=7,
            label=FAMILY_LABELS[f],
        )
        for f in ("raw", "redact", "semantic", "llm")
    ]
    fig.legend(
        handles=task_handles + fam_handles,
        loc="lower center",
        ncol=6,
        bbox_to_anchor=(0.5, -0.02),
        fontsize=7,
    )
    fig.suptitle(
        "All tasks × linkage risk components (color=task, shape=transform family)",
        y=1.01,
        fontsize=10,
    )
    fig.tight_layout()
    return _save(fig, "unified_task_risk_scatter", out_dir)


def plot_task_risk_small_multiples(
    obs: dict[str, Any],
    analytics: dict[str, Any],
    out_dir: Path,
    *,
    conditions: list[str] | None = None,
    purpose_filter: str | None = None,
) -> dict[str, Path]:
    """Grid: rows=utility tasks, cols=risk metrics; one point per condition."""
    _apply_style()
    cids = conditions or [
        c for c in PRIMARY_LATTICE_9 if c in obs.get("conditions", {})
    ]
    tasks = utility_specs(obs, analytics)
    if purpose_filter == "obs":
        tasks = [t for t in tasks if t[0].startswith("obs_")]
    elif purpose_filter == "analytics":
        tasks = [t for t in tasks if t[0].startswith("analytics_")]

    nrows, ncols = len(tasks), len(RISK_SPECS)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(ncols * 1.55, nrows * 1.45), squeeze=False
    )

    for ri, (task_id, task_label, getter) in enumerate(tasks):
        for ci, (_, risk_label, risk_key) in enumerate(RISK_SPECS):
            ax = axes[ri, ci]
            for cid in cids:
                rv = extract_risk(obs, cid, risk_key)
                uv = getter(cid)
                if rv is None or uv is None:
                    continue
                ax.scatter(
                    rv,
                    uv,
                    s=28,
                    c=TASK_COLORS.get(task_id, "#888888"),
                    marker=FAMILY_MARKERS[condition_family(cid)],
                    edgecolors="white",
                    linewidths=0.3,
                    zorder=3,
                )
            if ri == 0:
                ax.set_title(risk_label, fontsize=6)
            if ci == 0:
                ax.set_ylabel(task_label, fontsize=6)
            ax.set_xlim(-0.02, 1.05)
            ax.set_ylim(-0.02, 1.05)
            ax.tick_params(labelsize=5)
            ax.grid(True, alpha=0.15, linestyle="--")

    stem = (
        "task_risk_small_multiples"
        if not purpose_filter
        else f"task_risk_small_multiples_{purpose_filter}"
    )
    fig.suptitle(f"Utility × risk small multiples ({stem})", y=1.01, fontsize=10)
    fig.tight_layout()
    return _save(fig, stem, out_dir)


def plot_granularity_per_task(
    obs: dict[str, Any],
    analytics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Line plots: sem_coarse → medium → fine for each utility task + linkage."""
    _apply_style()
    sem_chain = ["sem_coarse", "sem_medium", "sem_fine"]
    tasks = utility_specs(obs, analytics)
    n = len(tasks)
    fig, axes = plt.subplots(n, 1, figsize=(6, 2.2 * n), squeeze=False)

    for ax, (task_id, task_label, getter) in zip(axes.flat, tasks, strict=True):
        u_vals = [getter(c) or 0.0 for c in sem_chain]
        r_vals = [extract_risk(obs, c, "combined_linkage_score") or 0.0 for c in sem_chain]
        x = np.arange(len(sem_chain))
        ax2 = ax.twinx()
        ax.plot(x, u_vals, "o-", color=TASK_COLORS.get(task_id, "#117733"), label="Utility")
        ax2.plot(
            x, r_vals, "s--", color="#882255", alpha=0.8, label="Combined linkage"
        )
        ax.set_xticks(x)
        ax.set_xticklabels(["coarse", "medium", "fine"])
        ax.set_ylabel(task_label, color=TASK_COLORS.get(task_id, "#117733"), fontsize=8)
        ax2.set_ylabel("Linkage", color="#882255", fontsize=8)
        ax.set_ylim(0, 1.05)
        ax2.set_ylim(0, max(1.05, max(r_vals) * 1.1 + 0.05))
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax2.spines["top"].set_visible(False)

    fig.suptitle("Policy granularity frontier per utility task", y=1.01)
    fig.tight_layout()
    return _save(fig, "granularity_per_task", out_dir)


def generate_granular_figures(
    obs: dict[str, Any],
    analytics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Generate all granular figure panels; return stem→path map."""
    outputs: dict[str, Path] = {}

    def _register(stem: str, paths: dict[str, Path]) -> None:
        for ext, path in paths.items():
            outputs[f"{stem}_{ext}"] = path

    _register("analytics_by_transform", plot_analytics_by_transform(analytics, out_dir))
    for k, v in plot_analytics_task_dedicated(analytics, out_dir).items():
        outputs[k] = v
    _register("unified_task_risk_scatter", plot_unified_task_scatter(obs, analytics, out_dir))
    _register(
        "task_risk_small_multiples_obs",
        plot_task_risk_small_multiples(obs, analytics, out_dir, purpose_filter="obs"),
    )
    _register(
        "task_risk_small_multiples_analytics",
        plot_task_risk_small_multiples(obs, analytics, out_dir, purpose_filter="analytics"),
    )
    _register(
        "task_risk_small_multiples_all",
        plot_task_risk_small_multiples(obs, analytics, out_dir),
    )
    _register("granularity_per_task", plot_granularity_per_task(obs, analytics, out_dir))
    return outputs
