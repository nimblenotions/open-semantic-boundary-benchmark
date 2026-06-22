"""Operative selection: risk constraints, dominance, task bundles, decision bundle."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.analytics_task import composite_utility
from eval.figures import PRIMARY_LATTICE

DEFAULT_R_MAX_GRID = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
DEFAULT_PROVENANCE_MIN = 0.9

TASK_BUNDLES: list[dict[str, Any]] = [
    {
        "id": "dual_purpose_balanced",
        "label": "Balanced dual-purpose (obs + med-class under moderate linkage)",
        "constraints": {
            "u_obs_min": 0.60,
            "u_analytics_med_min": 0.50,
            "u_analytics_composite_min": None,
            "linkage_max": 0.50,
            "provenance_min": DEFAULT_PROVENANCE_MIN,
        },
    },
    {
        "id": "strict_linkage",
        "label": "Strict linkage budget (compliance-oriented)",
        "constraints": {
            "u_obs_min": 0.55,
            "u_analytics_med_min": 0.45,
            "u_analytics_composite_min": None,
            "linkage_max": 0.40,
            "provenance_min": DEFAULT_PROVENANCE_MIN,
        },
    },
    {
        "id": "observability_first",
        "label": "Observability-first vendor triage",
        "constraints": {
            "u_obs_min": 0.65,
            "u_analytics_med_min": None,
            "u_analytics_composite_min": None,
            "linkage_max": 0.55,
            "provenance_min": DEFAULT_PROVENANCE_MIN,
        },
    },
    {
        "id": "analytics_med_class",
        "label": "Analytics med-class priority",
        "constraints": {
            "u_obs_min": None,
            "u_analytics_med_min": 0.50,
            "u_analytics_composite_min": None,
            "linkage_max": 0.55,
            "provenance_min": DEFAULT_PROVENANCE_MIN,
        },
    },
    {
        "id": "full_dual_composite",
        "label": "Full dual-purpose composite utility",
        "constraints": {
            "u_obs_min": 0.60,
            "u_analytics_med_min": None,
            "u_analytics_composite_min": 0.65,
            "linkage_max": 0.55,
            "provenance_min": DEFAULT_PROVENANCE_MIN,
        },
    },
]


@dataclass(frozen=True)
class ConditionPoint:
    condition_id: str
    u_obs: float
    u_analytics_med: float
    u_analytics_side: float
    u_analytics_adherence: float
    u_analytics_composite: float
    u_cohort: float
    linkage: float
    provenance_completeness: float
    token_recovery: float
    persona_top1: float


ANALYTICS_PURPOSE_ATTRS = {
    "analytics_med": "u_analytics_med",
    "analytics_side": "u_analytics_side",
    "analytics_adherence": "u_analytics_adherence",
    "analytics_composite": "u_analytics_composite",
    "analytics_cohort": "u_cohort",
}


def _trial4_linkage(obs_metrics: dict[str, Any], condition_id: str) -> float:
    cond = obs_metrics.get("conditions", {}).get(condition_id, {})
    t4 = cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})
    return float(t4.get("combined_linkage_score", t4.get("persona_top1", 0.0)))


def _obs_utility(obs_metrics: dict[str, Any], condition_id: str) -> float:
    cond = obs_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("failure_mode_macro_f1") is not None:
        return float(tier1["failure_mode_macro_f1"])
    return float(cond.get("tier0", {}).get("utility", {}).get("failure_mode_macro_f1", 0.0))


def _analytics_med(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("medication_class_macro_f1") is not None:
        return float(tier1["medication_class_macro_f1"])
    return float(
        cond.get("tier0", {}).get("utility", {}).get("medication_class_macro_f1", 0.0)
    )


def _analytics_composite(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("medication_class_macro_f1") is not None:
        return composite_utility(tier1)
    utility = cond.get("tier0", {}).get("utility", {})
    if utility:
        return composite_utility(utility)
    return float(cond.get("tier0", {}).get("composite_utility", 0.0))


def _analytics_side(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("side_effect_signal_macro_f1") is not None:
        return float(tier1["side_effect_signal_macro_f1"])
    return float(
        cond.get("tier0", {}).get("utility", {}).get("side_effect_signal_macro_f1", 0.0)
    )


def _analytics_adherence(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1 = cond.get("tier1", {})
    if tier1.get("status") == "ok" and tier1.get("adherence_signal_macro_f1") is not None:
        return float(tier1["adherence_signal_macro_f1"])
    return float(
        cond.get("tier0", {}).get("utility", {}).get("adherence_signal_macro_f1", 0.0)
    )


def _cohort_utility(analytics_metrics: dict[str, Any], condition_id: str) -> float:
    cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    tier1c = cond.get("tier1_cohort", {})
    if tier1c.get("cohort_segment_macro_f1") is not None:
        return float(tier1c["cohort_segment_macro_f1"])
    cohort = cond.get("cohort", {})
    return float(cohort.get("cohort_segment_macro_f1", 0.0))


def _utility_for_purpose(point: ConditionPoint, purpose: str) -> float:
    if purpose == "observability":
        return point.u_obs
    attr = ANALYTICS_PURPOSE_ATTRS.get(purpose)
    if attr is None:
        raise ValueError(f"unknown purpose: {purpose}")
    return float(getattr(point, attr))


def build_condition_points(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    *,
    conditions: list[str] | None = None,
) -> list[ConditionPoint]:
    cids = conditions or [
        c
        for c in PRIMARY_LATTICE
        if c in obs_metrics.get("conditions", {})
        and c in analytics_metrics.get("conditions", {})
    ]
    points: list[ConditionPoint] = []
    for cid in cids:
        obs_cond = obs_metrics["conditions"][cid]
        t4 = obs_cond.get("trial4_adversary") or obs_cond.get("tier0", {}).get(
            "trial4_adversary", {}
        )
        points.append(
            ConditionPoint(
                condition_id=cid,
                u_obs=_obs_utility(obs_metrics, cid),
                u_analytics_med=_analytics_med(analytics_metrics, cid),
                u_analytics_side=_analytics_side(analytics_metrics, cid),
                u_analytics_adherence=_analytics_adherence(analytics_metrics, cid),
                u_analytics_composite=_analytics_composite(analytics_metrics, cid),
                u_cohort=_cohort_utility(analytics_metrics, cid),
                linkage=_trial4_linkage(obs_metrics, cid),
                provenance_completeness=float(
                    obs_cond.get("provenance", {}).get("completeness", 0.0)
                ),
                token_recovery=float(t4.get("token_recovery_rate", 0.0)),
                persona_top1=float(t4.get("persona_top1", 0.0)),
            )
        )
    return points


def _dominates(
    a: ConditionPoint,
    b: ConditionPoint,
    *,
    purpose: str,
) -> bool:
    """a Pareto-dominates b on (utility, linkage) for purpose."""
    if purpose == "observability":
        u_a, u_b = a.u_obs, b.u_obs
    elif purpose in ANALYTICS_PURPOSE_ATTRS:
        u_a = _utility_for_purpose(a, purpose)
        u_b = _utility_for_purpose(b, purpose)
    else:
        raise ValueError(f"unknown purpose: {purpose}")

    if u_a < u_b or a.linkage > b.linkage:
        return False
    return u_a > u_b or a.linkage < b.linkage


def risk_constrained_selection(
    points: list[ConditionPoint],
    *,
    purpose: str,
    r_max_grid: list[float] | None = None,
    provenance_min: float = DEFAULT_PROVENANCE_MIN,
) -> list[dict[str, Any]]:
    """For each linkage ceiling, pick argmax utility among feasible conditions."""
    grid = r_max_grid or DEFAULT_R_MAX_GRID
    rows: list[dict[str, Any]] = []
    for r_max in grid:
        feasible = [
            p
            for p in points
            if p.linkage <= r_max + 1e-9 and p.provenance_completeness >= provenance_min
        ]
        if not feasible:
            rows.append(
                {
                    "purpose": purpose,
                    "r_max": r_max,
                    "winner": None,
                    "utility": None,
                    "linkage": None,
                    "n_feasible": 0,
                    "feasible_conditions": [],
                }
            )
            continue

        if purpose == "observability":
            key = lambda p: p.u_obs  # noqa: E731
            util_attr = "u_obs"
        elif purpose in ANALYTICS_PURPOSE_ATTRS:
            util_attr = ANALYTICS_PURPOSE_ATTRS[purpose]
            key = lambda p, a=util_attr: getattr(p, a)  # noqa: E731
        else:
            raise ValueError(f"unknown purpose: {purpose}")

        winner = max(feasible, key=key)
        rows.append(
            {
                "purpose": purpose,
                "r_max": r_max,
                "winner": winner.condition_id,
                "utility": getattr(winner, util_attr),
                "linkage": winner.linkage,
                "n_feasible": len(feasible),
                "feasible_conditions": [p.condition_id for p in feasible],
            }
        )
    return rows


def dominance_analysis(
    points: list[ConditionPoint],
    *,
    purpose: str,
) -> list[dict[str, Any]]:
    """Per condition: dominators, dominated-by count, on_frontier flag."""
    rows: list[dict[str, Any]] = []
    for target in points:
        dominators = [
            p.condition_id
            for p in points
            if p.condition_id != target.condition_id and _dominates(p, target, purpose=purpose)
        ]
        dominates_others = [
            p.condition_id
            for p in points
            if p.condition_id != target.condition_id and _dominates(target, p, purpose=purpose)
        ]
        on_frontier = len(dominators) == 0
        rows.append(
            {
                "purpose": purpose,
                "condition_id": target.condition_id,
                "u_obs": target.u_obs,
                "u_analytics_med": target.u_analytics_med,
                "u_analytics_side": target.u_analytics_side,
                "u_analytics_adherence": target.u_analytics_adherence,
                "u_analytics_composite": target.u_analytics_composite,
                "u_cohort": target.u_cohort,
                "linkage": target.linkage,
                "on_pareto_frontier": on_frontier,
                "dominated_by": dominators,
                "n_dominators": len(dominators),
                "dominates": dominates_others,
                "n_dominated": len(dominates_others),
                "recommend_deploy": on_frontier and len(dominates_others) > 0,
                "never_deploy": len(dominators) > 0 and not on_frontier,
            }
        )
    return rows


def task_bundle_feasibility(
    points: list[ConditionPoint],
    bundles: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Which conditions satisfy multi-constraint task bundles."""
    specs = bundles or TASK_BUNDLES
    rows: list[dict[str, Any]] = []
    for spec in specs:
        c = spec["constraints"]
        feasible: list[str] = []
        for p in points:
            ok = True
            if c.get("u_obs_min") is not None and p.u_obs < c["u_obs_min"]:
                ok = False
            if c.get("u_analytics_med_min") is not None and p.u_analytics_med < c[
                "u_analytics_med_min"
            ]:
                ok = False
            if c.get("u_analytics_composite_min") is not None and p.u_analytics_composite < c[
                "u_analytics_composite_min"
            ]:
                ok = False
            if c.get("linkage_max") is not None and p.linkage > c["linkage_max"]:
                ok = False
            if c.get("provenance_min") is not None and p.provenance_completeness < c[
                "provenance_min"
            ]:
                ok = False
            if ok:
                feasible.append(p.condition_id)

        rows.append(
            {
                "bundle_id": spec["id"],
                "label": spec["label"],
                "constraints": spec["constraints"],
                "feasible_conditions": feasible,
                "n_feasible": len(feasible),
                "empty": len(feasible) == 0,
            }
        )
    return rows


def build_operative_boundary_bundle(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    cfg: dict[str, Any],
    *,
    selection: dict[str, Any],
) -> dict[str, Any]:
    """Decision deliverable: recommendations per perspective + trace."""
    obs_at_045 = [
        r for r in selection["risk_constrained"] if r["purpose"] == "observability" and r["r_max"] == 0.45
    ]
    ana_at_045 = [
        r
        for r in selection["risk_constrained"]
        if r["purpose"] == "analytics_med" and r["r_max"] == 0.45
    ]
    balanced = next(
        (b for b in selection["task_bundles"] if b["bundle_id"] == "dual_purpose_balanced"),
        None,
    )

    obs_winner = obs_at_045[0]["winner"] if obs_at_045 else None
    ana_winner = ana_at_045[0]["winner"] if ana_at_045 else None
    same_recommendation = obs_winner == ana_winner and obs_winner is not None

    dominated_never = [
        r["condition_id"]
        for r in selection["dominance_obs"]
        if r["never_deploy"] or r["n_dominators"] >= 2
    ]
    never_set = set(dominated_never)

    def _pick_from_balanced(feasible: list[str]) -> str:
        """Prefer non-dominated semantic arms over dominated text baselines."""
        viable = [cid for cid in feasible if cid not in never_set]
        pool = viable or list(feasible)
        semantic = [cid for cid in pool if cid.startswith("sem_")]
        if semantic:
            return semantic[0]
        return pool[0]

    if same_recommendation:
        primary_rec = obs_winner
        decision_note = (
            f"At R_max=0.45, observability and analytics med-class agree on `{obs_winner}`."
        )
    elif balanced and balanced["feasible_conditions"]:
        primary_rec = _pick_from_balanced(balanced["feasible_conditions"])
        decision_note = (
            "No single condition wins both purposes at R_max=0.45; "
            f"dual_purpose_balanced bundle feasible set: {balanced['feasible_conditions']}. "
            f"Selected `{primary_rec}` (non-dominated semantic arm when available). "
            "Consider purpose-split exports or pick from bundle."
        )
    else:
        primary_rec = obs_winner or "sem_medium"
        decision_note = (
            "Purpose conflict: different winners under obs vs analytics at R_max=0.45; "
            "dual_purpose_balanced bundle may be empty — use per-purpose registration."
        )

    return {
        "sbb_version": "0.1.1",
        "artifact_type": "operative_boundary_bundle_v0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision_method": "risk_constrained_feasible_set",
        "tier1_model": obs_metrics.get("conditions", {})
        .get("raw", {})
        .get("tier1", {})
        .get("model", "qwen3:8b"),
        "adversary": "trial4_combined_linkage",
        "purposes_registered": [
            {
                "id": cfg.get("study", {}).get("purpose_id", "observability"),
                "consumer_id": cfg.get("study", {}).get("consumer_id", "obs_vendor"),
            },
            {
                "id": analytics_metrics.get("purpose_id", "analytics"),
                "consumer_id": analytics_metrics.get("consumer_id", "analytics_vendor"),
            },
        ],
        "recommended_condition": primary_rec,
        "recommended_condition_rule": decision_note,
        "per_perspective_at_r_max_0_45": {
            "observability": obs_winner,
            "analytics_med_class": ana_winner,
            "same_winner": same_recommendation,
        },
        "task_bundle_dual_purpose_balanced": balanced,
        "conditions_never_deploy_obs": dominated_never,
        "dominated_strategies": {
            "observability": [
                {"condition": r["condition_id"], "dominated_by": r["dominated_by"]}
                for r in selection["dominance_obs"]
                if r["dominated_by"]
            ],
            "analytics_med": [
                {"condition": r["condition_id"], "dominated_by": r["dominated_by"]}
                for r in selection["dominance_analytics_med"]
                if r["dominated_by"]
            ],
        },
        "metrics_ref": {
            "obs": str(
                Path(cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2"))
                / "metrics.json"
            ),
            "analytics": str(
                Path(cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2"))
                / "analytics_metrics.json"
            ),
        },
        "operative_selection_ref": "operative_selection/operative_selection.json",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for k, v in out.items():
                if isinstance(v, list):
                    out[k] = ";".join(str(x) for x in v)
            writer.writerow(out)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


TABLE_R_MAX_SUBSET = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

ANALYTICS_TASK_PURPOSES = [
    ("analytics_med", "med-class"),
    ("analytics_side", "side-effect"),
    ("analytics_adherence", "adherence"),
    ("analytics_cohort", "cohort segment"),
    ("analytics_composite", "composite"),
]


def build_analytics_multi_task_table(
    risk_constrained: list[dict[str, Any]],
    *,
    r_subset: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Pivot risk-constrained rows into one row per ε with all analytics task winners."""
    subset = r_subset or TABLE_R_MAX_SUBSET
    by_purpose: dict[str, dict[float, dict[str, Any]]] = {}
    for purpose, _ in [("observability", "obs")] + ANALYTICS_TASK_PURPOSES:
        by_purpose[purpose] = {
            r["r_max"]: r for r in risk_constrained if r["purpose"] == purpose
        }
    rows: list[dict[str, Any]] = []
    for eps in subset:
        row: dict[str, Any] = {"r_max": eps}
        for purpose, label in [("observability", "obs")] + ANALYTICS_TASK_PURPOSES:
            r = by_purpose[purpose].get(eps, {})
            row[f"{label}_winner"] = r.get("winner")
            row[f"{label}_utility"] = r.get("utility")
        med_w = row.get("med-class_winner")
        side_w = row.get("side-effect_winner")
        adh_w = row.get("adherence_winner")
        row["med_side_adherence_same_winner"] = (
            med_w == side_w == adh_w and med_w is not None
        )
        rows.append(row)
    return rows


def write_analytics_multi_task_artifacts(
    selection: dict[str, Any],
    out_dir: Path,
) -> Path:
    """CSV + markdown snippet for multi-task analytics operative selection."""
    table = build_analytics_multi_task_table(selection["risk_constrained"])
    csv_path = out_dir / "analytics_multi_task_simulation.csv"
    fieldnames = list(table[0].keys()) if table else []
    _write_csv(csv_path, table, fieldnames)

    md_rows = []
    for row in table:
        md_rows.append(
            [
                f"{row['r_max']:.2f}",
                row.get("obs_winner") or "—",
                f"{row.get('med-class_winner') or '—'} ({row.get('med-class_utility'):.3f})"
                if row.get("med-class_utility") is not None
                else (row.get("med-class_winner") or "—"),
                f"{row.get('side-effect_winner') or '—'} ({row.get('side-effect_utility'):.3f})"
                if row.get("side-effect_utility") is not None
                else (row.get("side-effect_winner") or "—"),
                f"{row.get('adherence_winner') or '—'} ({row.get('adherence_utility'):.3f})"
                if row.get("adherence_utility") is not None
                else (row.get("adherence_winner") or "—"),
                f"{row.get('cohort segment_winner') or '—'} ({row.get('cohort segment_utility'):.3f})"
                if row.get("cohort segment_utility") is not None
                else (row.get("cohort segment_winner") or "—"),
            ]
        )

    md_path = out_dir / "analytics_multi_task_simulation.md"
    md_path.write_text(
        "\n".join(
            [
                "# Analytics multi-task operative selection (simulation)",
                "",
                "Risk-constrained winner per registered analytics task at each $R_{max}$.",
                "",
                _markdown_table(
                    [
                        "$R_{max}$",
                        "Obs winner",
                        "Med-class",
                        "Side-effect",
                        "Adherence",
                        "Cohort (Ta-5)",
                    ],
                    md_rows,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return md_path


def write_operative_report(
    selection: dict[str, Any],
    out_path: Path,
) -> Path:
    """Human-readable markdown for paper appendix."""
    rc = selection["risk_constrained"]
    obs_rows = [r for r in rc if r["purpose"] == "observability"]
    ana_rows = [r for r in rc if r["purpose"] == "analytics_med"]

    def _fmt_rc(rows: list[dict[str, Any]]) -> list[list[str]]:
        return [
            [
                f"{r['r_max']:.2f}",
                r["winner"] or "—",
                f"{r['utility']:.3f}" if r["utility"] is not None else "—",
                f"{r['linkage']:.3f}" if r["linkage"] is not None else "—",
                str(r["n_feasible"]),
            ]
            for r in rows
        ]

    dom_obs = selection["dominance_obs"]
    dom_table = [
        [
            r["condition_id"],
            "yes" if r["on_pareto_frontier"] else "no",
            ", ".join(r["dominated_by"]) or "—",
            "yes" if r["never_deploy"] else "no",
        ]
        for r in dom_obs
    ]

    bundle_rows = [
        [
            b["bundle_id"],
            str(b["n_feasible"]),
            ", ".join(b["feasible_conditions"]) or "*(empty)*",
        ]
        for b in selection["task_bundles"]
    ]

    parts = [
        "# Operative selection report — primary analysis",
        "",
        f"Generated: {selection['generated_at_utc']}",
        "",
        "## 1. Risk-constrained selection — observability ($T_o$)",
        "",
        "Choose $\\arg\\max U_{obs}$ subject to $R \\leq R_{\\max}$ and provenance gate.",
        "",
        _markdown_table(
            ["$R_{max}$", "Winner", "$U_{obs}$", "Linkage", "# feasible"],
            _fmt_rc(obs_rows),
        ),
        "",
        "## 2. Risk-constrained selection — analytics med-class ($T_a$)",
        "",
        _markdown_table(
            ["$R_{max}$", "Winner", "$U_{med}$", "Linkage", "# feasible"],
            _fmt_rc(ana_rows),
        ),
        "",
        "## 2b. All analytics tasks at each $R_{max}$ (med / side / adherence / cohort / composite)",
        "",
        _markdown_table(
            [
                "$R_{max}$",
                "Obs",
                "Med-class",
                "Side-effect",
                "Adherence",
                "Cohort",
                "Composite",
            ],
            [
                [
                    f"{row['r_max']:.2f}",
                    row.get("obs_winner") or "—",
                    f"{row.get('med-class_winner') or '—'} ({row.get('med-class_utility'):.2f})"
                    if row.get("med-class_utility") is not None
                    else "—",
                    f"{row.get('side-effect_winner') or '—'} ({row.get('side-effect_utility'):.2f})"
                    if row.get("side-effect_utility") is not None
                    else "—",
                    f"{row.get('adherence_winner') or '—'} ({row.get('adherence_utility'):.2f})"
                    if row.get("adherence_utility") is not None
                    else "—",
                    f"{row.get('cohort segment_winner') or '—'} ({row.get('cohort segment_utility'):.2f})"
                    if row.get("cohort segment_utility") is not None
                    else "—",
                    f"{row.get('composite_winner') or '—'} ({row.get('composite_utility'):.2f})"
                    if row.get("composite_utility") is not None
                    else "—",
                ]
                for row in build_analytics_multi_task_table(rc)
            ],
        ),
        "",
        "See `analytics_multi_task_simulation.csv` for machine-readable export.",
        "",
        "## 3. Pareto dominance — observability",
        "",
        _markdown_table(
            ["Condition", "On frontier", "Dominated by", "Never deploy"],
            dom_table,
        ),
        "",
        "## 4. Task-bundle feasibility",
        "",
        _markdown_table(
            ["Bundle", "# feasible", "Feasible conditions"],
            bundle_rows,
        ),
        "",
        "## 5. Operative boundary bundle summary",
        "",
        f"**Recommended (composite rule):** `{selection['operative_bundle']['recommended_condition']}`",
        "",
        f"> {selection['operative_bundle']['recommended_condition_rule']}",
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path


def run_operative_selection(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    cfg: dict[str, Any],
    out_dir: Path,
    *,
    r_max_grid: list[float] | None = None,
) -> dict[str, Any]:
    """Run operative selection analyses and write artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    points = build_condition_points(obs_metrics, analytics_metrics)

    risk_constrained: list[dict[str, Any]] = []
    analytics_purposes = (
        "observability",
        "analytics_med",
        "analytics_side",
        "analytics_adherence",
        "analytics_composite",
        "analytics_cohort",
    )
    for purpose in analytics_purposes:
        risk_constrained.extend(
            risk_constrained_selection(points, purpose=purpose, r_max_grid=r_max_grid)
        )

    dominance_obs = dominance_analysis(points, purpose="observability")
    dominance_analytics_med = dominance_analysis(points, purpose="analytics_med")
    dominance_analytics_composite = dominance_analysis(points, purpose="analytics_composite")
    bundles = task_bundle_feasibility(points)

    selection_core = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "n_conditions": len(points),
        "condition_points": [asdict(p) for p in points],
        "risk_constrained": risk_constrained,
        "dominance_obs": dominance_obs,
        "dominance_analytics_med": dominance_analytics_med,
        "dominance_analytics_composite": dominance_analytics_composite,
        "task_bundles": bundles,
        "r_max_grid": r_max_grid or DEFAULT_R_MAX_GRID,
        "provenance_min": DEFAULT_PROVENANCE_MIN,
    }

    operative_bundle = build_operative_boundary_bundle(
        obs_metrics, analytics_metrics, cfg, selection=selection_core
    )
    selection_core["operative_bundle"] = operative_bundle

    json_path = out_dir / "operative_selection.json"
    json_path.write_text(json.dumps(selection_core, indent=2) + "\n", encoding="utf-8")

    bundle_path = out_dir / "operative_boundary_bundle_v0.json"
    bundle_path.write_text(json.dumps(operative_bundle, indent=2) + "\n", encoding="utf-8")

    _write_csv(
        out_dir / "risk_constrained.csv",
        risk_constrained,
        [
            "purpose",
            "r_max",
            "winner",
            "utility",
            "linkage",
            "n_feasible",
            "feasible_conditions",
        ],
    )
    _write_csv(
        out_dir / "dominance_obs.csv",
        dominance_obs,
        [
            "condition_id",
            "linkage",
            "u_obs",
            "on_pareto_frontier",
            "dominated_by",
            "never_deploy",
        ],
    )
    _write_csv(
        out_dir / "task_bundles.csv",
        bundles,
        ["bundle_id", "label", "n_feasible", "feasible_conditions", "empty"],
    )

    report_path = write_operative_report(selection_core, out_dir / "operative_selection_report.md")
    analytics_md = write_analytics_multi_task_artifacts(selection_core, out_dir)

    return {
        "out_dir": str(out_dir),
        "json": str(json_path),
        "operative_boundary_bundle": str(bundle_path),
        "report_md": str(report_path),
        "analytics_multi_task_md": str(analytics_md),
    }
