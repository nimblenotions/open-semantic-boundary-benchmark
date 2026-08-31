"""Promote train-only TF-IDF linkage into outputs/pilot_v2_camera_ready.

One-shot historical promotion after the train-only audit. Does not overwrite
outputs/pilot_v2 (legacy transductive linkage + frozen utilities). Does not
rerun LLM utility inference or regenerate lattice exports. Reuses linkage
already computed in outputs/pilot_v2_tfidf_train_only.

Not invoked by make repro-cikm-2026. Re-running this can rewrite committed
camera-ready files; writing there requires --force. Do not use it as
ordinary verification.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.advisor_figures import run_advisor_figures  # noqa: E402
from eval.artifact_guard import refuse_committed_write  # noqa: E402
from eval.dual_purpose import run_dual_purpose  # noqa: E402
from eval.figures import PRIMARY_LATTICE  # noqa: E402
from eval.operative_figures import generate_operative_figures  # noqa: E402
from eval.operative_selection import (  # noqa: E402
    build_condition_points,
    run_operative_selection,
)
from sbb.config import load_config, repo_root  # noqa: E402

FROZEN_DIR = "outputs/pilot_v2"
SENSITIVITY_DIR = "outputs/pilot_v2_tfidf_train_only"
TRANSDUCTIVE_ARCHIVE = "outputs/pilot_v2_tfidf_train_test"
PAPER_FIGURE_STEMS = (
    "linkage_decomposition",
    "utility_matrix_heatmap",
    "cross_purpose_regret_matrix",
)
PAPER_R_MAX = (0.40, 0.45, 0.50, 0.55)
EXPECTED_WINNERS_045 = {
    "observability": "redact_bracket",
    "analytics_med": "redact_surrogate",
    "analytics_side": "sem_coarse",
    "analytics_adherence": "sem_coarse",
    "analytics_cohort": "redact_bracket",
}


def _git_hash(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _trial4(metrics: dict[str, Any], cid: str) -> dict[str, Any]:
    cond = metrics.get("conditions", {}).get(cid, {})
    return cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})


def _winner(selection: dict[str, Any], purpose: str, r_max: float) -> str | None:
    for row in selection.get("risk_constrained", []):
        if row["purpose"] == purpose and abs(float(row["r_max"]) - r_max) < 1e-12:
            return row.get("winner")
    return None


def _feasible(selection: dict[str, Any], r_max: float) -> list[str]:
    for row in selection.get("risk_constrained", []):
        if row["purpose"] == "observability" and abs(float(row["r_max"]) - r_max) < 1e-12:
            return list(row.get("feasible_conditions") or [])
    return []


def write_linkage_table(metrics: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ranked = sorted(
        PRIMARY_LATTICE,
        key=lambda cid: float(_trial4(metrics, cid).get("combined_linkage_score", 1.0)),
    )
    for cid in ranked:
        t4 = _trial4(metrics, cid)
        rows.append(
            {
                "condition_id": cid,
                "persona_top1": float(t4.get("persona_top1", 0.0)),
                "attribute_combined_macro_f1": float(t4.get("attribute_combined_macro_f1", 0.0)),
                "longitudinal_linkage_auc": float(t4.get("longitudinal_linkage_auc", 0.0)),
                "token_recovery_rate": float(t4.get("token_recovery_rate", 0.0)),
                "combined_linkage_score": float(t4.get("combined_linkage_score", 0.0)),
                "tfidf_fit_scope": t4.get("tfidf_fit_scope"),
                "tfidf_n_fit_docs": t4.get("tfidf_n_fit_docs"),
                "tfidf_vocab_size": t4.get("tfidf_vocab_size"),
                "n_train": t4.get("n_train"),
                "n_test": t4.get("n_test"),
                "n_linkage_pairs": t4.get("n_linkage_pairs"),
                "embedder": t4.get("embedder"),
            }
        )
    path.write_text(json.dumps({"rank_low_to_high": ranked, "rows": rows}, indent=2) + "\n")
    return rows


def verify_operative(selection: dict[str, Any], frozen_sel: dict[str, Any]) -> dict[str, Any]:
    winners_045 = {
        purpose: _winner(selection, purpose, 0.45) for purpose in EXPECTED_WINNERS_045
    }
    winner_ok = winners_045 == EXPECTED_WINNERS_045
    crossings = []
    for r_max in PAPER_R_MAX:
        a = set(_feasible(frozen_sel, r_max))
        b = set(_feasible(selection, r_max))
        if a != b:
            crossings.append(
                {
                    "r_max": r_max,
                    "entered": sorted(b - a),
                    "exited": sorted(a - b),
                }
            )
    pareto_obs_a = [
        r["condition_id"]
        for r in frozen_sel.get("dominance_obs", [])
        if r.get("on_pareto_frontier")
    ]
    pareto_obs_b = [
        r["condition_id"]
        for r in selection.get("dominance_obs", [])
        if r.get("on_pareto_frontier")
    ]
    dual_a = next(
        (b for b in frozen_sel.get("task_bundles", []) if b["bundle_id"] == "dual_purpose_balanced"),
        {},
    )
    dual_b = next(
        (b for b in selection.get("task_bundles", []) if b["bundle_id"] == "dual_purpose_balanced"),
        {},
    )
    return {
        "winners_at_0_45": winners_045,
        "winners_match_paper_table": winner_ok,
        "r_max_boundary_crossings_vs_transductive": crossings,
        "pareto_obs_unchanged": pareto_obs_a == pareto_obs_b,
        "pareto_obs": pareto_obs_b,
        "dual_purpose_balanced_unchanged": (dual_a.get("feasible_conditions") or [])
        == (dual_b.get("feasible_conditions") or []),
        "dual_purpose_balanced": dual_b.get("feasible_conditions") or [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote train-only TF-IDF to camera-ready outputs")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Camera-ready directory (default: config outputs.camera_ready_dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into committed camera-ready artifacts",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    frozen = root / FROZEN_DIR
    sensitivity = root / SENSITIVITY_DIR
    archive = root / TRANSDUCTIVE_ARCHIVE
    camera = args.output or (
        root / cfg.get("outputs", {}).get("camera_ready_dir", "outputs/pilot_v2_camera_ready")
    )
    if not camera.is_absolute():
        camera = root / camera
    blocked = refuse_committed_write(root, camera, force=args.force)
    if blocked:
        print(blocked, file=sys.stderr)
        return 2

    frozen_metrics = frozen / "metrics.json"
    frozen_analytics = frozen / "analytics_metrics.json"
    sensitivity_metrics = sensitivity / "metrics.json"
    for required in (frozen_metrics, frozen_analytics, sensitivity_metrics):
        if not required.is_file():
            print(f"Missing required artifact: {required}", file=sys.stderr)
            return 1

    trial4_cfg = (cfg.get("eval") or {}).get("trial4") or {}
    scope = str(trial4_cfg.get("tfidf_fit_scope", "")).strip()
    if scope != "train_only":
        print(f"Refusing: config tfidf_fit_scope={scope!r}, expected 'train_only'", file=sys.stderr)
        return 1

    camera.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    if not (archive / "metrics.json").is_file():
        shutil.copy2(frozen_metrics, archive / "metrics.json")
    (archive / "README.md").write_text(
        "\n".join(
            [
                "# Historical train-and-test TF-IDF fit (provenance only)",
                "",
                "Copy of `outputs/pilot_v2/metrics.json` from an earlier development run",
                "in which `TfidfVectorizer` was fitted on train and test export strings",
                "(`tfidf_fit_scope=train_test`). Keep these numbers only for comparison.",
                "",
                "Do not use these linkage scores as the published result. The CIKM",
                "result snapshot is `outputs/pilot_v2_camera_ready` with",
                "`tfidf_fit_scope=train_only`. The citeable artifact is",
                "`releases/cikm-2026/`.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    shutil.copy2(sensitivity_metrics, camera / "metrics.json")
    shutil.copy2(frozen_analytics, camera / "analytics_metrics.json")
    if (sensitivity / "metrics_linkage.json").is_file():
        shutil.copy2(sensitivity / "metrics_linkage.json", camera / "metrics_linkage.json")

    obs = json.loads((camera / "metrics.json").read_text(encoding="utf-8"))
    notes = dict(obs.get("notes") or {})
    notes.update(
        {
            "canonical_paper_protocol": True,
            "tfidf_fit_scope": "train_only",
            "utility_source": f"{FROZEN_DIR}/metrics.json and analytics_metrics.json (frozen; not recomputed)",
            "linkage_source": f"{SENSITIVITY_DIR}/metrics.json",
            "transductive_archive": f"{TRANSDUCTIVE_ARCHIVE}/metrics.json",
            "no_llm_rerun": True,
            "no_lattice_regeneration": True,
        }
    )
    obs["notes"] = notes
    obs["tier"] = "camera-ready-tfidf-train-only"
    obs["generated_at_utc"] = datetime.now(UTC).isoformat()
    (camera / "metrics.json").write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")

    snapshot_dir = camera / "config_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    camera_cfg = dict(cfg)
    camera_cfg.setdefault("outputs", {})["pilot_dir"] = str(camera.relative_to(root))
    (snapshot_dir / "cikm_v0.1.yaml").write_text(
        yaml.safe_dump(camera_cfg, sort_keys=False), encoding="utf-8"
    )

    fig_dir = camera / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    advisor = run_advisor_figures(
        camera / "metrics.json",
        camera / "analytics_metrics.json",
        fig_dir,
    )
    dual = run_dual_purpose(
        camera / "metrics.json",
        camera / "analytics_metrics.json",
        fig_dir,
    )
    op_dir = camera / "operative_selection"
    op_summary = run_operative_selection(
        obs,
        json.loads((camera / "analytics_metrics.json").read_text(encoding="utf-8")),
        cfg,
        op_dir,
    )
    op_figs = generate_operative_figures(
        obs,
        json.loads((camera / "analytics_metrics.json").read_text(encoding="utf-8")),
        op_dir,
    )
    new_sel = json.loads(Path(op_summary["json"]).read_text(encoding="utf-8"))
    frozen_sel = json.loads(
        (frozen / "operative_selection" / "operative_selection.json").read_text(encoding="utf-8")
    )
    verification = verify_operative(new_sel, frozen_sel)

    points = build_condition_points(
        obs, json.loads((camera / "analytics_metrics.json").read_text(encoding="utf-8"))
    )
    dual_045 = [
        p.condition_id
        for p in points
        if p.linkage <= 0.45 + 1e-9 and p.u_obs >= 0.60 and p.u_analytics_med >= 0.50
    ]
    verification["dual_purpose_floors_at_0_45"] = dual_045
    verification["dual_purpose_empty_at_0_45"] = dual_045 == []

    tokenize = _trial4(obs, "redact_tokenize")
    verification["red_tokenize"] = {
        "token_recovery_rate": float(tokenize.get("token_recovery_rate", 0.0)),
        "persona_top1": float(tokenize.get("persona_top1", 0.0)),
        "near_zero_token_high_persona": float(tokenize.get("token_recovery_rate", 1.0)) < 0.01
        and float(tokenize.get("persona_top1", 0.0)) >= 0.80,
    }

    rows = write_linkage_table(obs, camera / "linkage_table.json")
    protocol = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_hash(root),
        "tfidf_fit_scope": "train_only",
        "tfidf_analyzer": "char_wb",
        "tfidf_ngram_range": [1, 3],
        "tfidf_max_features": 5000,
        "split_seed": int(cfg["corpus"]["split_seed"]),
        "train_ratio": cfg["corpus"]["train_ratio"],
        "val_ratio": cfg["corpus"]["val_ratio"],
        "test_ratio": cfg["corpus"]["test_ratio"],
        "eval_seed": int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42)),
        "no_llm_rerun": True,
        "no_lattice_regeneration": True,
        "source_paths": {
            "legacy_transductive_metrics": str(frozen_metrics.relative_to(root)),
            "transductive_archive": str((archive / "metrics.json").relative_to(root)),
            "train_only_sensitivity": str(sensitivity_metrics.relative_to(root)),
            "frozen_analytics_utility": str(frozen_analytics.relative_to(root)),
            "camera_ready_metrics": str((camera / "metrics.json").relative_to(root)),
        },
        "paper_figures": {
            stem: {
                "pdf": str((fig_dir / f"{stem}.pdf").relative_to(root)),
                "png": str((fig_dir / f"{stem}.png").relative_to(root)),
            }
            for stem in PAPER_FIGURE_STEMS
        },
        "advisor_figures": advisor.get("figures", {}),
        "dual_purpose_figures": dual.get("figures", {}),
        "operative_selection": op_summary,
        "operative_figures": {k: str(v) for k, v in op_figs.items()},
        "verification": verification,
        "rank_low_to_high": [r["condition_id"] for r in rows],
    }
    (camera / "CAMERA_READY_PROTOCOL.json").write_text(
        json.dumps(protocol, indent=2) + "\n", encoding="utf-8"
    )
    figures_manifest = {
        "cikm_paper_protocol": True,
        "tfidf_fit_scope": "train_only",
        "metrics": str((camera / "metrics.json").relative_to(root)),
        "analytics_metrics": str((camera / "analytics_metrics.json").relative_to(root)),
        "figures_dir": str(fig_dir.relative_to(root)),
        "legacy_transductive_metrics": str(frozen_metrics.relative_to(root)),
        "transductive_archive": str((archive / "metrics.json").relative_to(root)),
        "paper_figures": protocol["paper_figures"],
        "note": (
            "CIKM Figs. 2–4. Do not use outputs/pilot_v2/figures for those three "
            "plots (legacy transductive TF-IDF). Rebuild: make camera-ready-linkage."
        ),
    }
    (camera / "figures_manifest.json").write_text(
        json.dumps(figures_manifest, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# CIKM 2026 result snapshot",
        "",
        f"Generated: {protocol['generated_at_utc']}",
        f"Git commit: `{protocol['git_commit']}`",
        "",
        "This directory is the result snapshot underlying the CIKM 2026 paper.",
        "The citeable protocol, Table 3 excerpt, and Figures 2–4 live under",
        "`releases/cikm-2026/`.",
        "",
        "The snapshot uses train-only TF-IDF fitting as specified by the published",
        "protocol. Utility scores were copied from the historical development",
        "snapshot under `outputs/pilot_v2/` and were not recomputed with new LLM",
        "inference. Earlier development runs that fitted TF-IDF on train and test",
        "together are retained separately for provenance and are not part of the",
        "published result set.",
        "",
        "## Paper figures",
        "",
    ]
    for stem in PAPER_FIGURE_STEMS:
        md_lines.append(f"- `{fig_dir.relative_to(root) / f'{stem}.pdf'}`")
    md_lines += [
        "",
        "## Operative verification",
        "",
        f"- Table 3 winners at 0.45 match paper: **{verification['winners_match_paper_table']}**",
        f"- R_max boundary crossings vs transductive: `{verification['r_max_boundary_crossings_vs_transductive'] or 'none'}`",
        f"- Dual-purpose floors empty at 0.45: **{verification['dual_purpose_empty_at_0_45']}**",
        f"- `red_tokenize` near-zero token / high persona: **{verification['red_tokenize']['near_zero_token_high_persona']}** "
        f"(token={verification['red_tokenize']['token_recovery_rate']:.4f}, "
        f"persona={verification['red_tokenize']['persona_top1']:.3f})",
        "",
    ]
    (camera / "CAMERA_READY_PROTOCOL.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(json.dumps(
        {
            "camera_ready_dir": str(camera),
            "git_commit": protocol["git_commit"],
            "verification": verification,
            "paper_figures": protocol["paper_figures"],
        },
        indent=2,
    ))
    return 0 if verification["winners_match_paper_table"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
