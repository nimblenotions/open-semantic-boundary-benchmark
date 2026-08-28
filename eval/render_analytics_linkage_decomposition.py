"""Render purpose-specific linkage Fig 2 pair + obs vs ana comparison (audit only).

Produces two heatmaps (observability surface and analytics surface). Reads
purpose-specific linkage JSON from run_purpose_specific_linkage_audit.py.
Does not modify frozen pilot_v2, camera-ready outputs, or main.tex.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.advisor_figures import (  # noqa: E402
    plot_linkage_decomposition,
    write_linkage_decomposition_table,
)
from eval.observability_task import LLM_TEXT_CONDITIONS, TEXT_CONDITIONS  # noqa: E402
from sbb.config import repo_root  # noqa: E402

AUDIT_SRC = Path("outputs/post_acceptance_experiments/purpose_specific_linkage")
OUT_REL = AUDIT_SRC / "analytics_linkage_decomposition"
TEXT_ARMS = tuple(sorted(TEXT_CONDITIONS | LLM_TEXT_CONDITIONS))
SEMANTIC_ARMS = ("sem_coarse", "sem_medium", "sem_fine")
FROZEN_FIG2_TABLE = Path(
    "outputs/pilot_v2_camera_ready/figures/tables/linkage_decomposition.csv"
)

MAIN_TITLE = (
    "Linkage decomposition: lexical suppression $\\neq$ behavioural privacy"
)

SURFACE_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "observability",
        "linkage_decomposition_observability_surface",
        r"Released surface $z_{c,T_o}$ · observability purpose",
        r"$R(z_{c,T_o})$",
    ),
    (
        "analytics",
        "linkage_decomposition_analytics_surface",
        r"Released surface $z_{c,T_a}$ · analytics purpose",
        r"$R(z_{c,T_a})$",
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metrics_from_linkage_block(block: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "conditions": {
            cid: {"trial4_adversary": trial4} for cid, trial4 in block.items()
        }
    }


def _round4(val: float | None) -> float | str:
    if val is None:
        return ""
    return round(val, 4)


def _comparison_rows(comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in comparison:
        rows.append(
            {
                "condition": rec["condition"],
                "R_obs": _round4(rec["R_obs"]),
                "R_ana": _round4(rec["R_ana"]),
                "delta_R": _round4(rec["delta_R"]),
                "delta_persona": _round4(rec["R_persona_ana"] - rec["R_persona_obs"]),
                "delta_attribute": _round4(rec["R_attr_ana"] - rec["R_attr_obs"]),
                "delta_longitudinal": _round4(rec["R_long_ana"] - rec["R_long_obs"]),
                "delta_token": _round4(
                    (rec.get("token_ana") or 0.0) - (rec.get("token_obs") or 0.0)
                ),
                "R_persona_obs": _round4(rec["R_persona_obs"]),
                "R_persona_ana": _round4(rec["R_persona_ana"]),
                "R_attr_obs": _round4(rec["R_attr_obs"]),
                "R_attr_ana": _round4(rec["R_attr_ana"]),
                "R_long_obs": _round4(rec["R_long_obs"]),
                "R_long_ana": _round4(rec["R_long_ana"]),
                "token_obs": _round4(rec.get("token_obs")),
                "token_ana": _round4(rec.get("token_ana")),
            }
        )
    return rows


def _write_comparison_table(
    rows: list[dict[str, Any]], table_dir: Path
) -> tuple[Path, Path]:
    fieldnames = [
        "condition",
        "R_obs",
        "R_ana",
        "delta_R",
        "delta_persona",
        "delta_attribute",
        "delta_longitudinal",
        "delta_token",
        "R_persona_obs",
        "R_persona_ana",
        "R_attr_obs",
        "R_attr_ana",
        "R_long_obs",
        "R_long_ana",
        "token_obs",
        "token_ana",
    ]
    csv_path = table_dir / "obs_vs_analytics_linkage_comparison.csv"
    json_path = table_dir / "obs_vs_analytics_linkage_comparison.json"
    table_dir.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return csv_path, json_path


def _verify_text_arms(
    comparison_by_cid: dict[str, dict[str, Any]],
    text_z: dict[str, dict[str, Any]],
    sanity: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    all_identical = True
    for cid in TEXT_ARMS:
        comp = comparison_by_cid.get(cid)
        zeq = text_z.get(cid, {})
        san = (sanity.get("conditions") or {}).get(cid, {})
        delta_r = comp["delta_R"] if comp else None
        identical = (
            comp is not None
            and abs(delta_r) < 1e-12
            and zeq.get("z_byte_identical") is True
            and zeq.get("embed_text_identical") is True
            and san.get("persona_equal") is True
            and san.get("attr_equal") is True
            and san.get("long_equal") is True
            and san.get("token_equal") is True
        )
        if not identical:
            all_identical = False
        checks.append(
            {
                "condition": cid,
                "delta_R": delta_r,
                "z_byte_identical": zeq.get("z_byte_identical"),
                "embed_text_identical": zeq.get("embed_text_identical"),
                "linkage_channel_equal": san,
                "obs_ana_identical": identical,
            }
        )
    return {"all_text_arms_identical": all_identical, "conditions": checks}


def _verify_obs_matches_camera_ready(
    obs_metrics: dict[str, Any], root: Path
) -> dict[str, Any]:
    cam_path = root / FROZEN_FIG2_TABLE
    if not cam_path.is_file():
        return {"checked": False, "reason": f"missing {cam_path}"}
    mismatches: list[dict[str, Any]] = []
    for row in csv.DictReader(cam_path.open(encoding="utf-8")):
        cid = row["condition_id"]
        expected_r = float(row["combined_r"])
        actual = obs_metrics["conditions"][cid]["trial4_adversary"][
            "combined_linkage_score"
        ]
        if abs(expected_r - actual) > 1e-4:
            mismatches.append(
                {"condition": cid, "camera_ready": expected_r, "audit_obs": actual}
            )
    return {
        "checked": True,
        "camera_ready_table": str(FROZEN_FIG2_TABLE),
        "matches": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def _report_md(
    verification: dict[str, Any],
    cam_check: dict[str, Any],
    semantic_deltas: list[dict[str, Any]],
    surface_figures: list[dict[str, Any]],
) -> str:
    lines = [
        "# Purpose-specific linkage decomposition (two surfaces)",
        "",
        "Audit artifact only. Paper Fig 2 remains the observability-surface heatmap "
        "under `outputs/pilot_v2_camera_ready/figures/linkage_decomposition.pdf`.",
        "",
        "## Protocol lock",
        "",
        "- Frozen corpus and whole-persona split (unchanged)",
        "- Train-only character n-gram TF-IDF adversary (Trial4 channels)",
        "- Row order: `PRIMARY_LATTICE` (same as camera-ready Fig 2)",
        "- **Two figures:** one per released purpose surface (not per utility task)",
        "",
        "## Figures",
        "",
        "| surface | tasks sharing this \\(R(z_{c,T})\\) | files |",
        "| --- | --- | --- |",
    ]
    for spec in surface_figures:
        lines.append(
            f"| {spec['surface']} | {spec['tasks']} | `{spec['stem']}.{{pdf,png}}` |"
        )
    lines.extend(
        [
            "",
            "## Text / LLM conditions (six arms)",
            "",
        ]
    )
    if verification["all_text_arms_identical"]:
        lines.append(
            "All six text/LLM conditions are **obs–ana identical** for every linkage "
            "channel and combined \\(R(z)\\). Byte-identical \\(z\\) and embed text on the "
            "shared event corpus (`text_z_equality.json`); per-channel equality confirmed "
            "in `text_linkage_sanity.json`."
        )
    else:
        lines.append("**Discrepancies found** among text/LLM arms:")
        for rec in verification["conditions"]:
            if not rec["obs_ana_identical"]:
                lines.append(f"- `{rec['condition']}`: ΔR={rec['delta_R']}")
    lines.extend(
        [
            "",
            "| condition | ΔR | z identical | embed identical |",
            "| --- | ---: | :---: | :---: |",
        ]
    )
    for rec in verification["conditions"]:
        lines.append(
            f"| {rec['condition']} | {rec['delta_R']:.4g} | "
            f"{'✓' if rec['z_byte_identical'] else '✗'} | "
            f"{'✓' if rec['embed_text_identical'] else '✗'} |"
        )
    lines.extend(
        [
            "",
            "## Semantic schema arms (purpose-specific surface)",
            "",
            "Structured analytics exports differ from observability JSON; linkage can diverge:",
            "",
            "| condition | R_obs | R_ana | ΔR | Δpersona | Δattr | Δlong |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for rec in semantic_deltas:
        lines.append(
            f"| {rec['condition']} | {rec['R_obs']} | {rec['R_ana']} | "
            f"{rec['delta_R']} | {rec['delta_persona']} | {rec['delta_attribute']} | "
            f"{rec['delta_longitudinal']} |"
        )
    lines.extend(
        [
            "",
            "## Camera-ready cross-check",
            "",
        ]
    )
    if cam_check.get("matches"):
        lines.append(
            f"Observability figure matches frozen Fig 2 table `{cam_check['camera_ready_table']}`."
        )
    else:
        lines.append(f"Camera-ready check: {json.dumps(cam_check, indent=2)}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = repo_root()
    src_dir = root / AUDIT_SRC
    out_dir = root / OUT_REL
    fig_dir = out_dir / "figures"
    table_dir = out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    for stale in (fig_dir / "per_task", table_dir / "per_task"):
        if stale.is_dir():
            shutil.rmtree(stale)

    linkage_path = src_dir / "linkage_train_only.json"
    comparison_path = src_dir / "linkage_comparison.json"
    text_z_path = src_dir / "text_z_equality.json"
    sanity_path = src_dir / "text_linkage_sanity.json"

    for path in (linkage_path, comparison_path, text_z_path, sanity_path):
        if not path.is_file():
            raise SystemExit(f"Missing prerequisite audit artifact: {path}")

    frozen_hashes = {
        str(p.relative_to(root)): _sha256(p)
        for p in [
            root / "outputs/pilot_v2/metrics.json",
            root / "outputs/pilot_v2/analytics_metrics.json",
            root / FROZEN_FIG2_TABLE,
        ]
        if p.is_file()
    }

    linkage = json.loads(linkage_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    text_z = json.loads(text_z_path.read_text(encoding="utf-8"))
    sanity = json.loads(sanity_path.read_text(encoding="utf-8"))

    obs_metrics = _metrics_from_linkage_block(linkage["observability"])
    ana_metrics = _metrics_from_linkage_block(linkage["analytics"])
    metrics_by_surface = {
        "observability": obs_metrics,
        "analytics": ana_metrics,
    }

    all_figure_paths: dict[str, Path] = {}
    surface_figures: list[dict[str, Any]] = []
    for surface, stem, subtitle, combined_r_label in SURFACE_SPECS:
        paths = plot_linkage_decomposition(
            metrics_by_surface[surface],
            fig_dir,
            suptitle=MAIN_TITLE,
            subtitle=subtitle,
            filename_stem=stem,
            combined_r_label=combined_r_label,
        )
        all_figure_paths.update(paths)
        tasks = (
            "$T_o$-1, $T_o$-2"
            if surface == "observability"
            else "$T_a$-1, $T_a$-2, $T_a$-3, $T_a$-5"
        )
        write_linkage_decomposition_table(
            metrics_by_surface[surface], table_dir / surface
        )
        surface_figures.append(
            {"surface": surface, "stem": stem, "tasks": tasks, "subtitle": subtitle}
        )

    comparison_rows = _comparison_rows(comparison)
    cmp_csv, cmp_json = _write_comparison_table(comparison_rows, table_dir)

    comparison_by_cid = {r["condition"]: r for r in comparison}
    verification = _verify_text_arms(comparison_by_cid, text_z, sanity)
    cam_check = _verify_obs_matches_camera_ready(obs_metrics, root)
    semantic_deltas = [r for r in comparison_rows if r["condition"] in SEMANTIC_ARMS]

    report_path = out_dir / "REPORT.md"
    report_path.write_text(
        _report_md(verification, cam_check, semantic_deltas, surface_figures),
        encoding="utf-8",
    )

    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "note": (
            "Two purpose-surface Fig 2 analogues (observability + analytics); audit-only."
        ),
        "inputs": {
            "linkage_train_only": str(linkage_path.relative_to(root)),
            "linkage_comparison": str(comparison_path.relative_to(root)),
            "text_z_equality": str(text_z_path.relative_to(root)),
            "text_linkage_sanity": str(sanity_path.relative_to(root)),
        },
        "outputs": {
            "surface_figures": surface_figures,
            "figures": {
                k: str(v.relative_to(root)) for k, v in all_figure_paths.items()
            },
            "comparison_csv": str(cmp_csv.relative_to(root)),
            "comparison_json": str(cmp_json.relative_to(root)),
            "report": str(report_path.relative_to(root)),
        },
        "text_arm_verification": verification,
        "camera_ready_obs_check": cam_check,
        "frozen_sha256_before_after": frozen_hashes,
        "do_not_write": [
            "outputs/pilot_v2/**",
            "outputs/pilot_v2_camera_ready/**",
            "paper/**/*.tex",
        ],
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote {out_dir}", file=sys.stderr)
    print(f"Surface figures: {len(surface_figures)}", file=sys.stderr)
    print(
        f"Text arms obs=ana identical: {verification['all_text_arms_identical']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
