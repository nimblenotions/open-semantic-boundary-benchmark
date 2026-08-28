"""Train-only TF-IDF sensitivity audit for frozen SBB linkage evaluation.

Does not overwrite outputs/pilot_v2. Reuses frozen utility scores; reruns only
the Trial4 linkage suite with tfidf_fit_scope=train_only.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.figures import PRIMARY_LATTICE  # noqa: E402
from eval.operative_selection import (  # noqa: E402
    build_condition_points,
    run_operative_selection,
)
from eval.study import _evaluate_hypotheses, run_study  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402

PAPER_R_MAX = [0.40, 0.45, 0.50, 0.55]
PAPER_PURPOSES = [
    ("observability", "T_o-1"),
    ("analytics_med", "T_a-1"),
    ("analytics_side", "T_a-2"),
    ("analytics_adherence", "T_a-3"),
    ("analytics_cohort", "T_a-5"),
]
CHANNEL_KEYS = (
    "persona_top1",
    "attribute_combined_macro_f1",
    "longitudinal_linkage_auc",
    "token_recovery_rate",
    "combined_linkage_score",
)
DUAL_OBS_MIN = 0.60
DUAL_MED_MIN = 0.50
DEFAULT_OUT_DIR = "outputs/pilot_v2_tfidf_train_only"
FROZEN_PILOT_DIR = "outputs/pilot_v2"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _trial4(metrics: dict[str, Any], condition_id: str) -> dict[str, Any]:
    cond = metrics.get("conditions", {}).get(condition_id, {})
    return cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})


def _f(v: Any) -> float:
    return float(v) if v is not None else 0.0


def _rel_delta(new: float, old: float) -> float | None:
    if old == 0.0:
        return None if new == 0.0 else float("inf") if new > 0 else float("-inf")
    return (new - old) / abs(old)


def _rank_by_r(metrics: dict[str, Any]) -> list[tuple[str, float]]:
    rows = []
    for cid in PRIMARY_LATTICE:
        if cid not in metrics.get("conditions", {}):
            continue
        rows.append((cid, _f(_trial4(metrics, cid).get("combined_linkage_score"))))
    rows.sort(key=lambda x: x[1])
    return rows


def merge_frozen_utility(
    frozen_obs: dict[str, Any],
    linkage_result: dict[str, Any],
) -> dict[str, Any]:
    """Replace only Trial4 linkage; keep frozen utility, provenance, transfer."""
    merged = copy.deepcopy(frozen_obs)
    merged["generated_at_utc"] = datetime.now(UTC).isoformat()
    merged["tier"] = "linkage-sensitivity-tfidf-train-only"
    notes = dict(merged.get("notes") or {})
    notes.update(linkage_result.get("notes") or {})
    notes["utility_source"] = f"{FROZEN_PILOT_DIR}/metrics.json (frozen; not recomputed)"
    notes["analytics_utility_source"] = (
        f"{FROZEN_PILOT_DIR}/analytics_metrics.json (frozen; not recomputed)"
    )
    notes["linkage_source"] = "train-only TF-IDF sensitivity"
    notes["frozen_tfidf_fit_scope"] = "train_test"
    notes["sensitivity_tfidf_fit_scope"] = "train_only"
    merged["notes"] = notes

    for cid, new_cond in linkage_result.get("conditions", {}).items():
        if cid not in merged["conditions"]:
            continue
        t4 = new_cond["trial4_adversary"]
        merged["conditions"][cid]["trial4_adversary"] = t4
        if "tier0" in merged["conditions"][cid]:
            merged["conditions"][cid]["tier0"]["trial4_adversary"] = t4

    primary = {
        cid: m
        for cid, m in merged.get("conditions", {}).items()
        if m.get("role") in ("primary", "frozen")
    }
    if primary:
        merged["hypotheses"] = _evaluate_hypotheses(primary)
    return merged


def identity_checks(
    frozen_obs: dict[str, Any],
    linkage_result: dict[str, Any],
    merged: dict[str, Any],
    splits: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add(
        "split_seed",
        int(splits.get("seed", -1)) == int(cfg["corpus"]["split_seed"]),
        f"splits.json seed={splits.get('seed')} config.split_seed={cfg['corpus']['split_seed']}",
    )
    add(
        "persona_split_ratios",
        cfg["corpus"]["train_ratio"] == 0.70 and cfg["corpus"]["test_ratio"] == 0.20,
        f"train={cfg['corpus']['train_ratio']} val={cfg['corpus']['val_ratio']} "
        f"test={cfg['corpus']['test_ratio']}",
    )
    add(
        "tfidf_fit_scope_sensitivity",
        (linkage_result.get("notes") or {}).get("tfidf_fit_scope") == "train_only",
        str((linkage_result.get("notes") or {}).get("tfidf_fit_scope")),
    )

    for cid in PRIMARY_LATTICE:
        frozen_t4 = _trial4(frozen_obs, cid)
        new_t4 = _trial4(linkage_result, cid)
        merged_t4 = _trial4(merged, cid)
        frozen_cond = frozen_obs["conditions"][cid]
        merged_cond = merged["conditions"][cid]
        add(
            f"{cid}.n_test",
            int(new_t4.get("n_test", -1)) == int(frozen_t4.get("n_test", -2)),
            f"frozen={frozen_t4.get('n_test')} new={new_t4.get('n_test')}",
        )
        add(
            f"{cid}.n_linkage_pairs",
            int(new_t4.get("n_linkage_pairs", -1)) == int(frozen_t4.get("n_linkage_pairs", -2)),
            f"frozen={frozen_t4.get('n_linkage_pairs')} new={new_t4.get('n_linkage_pairs')}",
        )
        add(
            f"{cid}.token_recovery",
            abs(_f(new_t4.get("token_recovery_rate")) - _f(frozen_t4.get("token_recovery_rate")))
            < 1e-12,
            f"frozen={frozen_t4.get('token_recovery_rate')} new={new_t4.get('token_recovery_rate')}",
        )
        add(
            f"{cid}.embedder",
            new_t4.get("embedder") == "tfidf_char_wb",
            str(new_t4.get("embedder")),
        )
        add(
            f"{cid}.fit_scope",
            new_t4.get("tfidf_fit_scope") == "train_only",
            str(new_t4.get("tfidf_fit_scope")),
        )
        add(
            f"{cid}.provenance_preserved",
            frozen_cond.get("provenance") == merged_cond.get("provenance"),
            "frozen provenance copied into merged metrics",
        )
        add(
            f"{cid}.tier1_preserved",
            frozen_cond.get("tier1") == merged_cond.get("tier1"),
            "frozen tier1 utility copied into merged metrics",
        )
        add(
            f"{cid}.merged_uses_new_linkage",
            merged_t4.get("combined_linkage_score") == new_t4.get("combined_linkage_score"),
            "merged trial4 equals sensitivity run",
        )

    return {
        "all_ok": all(c["ok"] for c in checks),
        "n_checks": len(checks),
        "n_failed": sum(1 for c in checks if not c["ok"]),
        "checks": checks,
    }


def linkage_comparison(frozen_obs: dict[str, Any], merged: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    frozen_rank = {cid: i + 1 for i, (cid, _) in enumerate(_rank_by_r(frozen_obs))}
    new_rank = {cid: i + 1 for i, (cid, _) in enumerate(_rank_by_r(merged))}
    for cid in PRIMARY_LATTICE:
        a = _trial4(frozen_obs, cid)
        b = _trial4(merged, cid)
        r_a = _f(a.get("combined_linkage_score"))
        r_b = _f(b.get("combined_linkage_score"))
        rows.append(
            {
                "condition_id": cid,
                "persona_top1_frozen": _f(a.get("persona_top1")),
                "persona_top1_train_only": _f(b.get("persona_top1")),
                "attribute_frozen": _f(a.get("attribute_combined_macro_f1")),
                "attribute_train_only": _f(b.get("attribute_combined_macro_f1")),
                "longitudinal_frozen": _f(a.get("longitudinal_linkage_auc")),
                "longitudinal_train_only": _f(b.get("longitudinal_linkage_auc")),
                "token_recovery_frozen": _f(a.get("token_recovery_rate")),
                "token_recovery_train_only": _f(b.get("token_recovery_rate")),
                "R_frozen": r_a,
                "R_train_only": r_b,
                "R_abs_delta": r_b - r_a,
                "R_rel_delta": _rel_delta(r_b, r_a),
                "rank_frozen": frozen_rank.get(cid),
                "rank_train_only": new_rank.get(cid),
                "rank_change": (new_rank.get(cid) or 0) - (frozen_rank.get(cid) or 0),
                "tfidf_n_fit_docs": b.get("tfidf_n_fit_docs"),
                "tfidf_vocab_size": b.get("tfidf_vocab_size"),
            }
        )
    return {
        "rows": rows,
        "rank_frozen_low_to_high": [cid for cid, _ in _rank_by_r(frozen_obs)],
        "rank_train_only_low_to_high": [cid for cid, _ in _rank_by_r(merged)],
        "order_changed": [cid for cid, _ in _rank_by_r(frozen_obs)]
        != [cid for cid, _ in _rank_by_r(merged)],
    }


def _winners_at(
    selection: dict[str, Any], purpose: str, r_max: float
) -> dict[str, Any] | None:
    for row in selection.get("risk_constrained", []):
        if row["purpose"] == purpose and abs(float(row["r_max"]) - r_max) < 1e-12:
            return row
    return None


def _frontier(selection: dict[str, Any], key: str) -> list[str]:
    return [
        r["condition_id"]
        for r in selection.get(key, [])
        if r.get("on_pareto_frontier")
    ]


def _dual_purpose_at_rmax(points: list[Any], r_max: float) -> dict[str, Any]:
    feasible = [p for p in points if p.linkage <= r_max + 1e-9]
    bundle = [
        p.condition_id
        for p in feasible
        if p.u_obs >= DUAL_OBS_MIN and p.u_analytics_med >= DUAL_MED_MIN
    ]
    return {
        "r_max": r_max,
        "u_obs_min": DUAL_OBS_MIN,
        "u_analytics_med_min": DUAL_MED_MIN,
        "feasible_conditions": [p.condition_id for p in feasible],
        "bundle_ok": bundle,
        "empty": len(bundle) == 0,
    }


def operative_comparison(
    frozen_sel: dict[str, Any],
    new_sel: dict[str, Any],
    frozen_points: list[Any],
    new_points: list[Any],
) -> dict[str, Any]:
    winner_grid: list[dict[str, Any]] = []
    feasible_changes: list[dict[str, Any]] = []
    boundary_crossings: list[dict[str, Any]] = []

    frozen_r = {p.condition_id: p.linkage for p in frozen_points}
    new_r = {p.condition_id: p.linkage for p in new_points}

    for r_max in PAPER_R_MAX:
        for purpose, label in PAPER_PURPOSES:
            a = _winners_at(frozen_sel, purpose, r_max) or {}
            b = _winners_at(new_sel, purpose, r_max) or {}
            winner_grid.append(
                {
                    "r_max": r_max,
                    "purpose": purpose,
                    "label": label,
                    "winner_frozen": a.get("winner"),
                    "winner_train_only": b.get("winner"),
                    "winner_changed": a.get("winner") != b.get("winner"),
                    "feasible_frozen": a.get("feasible_conditions") or [],
                    "feasible_train_only": b.get("feasible_conditions") or [],
                    "n_feasible_frozen": a.get("n_feasible"),
                    "n_feasible_train_only": b.get("n_feasible"),
                }
            )
        a0 = _winners_at(frozen_sel, "observability", r_max) or {}
        b0 = _winners_at(new_sel, "observability", r_max) or {}
        frozen_set = set(a0.get("feasible_conditions") or [])
        new_set = set(b0.get("feasible_conditions") or [])
        feasible_changes.append(
            {
                "r_max": r_max,
                "feasible_frozen": sorted(frozen_set),
                "feasible_train_only": sorted(new_set),
                "entered": sorted(new_set - frozen_set),
                "exited": sorted(frozen_set - new_set),
            }
        )

    for cid in PRIMARY_LATTICE:
        for r_max in PAPER_R_MAX:
            was = frozen_r.get(cid, 1.0) <= r_max + 1e-9
            now = new_r.get(cid, 1.0) <= r_max + 1e-9
            if was != now:
                boundary_crossings.append(
                    {
                        "condition_id": cid,
                        "r_max": r_max,
                        "R_frozen": frozen_r.get(cid),
                        "R_train_only": new_r.get(cid),
                        "direction": "became_feasible" if now else "became_infeasible",
                    }
                )

    dual_frozen = {r: _dual_purpose_at_rmax(frozen_points, r) for r in PAPER_R_MAX}
    dual_new = {r: _dual_purpose_at_rmax(new_points, r) for r in PAPER_R_MAX}

    frozen_bundles = {b["bundle_id"]: b for b in frozen_sel.get("task_bundles", [])}
    new_bundles = {b["bundle_id"]: b for b in new_sel.get("task_bundles", [])}
    bundle_cmp = []
    for bid in frozen_bundles:
        a = frozen_bundles[bid]
        b = new_bundles.get(bid, {})
        bundle_cmp.append(
            {
                "bundle_id": bid,
                "feasible_frozen": a.get("feasible_conditions") or [],
                "feasible_train_only": b.get("feasible_conditions") or [],
                "empty_frozen": a.get("empty"),
                "empty_train_only": b.get("empty"),
                "changed": (a.get("feasible_conditions") or []) != (b.get("feasible_conditions") or []),
            }
        )

    return {
        "winner_grid": winner_grid,
        "feasible_sets": feasible_changes,
        "r_max_boundary_crossings": boundary_crossings,
        "any_winner_changed": any(r["winner_changed"] for r in winner_grid),
        "pareto_obs_frozen": _frontier(frozen_sel, "dominance_obs"),
        "pareto_obs_train_only": _frontier(new_sel, "dominance_obs"),
        "pareto_obs_changed": _frontier(frozen_sel, "dominance_obs")
        != _frontier(new_sel, "dominance_obs"),
        "pareto_med_frozen": _frontier(frozen_sel, "dominance_analytics_med"),
        "pareto_med_train_only": _frontier(new_sel, "dominance_analytics_med"),
        "pareto_med_changed": _frontier(frozen_sel, "dominance_analytics_med")
        != _frontier(new_sel, "dominance_analytics_med"),
        "dual_purpose_paper_floors": {
            "frozen": dual_frozen,
            "train_only": dual_new,
        },
        "task_bundles": bundle_cmp,
    }


def _fmt(v: float | None, digits: int = 3) -> str:
    if v is None:
        return "—"
    if v == float("inf"):
        return "+inf"
    if v == float("-inf"):
        return "-inf"
    return f"{v:.{digits}f}"


def write_report(
    out_path: Path,
    identity: dict[str, Any],
    linkage: dict[str, Any],
    operative: dict[str, Any],
) -> None:
    lines: list[str] = [
        "# Train-only TF-IDF sensitivity audit",
        "",
        "Incorrect fit **A** (superseded): `tfidf_fit_scope=train_test` (vectorizer fit on train + test exports).",
        "Corrected protocol **B**: `tfidf_fit_scope=train_only` (fit on train exports, then transform train and test).",
        "Utility scores, lattice exports, split, and provenance are frozen from `outputs/pilot_v2`.",
        "CIKM uses **B** (`outputs/pilot_v2_camera_ready`). Keep **A** only as an audit copy.",
        "",
        "## Identity checks",
        "",
        f"All checks passed: **{'yes' if identity['all_ok'] else 'NO'}** "
        f"({identity['n_checks'] - identity['n_failed']}/{identity['n_checks']}).",
        "",
    ]
    failed = [c for c in identity["checks"] if not c["ok"]]
    if failed:
        lines.append("Failed checks:")
        for c in failed:
            lines.append(f"- `{c['name']}`: {c['detail']}")
        lines.append("")

    lines += [
        "## Per-condition linkage (A transductive vs B train-only)",
        "",
        "| Condition | Persona A | Persona B | Attr A | Attr B | Long. A | Long. B | Token A | Token B | R(z) A | R(z) B | ΔR | rel Δ | Rank A | Rank B |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in linkage["rows"]:
        lines.append(
            "| {condition_id} | {p_a} | {p_b} | {at_a} | {at_b} | {l_a} | {l_b} | {t_a} | {t_b} | {r_a} | {r_b} | {d} | {rd} | {k_a} | {k_b} |".format(
                condition_id=row["condition_id"],
                p_a=_fmt(row["persona_top1_frozen"]),
                p_b=_fmt(row["persona_top1_train_only"]),
                at_a=_fmt(row["attribute_frozen"]),
                at_b=_fmt(row["attribute_train_only"]),
                l_a=_fmt(row["longitudinal_frozen"]),
                l_b=_fmt(row["longitudinal_train_only"]),
                t_a=_fmt(row["token_recovery_frozen"], 4),
                t_b=_fmt(row["token_recovery_train_only"], 4),
                r_a=_fmt(row["R_frozen"]),
                r_b=_fmt(row["R_train_only"]),
                d=_fmt(row["R_abs_delta"], 4),
                rd=_fmt(row["R_rel_delta"], 3) if row["R_rel_delta"] is not None else "—",
                k_a=row["rank_frozen"],
                k_b=row["rank_train_only"],
            )
        )
    lines += [
        "",
        f"R(z) order frozen (low→high): `{linkage['rank_frozen_low_to_high']}`",
        f"R(z) order train-only (low→high): `{linkage['rank_train_only_low_to_high']}`",
        f"Order changed: **{'yes' if linkage['order_changed'] else 'no'}**",
        "",
        "## Operative selection at reported $R_{\\max}$",
        "",
        "| $R_{\\max}$ | Task | Winner A | Winner B | Changed | Feasible A | Feasible B |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in operative["winner_grid"]:
        lines.append(
            f"| {row['r_max']:.2f} | {row['label']} | {row['winner_frozen'] or '—'} | "
            f"{row['winner_train_only'] or '—'} | {'yes' if row['winner_changed'] else 'no'} | "
            f"{', '.join(row['feasible_frozen']) or '—'} | {', '.join(row['feasible_train_only']) or '—'} |"
        )
    lines += ["", "### $R_{\\max}$ boundary crossings (solely from train-only fitting)", ""]
    if operative["r_max_boundary_crossings"]:
        for x in operative["r_max_boundary_crossings"]:
            lines.append(
                f"- `{x['condition_id']}` at $R_{{\\max}}={x['r_max']:.2f}$: {x['direction']} "
                f"(R A={x['R_frozen']:.4f} → B={x['R_train_only']:.4f})"
            )
    else:
        lines.append("None.")
    lines += [
        "",
        "### Pareto-frontier membership",
        "",
        f"- Observability frozen: `{operative['pareto_obs_frozen']}`",
        f"- Observability train-only: `{operative['pareto_obs_train_only']}` "
        f"(changed: {'yes' if operative['pareto_obs_changed'] else 'no'})",
        f"- Analytics med-class frozen: `{operative['pareto_med_frozen']}`",
        f"- Analytics med-class train-only: `{operative['pareto_med_train_only']}` "
        f"(changed: {'yes' if operative['pareto_med_changed'] else 'no'})",
        "",
        "### Dual-purpose floors (paper: $U_{obs}\\ge 0.60$, $U_{med}\\ge 0.50$)",
        "",
    ]
    for r_max in PAPER_R_MAX:
        a = operative["dual_purpose_paper_floors"]["frozen"][r_max]
        b = operative["dual_purpose_paper_floors"]["train_only"][r_max]
        lines.append(
            f"- $R_{{\\max}}={r_max:.2f}$: frozen bundle `{a['bundle_ok'] or 'empty'}`; "
            f"train-only bundle `{b['bundle_ok'] or 'empty'}`"
        )
    lines += ["", "### Registered task-bundle feasibility (code `TASK_BUNDLES`)", ""]
    for b in operative["task_bundles"]:
        lines.append(
            f"- `{b['bundle_id']}`: frozen `{b['feasible_frozen'] or 'empty'}` → "
            f"train-only `{b['feasible_train_only'] or 'empty'}` "
            f"(changed: {'yes' if b['changed'] else 'no'})"
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train-only TF-IDF linkage sensitivity")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Reuse existing sensitivity metrics_linkage.json and only rebuild comparison",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = copy.deepcopy(load_config(args.config))
    frozen_dir = root / FROZEN_PILOT_DIR
    frozen_metrics_path = frozen_dir / "metrics.json"
    frozen_analytics_path = frozen_dir / "analytics_metrics.json"
    frozen_operative_path = frozen_dir / "operative_selection" / "operative_selection.json"
    out_dir = args.output_dir or (root / DEFAULT_OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    if cfg.get("outputs", {}).get("pilot_dir") != FROZEN_PILOT_DIR:
        print("Refusing to run: frozen config pilot_dir is not outputs/pilot_v2", file=sys.stderr)
        return 1
    if out_dir.resolve() == frozen_dir.resolve():
        print("Refusing to write into frozen outputs/pilot_v2", file=sys.stderr)
        return 1

    frozen_obs = _load_json(frozen_metrics_path)
    frozen_analytics = _load_json(frozen_analytics_path)
    splits = _load_json(root / cfg["paths"]["ground_truth"] / "splits.json")

    cfg["eval"].setdefault("trial4", {})
    cfg["eval"]["trial4"]["tfidf_fit_scope"] = "train_only"
    cfg["outputs"]["pilot_dir"] = str(out_dir.relative_to(root)) if out_dir.is_relative_to(root) else str(out_dir)

    snapshot_dir = out_dir / "config_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "cikm_v0.1.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8"
    )

    linkage_path = out_dir / "metrics_linkage.json"
    if args.skip_run and linkage_path.is_file():
        linkage_result = _load_json(linkage_path)
        print(f"Reusing {linkage_path}", file=sys.stderr)
    else:
        print("Running Trial4 linkage with tfidf_fit_scope=train_only …", file=sys.stderr)
        linkage_result = run_study(cfg, root, tier="linkage")
        linkage_path.write_text(json.dumps(linkage_result, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {linkage_path}", file=sys.stderr)

    merged = merge_frozen_utility(frozen_obs, linkage_result)
    merged_path = out_dir / "metrics.json"
    merged_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    identity = identity_checks(frozen_obs, linkage_result, merged, splits, load_config(args.config))
    (out_dir / "identity_checks.json").write_text(
        json.dumps(identity, indent=2) + "\n", encoding="utf-8"
    )

    linkage = linkage_comparison(frozen_obs, merged)
    (out_dir / "linkage_comparison.json").write_text(
        json.dumps(linkage, indent=2) + "\n", encoding="utf-8"
    )

    op_dir = out_dir / "operative_selection"
    new_op_summary = run_operative_selection(merged, frozen_analytics, cfg, op_dir)
    new_sel = _load_json(Path(new_op_summary["json"]))
    frozen_sel = _load_json(frozen_operative_path)
    frozen_points = build_condition_points(frozen_obs, frozen_analytics)
    new_points = build_condition_points(merged, frozen_analytics)
    operative = operative_comparison(frozen_sel, new_sel, frozen_points, new_points)
    (out_dir / "operative_comparison.json").write_text(
        json.dumps(operative, indent=2) + "\n", encoding="utf-8"
    )

    report_path = out_dir / "tfidf_fit_sensitivity_report.md"
    write_report(report_path, identity, linkage, operative)

    print(json.dumps(
        {
            "output_dir": str(out_dir),
            "identity_all_ok": identity["all_ok"],
            "order_changed": linkage["order_changed"],
            "any_winner_changed": operative["any_winner_changed"],
            "boundary_crossings": operative["r_max_boundary_crossings"],
            "report": str(report_path),
        },
        indent=2,
    ))
    return 0 if identity["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
