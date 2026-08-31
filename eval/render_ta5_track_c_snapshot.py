"""Render Track C (assessor-symmetric Ta-5) charts into a new snapshot.

Writes under outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/.
Does not write frozen pilot_v2 artifacts. Not invoked by make repro-cikm-2026.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.advisor_figures import run_advisor_figures  # noqa: E402
from eval.granular_figures import (  # noqa: E402
    plot_analytics_task_dedicated,
    plot_granularity_per_task,
    plot_task_risk_small_multiples,
)
from eval.operative_selection import (  # noqa: E402
    build_analytics_multi_task_table,
    run_operative_selection,
)
from sbb.config import load_config, repo_root  # noqa: E402

AUDIT_REL = Path("outputs/post_acceptance_experiments/ta5_cohort_audit")
SNAPSHOT_REL = AUDIT_REL / "snapshot_track_c"
PAPER_GRID = (0.40, 0.45, 0.50, 0.55)
SHORT_LABEL = {
    "raw": "raw",
    "redact_bracket": "bracket",
    "redact_tokenize": "tokenize",
    "redact_surrogate": "surrogate",
    "redact_llm_substitute": "llm_sub",
    "redact_llm_rephrase": "llm_reph",
    "sem_coarse": "coarse",
    "sem_medium": "medium",
    "sem_fine": "fine",
}
TABLE3_COLS = [
    ("observability", "T_o-1"),
    ("analytics_med", "T_a-1"),
    ("analytics_side", "T_a-2"),
    ("analytics_adherence", "T_a-3"),
    ("analytics_cohort", "T_a-5"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _patch_analytics_cohort(
    frozen: dict[str, Any], scores: dict[str, float]
) -> dict[str, Any]:
    patched = json.loads(json.dumps(frozen))
    for cid, score in scores.items():
        block = patched["conditions"].setdefault(cid, {})
        tier1c = dict(block.get("tier1_cohort") or {})
        tier1c["cohort_segment_macro_f1"] = score
        tier1c["source"] = "ta5_cohort_audit_track_c"
        tier1c["cohort_mode"] = "assessor_symmetric"
        block["tier1_cohort"] = tier1c
    return patched


def _cell(winner: str | None, utility: float | None) -> str:
    if not winner or utility is None:
        return "—"
    return f"{SHORT_LABEL.get(winner, winner)} ({utility:.2f})"


def _table3_rows(multi: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_r = {float(r["r_max"]): r for r in multi}
    rows = []
    for r in PAPER_GRID:
        src = by_r[r]
        rows.append(
            {
                "r_max": r,
                "T_o-1": _cell(src.get("obs_winner"), src.get("obs_utility")),
                "T_a-1": _cell(src.get("med-class_winner"), src.get("med-class_utility")),
                "T_a-2": _cell(
                    src.get("side-effect_winner"), src.get("side-effect_utility")
                ),
                "T_a-3": _cell(
                    src.get("adherence_winner"), src.get("adherence_utility")
                ),
                "T_a-5": _cell(
                    src.get("cohort segment_winner"),
                    src.get("cohort segment_utility"),
                ),
            }
        )
    return rows


def _table3_tex(rows: list[dict[str, Any]]) -> str:
    lines = [
        r"\begin{tabular}{@{}rlllll@{}}",
        r"\toprule",
        r"$R_{\max}$ & $T_o$-1 & $T_a$-1 & $T_a$-2 & $T_a$-3 & $T_a$-5 \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{row['r_max']:.2f} & {row['T_o-1']} & {row['T_a-1']} & "
            f"{row['T_a-2']} & {row['T_a-3']} & {row['T_a-5']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    return "\n".join(lines)


def _table3_md(rows: list[dict[str, Any]], title: str) -> str:
    lines = [
        f"## {title}",
        "",
        "| $R_{max}$ | $T_o$-1 | $T_a$-1 | $T_a$-2 | $T_a$-3 | $T_a$-5 |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['r_max']:.2f} | {row['T_o-1']} | {row['T_a-1']} | "
            f"{row['T_a-2']} | {row['T_a-3']} | {row['T_a-5']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = repo_root()
    cfg = load_config()
    audit_dir = root / AUDIT_REL
    snap_dir = root / SNAPSHOT_REL
    fig_dir = snap_dir / "figures"
    op_dir = snap_dir / "operative_selection"
    snap_dir.mkdir(parents=True, exist_ok=True)

    frozen_analytics_path = (
        root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2") / "analytics_metrics.json"
    )
    frozen_obs_path = (
        root / cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2") / "metrics.json"
    )
    frozen_hash_before = _sha256(frozen_analytics_path)

    frozen_analytics = json.loads(frozen_analytics_path.read_text(encoding="utf-8"))
    track_c = json.loads((audit_dir / "track_c_scores.json").read_text(encoding="utf-8"))
    scores = {
        cid: rec["track_c_assessor_symmetric"]
        for cid, rec in track_c["conditions"].items()
        if rec.get("status") == "ok"
    }
    patched = _patch_analytics_cohort(frozen_analytics, scores)
    patched_path = snap_dir / "analytics_metrics_track_c.json"
    patched_path.write_text(
        json.dumps(patched, indent=2) + "\n", encoding="utf-8"
    )

    advisor = run_advisor_figures(frozen_obs_path, patched_path, fig_dir)
    obs = json.loads(frozen_obs_path.read_text(encoding="utf-8"))
    dedicated = plot_analytics_task_dedicated(patched, fig_dir)
    granularity = plot_granularity_per_task(obs, patched, fig_dir)
    small_multiples = plot_task_risk_small_multiples(
        obs, patched, fig_dir, purpose_filter="analytics"
    )
    run_operative_selection(obs, patched, cfg, op_dir)
    frozen_op_dir = snap_dir / "operative_selection_frozen_reference"
    run_operative_selection(obs, frozen_analytics, cfg, frozen_op_dir)
    track_c_sel = json.loads((op_dir / "operative_selection.json").read_text(encoding="utf-8"))
    frozen_sel = json.loads(
        (frozen_op_dir / "operative_selection.json").read_text(encoding="utf-8")
    )
    multi = build_analytics_multi_task_table(
        track_c_sel["risk_constrained"], r_subset=list(PAPER_GRID)
    )
    frozen_multi = build_analytics_multi_task_table(
        frozen_sel["risk_constrained"], r_subset=list(PAPER_GRID)
    )
    track_c_rows = _table3_rows(multi)
    frozen_rows = _table3_rows(frozen_multi)
    (snap_dir / "table3_operative_grid_track_c.tex").write_text(
        _table3_tex(track_c_rows), encoding="utf-8"
    )
    (snap_dir / "table3_operative_grid_frozen.tex").write_text(
        _table3_tex(frozen_rows), encoding="utf-8"
    )
    (snap_dir / "table3_operative_grid.json").write_text(
        json.dumps(
            {"frozen": frozen_rows, "track_c": track_c_rows},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # Committed table3_operative_grid.md is the published purpose-specific
    # grid (analytics sem_medium infeasible at 0.50/0.55). This renderer uses
    # shared observability R and must not overwrite that file.

    frozen_hash_after = _sha256(frozen_analytics_path)
    if frozen_hash_after != frozen_hash_before:
        raise SystemExit("Refusing: frozen analytics_metrics.json changed during render")

    figure_paths = {k: str(Path(v).name) for k, v in advisor["figures"].items()}
    figure_paths.update({k: v.name for k, v in dedicated.items()})
    figure_paths.update({f"granularity_{k}": v.name for k, v in granularity.items()})
    figure_paths.update(
        {f"small_multiples_{k}": v.name for k, v in small_multiples.items()}
    )
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "note": "Track C snapshot only. Frozen outputs/pilot_v2/analytics_metrics.json untouched.",
        "frozen_analytics": str(frozen_analytics_path.relative_to(root)),
        "frozen_analytics_sha256": frozen_hash_after,
        "patched_analytics": str(patched_path.relative_to(root)),
        "patched_field": "conditions.*.tier1_cohort.cohort_segment_macro_f1",
        "track_c_scores": str((audit_dir / "track_c_scores.json").relative_to(root)),
        "track_c_scores_used": scores,
        "figures_dir": str(fig_dir.relative_to(root)),
        "operative_dir": str(op_dir.relative_to(root)),
        "paper_maps": {
            "fig3": "utility_matrix_heatmap.pdf (cohort column)",
            "fig4": "cross_purpose_regret_matrix.pdf (cohort row/col at R_max=0.45)",
            "table3": "table3_operative_grid_track_c.tex",
        },
        "advisor": {
            "regret_winners": advisor["regret_winners"],
            "figures": advisor["figures"],
            "tables": advisor["tables"],
        },
        "extra_figures": figure_paths,
        "do_not_write": [
            "outputs/pilot_v2/**",
            "data/eval_cache_analytics/**",
            "paper/**/*.tex",
        ],
    }
    (snap_dir / "SNAPSHOT.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(f"Wrote {snap_dir}", file=sys.stderr)
    print(f"Frozen analytics sha256 unchanged: {frozen_hash_after}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
