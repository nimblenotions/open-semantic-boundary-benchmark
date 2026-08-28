"""Generate Phase 4 paper figures from eval metrics (matplotlib, PNG + PDF)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Colorblind-safe palette (Paul Tol–style)
PALETTE = {
    "raw": "#332288",
    "redact": "#CC6677",
    "sem": "#44AA99",
    "tier1": "#DDCC77",
    "linkage": "#882255",
    "utility": "#117733",
}

FROZEN_LATTICE = [
    "raw",
    "redact_bracket",
    "redact_tokenize",
    "redact_surrogate",
    "sem_coarse",
    "sem_medium",
    "sem_fine",
]

LATTICE_RULE_SEMANTIC = list(FROZEN_LATTICE)
LLM_CONDITIONS = ["redact_llm_substitute", "redact_llm_rephrase"]
PRIMARY_LATTICE = LATTICE_RULE_SEMANTIC + LLM_CONDITIONS
H4_PANEL_CONDITIONS = [
    "redact_bracket",
    "sem_medium",
    "redact_llm_substitute",
    "redact_llm_rephrase",
]
SENSITIVITY_MODELS = ["qwen3:8b", "llama3.1:8b", "gemma4:latest"]
SENSITIVITY_MODEL_LABELS = {
    "qwen3:8b": "qwen3:8b",
    "llama3.1:8b": "llama3.1:8b",
    "gemma4:latest": "gemma4:latest",
}

H1_CONDITIONS = ["raw", "redact_bracket", "redact_tokenize", "redact_surrogate"]
SEM_CHAIN = ["sem_coarse", "sem_medium", "sem_fine"]

FIG_DPI = 300


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (6.5, 4.0),
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
        }
    )


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _condition_color(condition_id: str) -> str:
    if condition_id == "raw":
        return PALETTE["raw"]
    if condition_id.startswith("redact"):
        return PALETTE["redact"]
    return PALETTE["sem"]


def _cond(metrics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    return metrics["conditions"][condition_id]


def _tier0_block(metrics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    return _cond(metrics, condition_id).get("tier0", {})


def _has_tier0(metrics: dict[str, Any], conditions: list[str] | None = None) -> bool:
    cids = conditions if conditions is not None else list(metrics.get("conditions", {}))
    return any(
        _tier0_block(metrics, cid).get("utility") for cid in cids if cid in metrics["conditions"]
    )


def _tier1_f1(metrics: dict[str, Any], condition_id: str) -> float | None:
    tier1 = metrics["conditions"][condition_id].get("tier1", {})
    if tier1.get("status") == "deferred":
        return None
    value = tier1.get("failure_mode_macro_f1")
    return float(value) if value is not None else None


def _primary_conditions(metrics: dict[str, Any]) -> list[str]:
    notes = metrics.get("notes", {})
    configured = notes.get("primary_conditions")
    if isinstance(configured, list) and configured:
        return [cid for cid in configured if cid in metrics.get("conditions", {})]
    ordered = PRIMARY_LATTICE
    return [cid for cid in ordered if cid in metrics.get("conditions", {})]


def _has_tier1(metrics: dict[str, Any], conditions: list[str]) -> bool:
    return any(_tier1_f1(metrics, cid) is not None for cid in conditions)


def _utility_f1_label(metrics: dict[str, Any]) -> str:
    if _has_tier1(metrics, _primary_conditions(metrics) or FROZEN_LATTICE):
        return "Macro-F1 failure_mode (Tier-1 qwen)"
    return "Macro-F1 failure_mode (Tier-0)"


def _f1(metrics: dict[str, Any], condition_id: str) -> float:
    tier1 = _tier1_f1(metrics, condition_id)
    if tier1 is not None:
        return tier1
    tier0 = _tier0_block(metrics, condition_id)
    utility = tier0.get("utility", {})
    if utility.get("failure_mode_macro_f1") is not None:
        return float(utility["failure_mode_macro_f1"])
    return 0.0


def _transfer_f1(metrics: dict[str, Any], condition_id: str) -> float:
    transfer = metrics["conditions"][condition_id].get("transfer", {})
    return float(transfer.get("transfer_failure_mode_macro_f1", 0.0))


def _linkage(metrics: dict[str, Any], condition_id: str) -> float:
    risk = _tier0_block(metrics, condition_id).get("risk", {})
    return float(risk.get("persona_top1", 0.0))


def _trial4(metrics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    cond = _cond(metrics, condition_id)
    if cond.get("trial4_adversary"):
        return cond["trial4_adversary"]
    return _tier0_block(metrics, condition_id).get("trial4_adversary", {})


def _trial4_linkage(metrics: dict[str, Any], condition_id: str) -> float:
    t4 = _trial4(metrics, condition_id)
    if t4:
        return float(t4.get("combined_linkage_score", t4.get("persona_top1", 0.0)))
    return _linkage(metrics, condition_id)


def _has_trial4(metrics: dict[str, Any]) -> bool:
    cids = _primary_conditions(metrics) or FROZEN_LATTICE
    return any(_trial4(metrics, cid) for cid in cids if cid in metrics["conditions"])


def _has_trial4_components(metrics: dict[str, Any]) -> bool:
    """True when full Trial4 component metrics exist (not linkage-only stubs)."""
    cids = _primary_conditions(metrics) or FROZEN_LATTICE
    for cid in cids:
        t4 = _trial4(metrics, cid)
        if not t4:
            continue
        if any(
            t4.get(key) not in (None, "", 0.0, 0.5)
            for key in ("persona_top1", "medication_class_macro_f1")
        ):
            return True
    return False


def _token_recovery(metrics: dict[str, Any], condition_id: str) -> float:
    t4 = _trial4(metrics, condition_id)
    if t4.get("token_recovery_rate") is not None:
        return float(t4["token_recovery_rate"])
    risk = _tier0_block(metrics, condition_id).get("risk", {})
    return float(risk.get("token_recovery_rate", 0.0))


def _sensitivity_f1(
    metrics: dict[str, Any], condition_id: str, model: str
) -> float | None:
    tier1 = _cond(metrics, condition_id).get("tier1", {})
    if tier1.get("model") == model and tier1.get("failure_mode_macro_f1") is not None:
        return float(tier1["failure_mode_macro_f1"])
    sens = tier1.get("sensitivity", {})
    block = sens.get(model, {})
    value = block.get("failure_mode_macro_f1")
    return float(value) if value is not None else None


def _analytics_sensitivity_composite(
    metrics: dict[str, Any], condition_id: str, model: str
) -> float | None:
    from eval.analytics_task import composite_utility

    tier1 = _cond(metrics, condition_id).get("tier1", {})
    if tier1.get("model") == model:
        if tier1.get("composite_utility") is not None:
            return float(tier1["composite_utility"])
        if tier1.get("medication_class_macro_f1") is not None:
            return composite_utility(tier1)
    block = tier1.get("sensitivity", {}).get(model, {})
    if block.get("composite_utility") is not None:
        return float(block["composite_utility"])
    if block.get("medication_class_macro_f1") is not None:
        return composite_utility(block)
    return None


def _has_analytics_sensitivity(
    metrics: dict[str, Any],
    *,
    conditions: list[str] | None = None,
    models: list[str] | None = None,
) -> bool:
    cids = conditions or _primary_conditions(metrics)
    model_list = models or SENSITIVITY_MODELS
    models_with_data = 0
    for model in model_list:
        if any(
            _analytics_sensitivity_composite(metrics, cid, model) is not None
            for cid in cids
        ):
            models_with_data += 1
    return models_with_data >= 2


def _has_sensitivity(
    metrics: dict[str, Any],
    *,
    conditions: list[str] | None = None,
    models: list[str] | None = None,
) -> bool:
    cids = conditions or _primary_conditions(metrics)
    model_list = models or SENSITIVITY_MODELS
    models_with_data = 0
    for model in model_list:
        if any(
            _sensitivity_f1(metrics, cid, model) is not None for cid in cids
        ):
            models_with_data += 1
    return models_with_data >= 2


def _has_h4_conditions(metrics: dict[str, Any]) -> bool:
    return all(cid in metrics.get("conditions", {}) for cid in LLM_CONDITIONS)


def _provenance(metrics: dict[str, Any], condition_id: str) -> float | None:
    prov = metrics["conditions"][condition_id].get("provenance", {})
    return prov.get("completeness")


def _save(fig: plt.Figure, stem: str, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def _short_label(condition_id: str) -> str:
    return condition_id.replace("redact_", "red_").replace("sem_", "sem_")


def plot_pareto(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    _apply_style()
    fig, ax = plt.subplots()

    for condition_id in FROZEN_LATTICE:
        x, y = _linkage(metrics, condition_id), _f1(metrics, condition_id)
        ax.scatter(
            x,
            y,
            s=70,
            color=_condition_color(condition_id),
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )
        ax.annotate(
            _short_label(condition_id),
            (x, y),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )

    chain_x = [_linkage(metrics, c) for c in SEM_CHAIN]
    chain_y = [_f1(metrics, c) for c in SEM_CHAIN]
    ax.plot(chain_x, chain_y, "--", color=PALETTE["sem"], alpha=0.7, linewidth=1.5, zorder=2)

    ax.set_xlabel("Persona top-1 (linkage risk)")
    ax.set_ylabel(_utility_f1_label(metrics))
    ax.set_title("Privacy–utility frontier (Fig P)")
    ax.set_xlim(left=-0.02)
    ax.set_ylim(bottom=-0.02, top=1.05)
    return _save(fig, "pareto", out_dir)


def plot_h1_token_recovery(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """H1 panel: token PHI recovery on text redaction arms (Trial4 oracle)."""
    _apply_style()
    fig, ax = plt.subplots()
    colors = [_condition_color(c) for c in H1_CONDITIONS]
    x = np.arange(len(H1_CONDITIONS))
    recovery = [_token_recovery(metrics, c) for c in H1_CONDITIONS]
    ax.bar(x, recovery, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in H1_CONDITIONS], rotation=20, ha="right")
    ax.set_ylabel("Token recovery rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("H1: token PHI recovery (text arms)")
    return _save(fig, "h1_token_recovery", out_dir)


def plot_h1_transfer(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    _apply_style()
    fig, ax = plt.subplots()
    transfer = [_transfer_f1(metrics, c) for c in H1_CONDITIONS]
    colors = [_condition_color(c) for c in H1_CONDITIONS]
    x = np.arange(len(H1_CONDITIONS))
    ax.bar(x, transfer, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in H1_CONDITIONS], rotation=20, ha="right")
    ax.set_ylabel("Transfer macro-F1 (raw-trained)")
    ax.set_ylim(0, 1.05)
    ax.set_title("H1: transfer utility (raw-trained → condition test)")
    return _save(fig, "h1_transfer", out_dir)


def _tier0_error_stage(metrics: dict[str, Any], condition_id: str) -> float:
    utility = _tier0_block(metrics, condition_id).get("utility", {})
    return float(utility.get("error_stage_accuracy", 0.0))


def plot_h1_error_stage_tier0(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """H1 panel: Tier-0 error_stage accuracy on text redaction arms."""
    _apply_style()
    fig, ax = plt.subplots()
    colors = [_condition_color(c) for c in H1_CONDITIONS]
    x = np.arange(len(H1_CONDITIONS))
    vals = [_tier0_error_stage(metrics, c) for c in H1_CONDITIONS]
    ax.bar(x, vals, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in H1_CONDITIONS], rotation=20, ha="right")
    ax.set_ylabel("error_stage accuracy (Tier-0 sklearn)")
    ax.set_ylim(0, 1.05)
    ax.set_title("H1: error_stage under text redaction (Tier-0)")
    return _save(fig, "h1_error_stage_tier0", out_dir)


def plot_obs_error_stage_tier1(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """Obs error_stage accuracy (Tier-1 qwen) across primary lattice."""
    _apply_style()
    conditions = _primary_conditions(metrics) or FROZEN_LATTICE
    vals = [
        float(_cond(metrics, c).get("tier1", {}).get("error_stage_accuracy") or 0.0)
        for c in conditions
    ]
    x = np.arange(len(conditions))
    colors = [_condition_color(c) for c in conditions]
    fig, ax = plt.subplots()
    ax.bar(x, vals, color=colors, width=0.65, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in conditions], rotation=30, ha="right")
    ax.set_ylabel("error_stage accuracy (Tier-1 qwen)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Obs error_stage by transform (Tier-1)")
    return _save(fig, "obs_error_stage_tier1", out_dir)


def plot_h1(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """Legacy alias; prefer dedicated H1 panels."""
    return plot_h1_token_recovery(metrics, out_dir)


def plot_h2(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """H2: Tier-1 qwen macro-F1 across primary lattice (9 conditions)."""
    _apply_style()
    conditions = _primary_conditions(metrics) or FROZEN_LATTICE
    tier1_vals = [_tier1_f1(metrics, c) for c in conditions]
    has_t1 = _has_tier1(metrics, conditions)

    fig, ax = plt.subplots()
    x = np.arange(len(conditions))
    if has_t1:
        vals = [v if v is not None else 0.0 for v in tier1_vals]
        ax.bar(x, vals, width=0.65, color=PALETTE["tier1"], zorder=3)
        ylabel = "Macro-F1 failure_mode (Tier-1 qwen)"
    else:
        vals = [_f1(metrics, c) for c in conditions]
        ax.bar(x, vals, width=0.65, color=PALETTE["utility"], zorder=3)
        ylabel = "Macro-F1 failure_mode (Tier-0)"
    ax.set_xticks(x)
    ax.set_xticklabels([_short_label(c) for c in conditions], rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1.05)
    ax.set_title("H2: utility recovery (Tier-1 qwen, test split)")
    return _save(fig, "h2_utility_recovery", out_dir)


def plot_h3(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    _apply_style()
    fig, ax1 = plt.subplots()
    x = np.arange(len(SEM_CHAIN))
    f1_vals = [_f1(metrics, c) for c in SEM_CHAIN]
    link_vals = [_trial4_linkage(metrics, c) for c in SEM_CHAIN]

    line1 = ax1.plot(
        x,
        f1_vals,
        "o-",
        color=PALETTE["utility"],
        linewidth=2,
        markersize=8,
        label="Macro-F1",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels([c.replace("sem_", "") for c in SEM_CHAIN])
    ax1.set_ylabel("Macro-F1 failure_mode", color=PALETTE["utility"])
    ax1.set_ylim(0, 1.05)
    ax1.tick_params(axis="y", labelcolor=PALETTE["utility"])
    ax1.set_xlabel("Semantic granularity")
    ax1.set_title("H3: granularity frontier")

    ax2 = ax1.twinx()
    line2 = ax2.plot(
        x,
        link_vals,
        "s--",
        color=PALETTE["linkage"],
        linewidth=2,
        markersize=7,
        label="Trial4 linkage",
    )
    ax2.set_ylabel("Trial4 combined linkage", color=PALETTE["linkage"])
    ax2.set_ylim(-0.02, min(1.05, max(link_vals) * 1.15 + 0.05))
    ax2.tick_params(axis="y", labelcolor=PALETTE["linkage"])

    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc="upper left")
    return _save(fig, "h3_granularity", out_dir)


def plot_h4(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """H4: LLM transform arms vs rule redaction and sem_medium knee."""
    _apply_style()
    conditions = [c for c in H4_PANEL_CONDITIONS if c in metrics.get("conditions", {})]
    if len(conditions) < 2:
        raise ValueError("H4 panel requires LLM and baseline conditions in metrics")

    fig, ax1 = plt.subplots()
    x = np.arange(len(conditions))
    f1_vals = [_f1(metrics, c) for c in conditions]
    link_vals = [_trial4_linkage(metrics, c) for c in conditions]
    colors = [_condition_color(c) for c in conditions]

    ax1.bar(x, f1_vals, color=colors, width=0.55, zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels([_short_label(c) for c in conditions], rotation=20, ha="right")
    ax1.set_ylabel("Tier-1 macro-F1", color=PALETTE["utility"])
    ax1.set_ylim(0, 1.05)
    ax1.set_title("H4: LLM sanitization vs rule redaction / sem_medium")

    ax2 = ax1.twinx()
    ax2.plot(
        x,
        link_vals,
        "D--",
        color=PALETTE["linkage"],
        linewidth=2,
        markersize=7,
        label="Trial4 linkage",
    )
    ax2.set_ylabel("Trial4 combined linkage", color=PALETTE["linkage"])
    ax2.set_ylim(-0.02, 1.05)
    ax2.tick_params(axis="y", labelcolor=PALETTE["linkage"])

    return _save(fig, "h4_llm_arms", out_dir)


def plot_sensitivity(
    metrics: dict[str, Any],
    out_dir: Path,
    *,
    analytics_metrics: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Open-weight sensitivity: grouped bars by model (qwen / llama / gemma)."""
    _apply_style()
    conditions = _primary_conditions(metrics) or FROZEN_LATTICE
    dual_panel = analytics_metrics is not None and _has_analytics_sensitivity(
        analytics_metrics, conditions=conditions
    )

    if dual_panel:
        fig, axes = plt.subplots(2, 1, figsize=(9.0, 7.5), sharex=True)
        ax_obs, ax_ana = axes
    else:
        fig, ax_obs = plt.subplots(figsize=(9.0, 4.5))
        ax_ana = None

    models = [
        m
        for m in SENSITIVITY_MODELS
        if _has_sensitivity(metrics, conditions=[conditions[0]], models=[m])
        or any(_sensitivity_f1(metrics, cid, m) is not None for cid in conditions)
    ]
    if not models:
        models = [
            m
            for m in SENSITIVITY_MODELS
            if any(_sensitivity_f1(metrics, cid, m) is not None for cid in conditions)
        ]
    if not models:
        raise ValueError("no sensitivity metrics available for figure")

    x = np.arange(len(conditions))
    width = 0.8 / len(models)
    palette_models = ["#332288", "#CC6677", "#44AA99"]

    for idx, model in enumerate(models):
        offsets = x + (idx - (len(models) - 1) / 2) * width
        vals = [_sensitivity_f1(metrics, cid, model) or 0.0 for cid in conditions]
        ax_obs.bar(
            offsets,
            vals,
            width=width * 0.95,
            label=SENSITIVITY_MODEL_LABELS.get(model, model),
            color=palette_models[idx % len(palette_models)],
            zorder=3,
        )

    ax_obs.set_xticks(x)
    if ax_ana is None:
        ax_obs.set_xticklabels(
            [_short_label(c) for c in conditions], rotation=30, ha="right"
        )
    else:
        ax_obs.tick_params(labelbottom=False)
    ax_obs.set_ylabel("Obs failure_mode macro-F1")
    ax_obs.set_ylim(0, 1.05)
    ax_obs.set_title("Tier-1 consumer sensitivity (test split)")
    ax_obs.legend(loc="upper right", fontsize=8)

    if ax_ana is not None and analytics_metrics is not None:
        for idx, model in enumerate(models):
            offsets = x + (idx - (len(models) - 1) / 2) * width
            vals = [
                _analytics_sensitivity_composite(analytics_metrics, cid, model) or 0.0
                for cid in conditions
            ]
            ax_ana.bar(
                offsets,
                vals,
                width=width * 0.95,
                label=SENSITIVITY_MODEL_LABELS.get(model, model),
                color=palette_models[idx % len(palette_models)],
                zorder=3,
            )
        ax_ana.set_xticks(x)
        ax_ana.set_xticklabels(
            [_short_label(c) for c in conditions], rotation=30, ha="right"
        )
        ax_ana.set_ylabel("Analytics composite macro-F1")
        ax_ana.set_ylim(0, 1.05)
        ax_ana.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    return _save(fig, "sensitivity_models", out_dir)


def write_r4_table(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "r4_summary.csv"
    rows: list[dict[str, Any]] = []

    for condition_id in _primary_conditions(metrics) or FROZEN_LATTICE:
        if condition_id not in metrics.get("conditions", {}):
            continue
        tier0 = _tier0_block(metrics, condition_id)
        tier0_utility = tier0.get("utility", {})
        tier0_risk = tier0.get("risk", {})
        tier1 = _cond(metrics, condition_id).get("tier1", {})
        transfer = _cond(metrics, condition_id).get("transfer", {})
        trial4 = _trial4(metrics, condition_id)
        rows.append(
            {
                "condition": condition_id,
                "role": _cond(metrics, condition_id).get("role", "frozen"),
                "tier0_f1": tier0_utility.get("failure_mode_macro_f1", ""),
                "transfer_f1": transfer.get("transfer_failure_mode_macro_f1", ""),
                "tier0_error_stage_acc": tier0_utility.get("error_stage_accuracy", ""),
                "transfer_error_stage_acc": transfer.get(
                    "transfer_error_stage_accuracy", ""
                ),
                "tier1_f1": tier1.get("failure_mode_macro_f1", ""),
                "tier1_status": tier1.get("status", ""),
                "trial4_linkage": trial4.get("combined_linkage_score", ""),
                "persona_top1": tier0_risk.get("persona_top1", ""),
                "token_recovery": _token_recovery(metrics, condition_id),
                "provenance": _provenance(metrics, condition_id),
            }
        )

    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis("off")
    headers = [
        "Condition",
        "Tier-0 F1",
        "Transfer F1",
        "Tier-1 F1",
        "Trial4 link.",
        "Top-1",
        "Token rec.",
        "Prov.",
    ]
    def _fmt(val: Any, *, na: str = "—") -> str:
        if val == "" or val is None:
            return na
        return f"{float(val):.3f}"

    table_rows = [
        [
            r["condition"],
            _fmt(r["tier0_f1"]),
            _fmt(r["transfer_f1"]),
            _fmt(r["tier1_f1"]),
            _fmt(r["trial4_linkage"]),
            _fmt(r["persona_top1"]),
            _fmt(r["token_recovery"]),
            _fmt(r["provenance"], na="n/a") if r["provenance"] is not None else "n/a",
        ]
        for r in rows
    ]
    table = ax.table(
        cellText=table_rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.4)
    ax.set_title("R4: main results summary (test split)", pad=12)
    png_paths = _save(fig, "r4_summary_table", out_dir)
    return {"csv": csv_path, **png_paths}


def write_config_snapshot(cfg: dict[str, Any], config_path: Path, out_dir: Path) -> Path:
    import shutil
    from datetime import UTC, datetime

    snapshot_dir = out_dir / "config_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    dest = snapshot_dir / config_path.name
    shutil.copy2(config_path, dest)
    manifest = {
        "copied_at_utc": datetime.now(UTC).isoformat(),
        "config_source": str(config_path),
        "config_copy": str(dest),
        "study": cfg.get("study", {}),
        "persona_count": cfg.get("persona_count", cfg.get("corpus", {}).get("persona_count")),
    }
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return snapshot_dir


def plot_adversary_pareto(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """Privacy–utility frontier using Trial4 combined linkage score."""
    _apply_style()
    fig, ax = plt.subplots()

    for condition_id in _primary_conditions(metrics) or FROZEN_LATTICE:
        if condition_id not in metrics["conditions"]:
            continue
        x, y = _trial4_linkage(metrics, condition_id), _f1(metrics, condition_id)
        ax.scatter(
            x,
            y,
            s=70,
            color=_condition_color(condition_id),
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )
        ax.annotate(
            _short_label(condition_id),
            (x, y),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )

    chain_x = [_trial4_linkage(metrics, c) for c in SEM_CHAIN]
    chain_y = [_f1(metrics, c) for c in SEM_CHAIN]
    ax.plot(chain_x, chain_y, "--", color=PALETTE["sem"], alpha=0.7, linewidth=1.5, zorder=2)

    ax.set_xlabel("Combined linkage score (Trial4 adversary)")
    ax.set_ylabel(_utility_f1_label(metrics))
    ax.set_title("Trial4 privacy–utility frontier")
    ax.set_xlim(left=-0.02)
    ax.set_ylim(bottom=-0.02, top=1.05)
    return _save(fig, "adversary_pareto", out_dir)


def plot_adversary_bars(metrics: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """Grouped bars: persona top-1/top-5, med-class F1, linkage AUC by condition."""
    _apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.5))
    conditions = [c for c in (_primary_conditions(metrics) or FROZEN_LATTICE) if c in metrics["conditions"]]
    x = np.arange(len(conditions))
    colors = [_condition_color(c) for c in conditions]

    series = [
        ("Persona top-1", [float(_trial4(metrics, c).get("persona_top1", 0.0)) for c in conditions]),
        ("Persona top-5", [float(_trial4(metrics, c).get("persona_top5", 0.0)) for c in conditions]),
        (
            "Med-class macro-F1",
            [float(_trial4(metrics, c).get("medication_class_macro_f1", 0.0)) for c in conditions],
        ),
        (
            "Linkage AUC",
            [float(_trial4(metrics, c).get("longitudinal_linkage_auc", 0.5)) for c in conditions],
        ),
    ]

    for ax, (title, values) in zip(axes.flat, series, strict=True):
        ax.bar(x, values, color=colors, width=0.65, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels([_short_label(c) for c in conditions], rotation=25, ha="right", fontsize=7)
        ax.set_ylabel(title)
        ax.set_ylim(0, 1.05)
        ax.set_title(title)

    fig.suptitle("Trial4 adversary metrics by lattice condition", y=1.02)
    fig.tight_layout()
    return _save(fig, "adversary_bars", out_dir)


def plot_retention_vs_utility(
    retention: dict[str, Any],
    metrics: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    """Scatter retention (cosine mean) vs Tier-0 F1 by condition (appendix diagnostic)."""
    _apply_style()
    fig, ax = plt.subplots()

    for condition_id, row in retention.get("conditions", {}).items():
        x = float(row["cosine_mean"])
        f1 = row.get("tier0_failure_mode_macro_f1")
        if f1 is None and condition_id in metrics.get("conditions", {}):
            tier0 = _tier0_block(metrics, condition_id)
            f1 = tier0.get("utility", {}).get("failure_mode_macro_f1")
        if f1 is None and condition_id in metrics.get("conditions", {}):
            f1 = _tier1_f1(metrics, condition_id)
        if f1 is None:
            continue
        y = float(f1)
        ax.scatter(
            x,
            y,
            s=70,
            color=_condition_color(condition_id),
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )
        ax.annotate(
            _short_label(condition_id),
            (x, y),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )

    ax.set_xlabel("Embedding retention (cosine mean, raw vs export)")
    ax.set_ylabel(_utility_f1_label(metrics))
    ax.set_title("Retention vs utility (appendix diagnostic)")
    ax.set_xlim(left=-0.02, right=1.05)
    ax.set_ylim(bottom=-0.02, top=1.05)
    return _save(fig, "retention_vs_utility", out_dir)


def _has_transfer(metrics: dict[str, Any], conditions: list[str]) -> bool:
    return any(
        _cond(metrics, cid).get("transfer") for cid in conditions if cid in metrics["conditions"]
    )


def generate_all_figures(
    metrics: dict[str, Any],
    out_dir: Path,
    *,
    analytics_metrics: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Generate Tier-1-forward figures and tables; return stem → path map."""
    outputs: dict[str, Path] = {}
    primary = _primary_conditions(metrics) or FROZEN_LATTICE

    if _has_transfer(metrics, H1_CONDITIONS):
        paths = plot_h1_transfer(metrics, out_dir)
        outputs["h1_transfer_png"] = paths["png"]
        outputs["h1_transfer_pdf"] = paths["pdf"]

    if _has_trial4(metrics) or _has_tier0(metrics, H1_CONDITIONS):
        paths = plot_h1_token_recovery(metrics, out_dir)
        outputs["h1_token_recovery_png"] = paths["png"]
        outputs["h1_token_recovery_pdf"] = paths["pdf"]

    if _has_tier0(metrics, H1_CONDITIONS):
        paths = plot_h1_error_stage_tier0(metrics, out_dir)
        outputs["h1_error_stage_tier0_png"] = paths["png"]
        outputs["h1_error_stage_tier0_pdf"] = paths["pdf"]

    if _has_tier1(metrics, _primary_conditions(metrics) or FROZEN_LATTICE):
        paths = plot_obs_error_stage_tier1(metrics, out_dir)
        outputs["obs_error_stage_tier1_png"] = paths["png"]
        outputs["obs_error_stage_tier1_pdf"] = paths["pdf"]

    h2_paths = plot_h2(metrics, out_dir)
    outputs["h2_png"] = h2_paths["png"]
    outputs["h2_pdf"] = h2_paths["pdf"]

    if _has_trial4(metrics):
        paths = plot_h3(metrics, out_dir)
        outputs["h3_png"] = paths["png"]
        outputs["h3_pdf"] = paths["pdf"]

    if _has_h4_conditions(metrics):
        paths = plot_h4(metrics, out_dir)
        outputs["h4_png"] = paths["png"]
        outputs["h4_pdf"] = paths["pdf"]

    if _has_sensitivity(metrics, conditions=primary):
        try:
            paths = plot_sensitivity(
                metrics, out_dir, analytics_metrics=analytics_metrics
            )
            outputs["sensitivity_png"] = paths["png"]
            outputs["sensitivity_pdf"] = paths["pdf"]
        except ValueError:
            pass

    r4 = write_r4_table(metrics, out_dir)
    outputs["r4_csv"] = r4["csv"]
    outputs["r4_table_png"] = r4["png"]
    outputs["r4_table_pdf"] = r4["pdf"]

    if _has_trial4(metrics):
        paths = plot_adversary_pareto(metrics, out_dir)
        outputs["adversary_pareto_png"] = paths["png"]
        outputs["adversary_pareto_pdf"] = paths["pdf"]
        if _has_trial4_components(metrics):
            paths = plot_adversary_bars(metrics, out_dir)
            outputs["adversary_bars_png"] = paths["png"]
            outputs["adversary_bars_pdf"] = paths["pdf"]

    if _has_tier0(metrics, FROZEN_LATTICE):
        paths = plot_pareto(metrics, out_dir)
        outputs["pareto_png"] = paths["png"]
        outputs["pareto_pdf"] = paths["pdf"]

    return outputs
