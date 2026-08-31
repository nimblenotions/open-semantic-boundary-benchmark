"""Purpose-specific linkage audit (post-acceptance).

Writes only under outputs/post_acceptance_experiments/purpose_specific_linkage/.
Does not modify pilot_v2, policies, schemas, transforms, caches, or
releases/cikm-2026/.

Fits Trial4 TF-IDF on training export strings only (paper_protocol.linkage.fit
= train_only) and scores observability and analytics surfaces separately.
Not invoked by make repro-cikm-2026.

make eval / run_obs_study.py is a separate historical study runner. With the
current config it also defaults to train_only, but it is not the published
verification path and it refuses to overwrite transductive pilot_v2 linkage.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eval.adversary_trial4 import (  # noqa: E402
    evaluate_trial4_adversary,
    train_only_tfidf_embedder,
)
from dataclasses import dataclass  # noqa: E402

from eval.export_text import export_text_for_embedding  # noqa: E402
from eval.io import join_eval_rows, load_labels, load_splits  # noqa: E402
from eval.observability_task import LLM_TEXT_CONDITIONS, TEXT_CONDITIONS  # noqa: E402
from eval.operative_selection import (  # noqa: E402
    ANALYTICS_PURPOSE_ATTRS,
    ConditionPoint,
    DEFAULT_PROVENANCE_MIN,
    TASK_BUNDLES,
    risk_constrained_selection,
)
from eval.paper_protocol import (  # noqa: E402
    frozen_pilot_dir,
    paper_protocol,
    purpose_specific_output_dir,
    tfidf_params,
    track_c_scores_path,
)
from eval.study import resolve_eval_conditions  # noqa: E402
from sbb.config import load_config, repo_root  # noqa: E402
from transform.io import load_condition_exports, load_jsonl  # noqa: E402

R_MAX_GRID = (0.40, 0.45, 0.50, 0.55)
FOCAL_R_MAX = 0.45
TEXT_ARMS = tuple(TEXT_CONDITIONS | LLM_TEXT_CONDITIONS)
SEMANTIC_ARMS = ("sem_coarse", "sem_medium", "sem_fine")
@dataclass(frozen=True)
class _ScatterPoint:
    cid: str
    x: float
    y: float


def _pareto_frontier_ids(points: list[_ScatterPoint]) -> set[str]:
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


PERSONA_ATTR_FLAGS = {
    "cohort_segment",
    "engagement_trend",
    "occupation_sector",
    "specific_medication",
    "quasi_id",
    "time_bucket",
    "failure_mode",
    "medication_class",
    "symptoms",
    "symptom_categories",
}


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _git_meta(root: Path) -> dict[str, str]:
    def _run(args: list[str]) -> str:
        try:
            return subprocess.check_output(
                args, cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "commit_short": _run(["git", "rev-parse", "--short", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "status_short": _run(["git", "status", "-sb"]),
    }


def _load_raw(root: Path, cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")
    return {row["event_id"]: row for row in rows}


def _z_keys(exports: dict[str, dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for rec in exports.values():
        keys.update(rec.get("z", {}))
    return sorted(keys)


def _run_train_only_trial4(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    seed: int,
    tfidf: dict[str, Any],
) -> dict[str, Any]:
    embedder = train_only_tfidf_embedder(
        train_rows,
        max_features=int(tfidf["max_features"]),
        ngram_range=tuple(tfidf["ngram_range"]),
        analyzer=str(tfidf["analyzer"]),
    )
    result = evaluate_trial4_adversary(
        train_rows,
        test_rows,
        raw_by_id,
        persona_table,
        embedder=embedder,
        seed=seed,
    )
    result["tfidf_fit"] = "train_only"
    result["n_train_fit_docs"] = len(train_rows)
    return result


def _compare_text_z(
    obs_exports: dict[str, dict[str, Any]],
    ana_exports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    obs_ids = set(obs_exports)
    ana_ids = set(ana_exports)
    n_z_equal = 0
    n_embed_equal = 0
    n_r_equal = 0
    first_z_diff = None
    first_embed_diff = None
    r_key_diffs: set[str] = set()
    for eid in sorted(obs_ids & ana_ids):
        oz, az = obs_exports[eid]["z"], ana_exports[eid]["z"]
        z_eq = json.dumps(oz, sort_keys=True) == json.dumps(az, sort_keys=True)
        n_z_equal += int(z_eq)
        if not z_eq and first_z_diff is None:
            first_z_diff = {
                "event_id": eid,
                "obs_z": oz,
                "ana_z": az,
            }
        o_txt = export_text_for_embedding(obs_exports[eid])
        a_txt = export_text_for_embedding(ana_exports[eid])
        e_eq = o_txt == a_txt
        n_embed_equal += int(e_eq)
        if not e_eq and first_embed_diff is None:
            first_embed_diff = {"event_id": eid, "obs": o_txt[:200], "ana": a_txt[:200]}
        or_, ar_ = obs_exports[eid].get("r", {}), ana_exports[eid].get("r", {})
        if or_ == ar_:
            n_r_equal += 1
        else:
            for k in set(or_) | set(ar_):
                if or_.get(k) != ar_.get(k):
                    r_key_diffs.add(k)
    n = len(obs_ids & ana_ids)
    return {
        "n_shared_events": n,
        "n_obs_only": len(obs_ids - ana_ids),
        "n_ana_only": len(ana_ids - obs_ids),
        "n_z_equal": n_z_equal,
        "n_embed_text_equal": n_embed_equal,
        "n_r_equal": n_r_equal,
        "z_byte_identical": n_z_equal == n and n > 0,
        "embed_text_identical": n_embed_equal == n and n > 0,
        "r_differing_keys": sorted(r_key_diffs),
        "first_z_diff": first_z_diff,
        "first_embed_diff": first_embed_diff,
    }


def _schema_compare(
    obs_exports: dict[str, dict[str, Any]],
    ana_exports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    obs_k, ana_k = set(_z_keys(obs_exports)), set(_z_keys(ana_exports))
    return {
        "obs_fields": sorted(obs_k),
        "ana_fields": sorted(ana_k),
        "common_fields": sorted(obs_k & ana_k),
        "obs_only_fields": sorted(obs_k - ana_k),
        "ana_only_fields": sorted(ana_k - obs_k),
        "persona_attr_flags": sorted((obs_k | ana_k) & PERSONA_ATTR_FLAGS),
        "releases_cohort_segment": "cohort_segment" in ana_k,
    }


def _frozen_t4(obs_metrics: dict[str, Any], cid: str) -> dict[str, Any]:
    cond = obs_metrics["conditions"][cid]
    return cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})


def _u_obs(obs_metrics: dict[str, Any], cid: str) -> float:
    return float(
        obs_metrics["conditions"][cid]["tier1"]["failure_mode_macro_f1"]
    )


def _u_obs_stage(obs_metrics: dict[str, Any], cid: str) -> float:
    return float(obs_metrics["conditions"][cid]["tier1"]["error_stage_accuracy"])


def _u_ana(analytics: dict[str, Any], cid: str, key: str) -> float:
    return float(analytics["conditions"][cid]["tier1"][key])


def _make_points(
    cids: list[str],
    *,
    obs_metrics: dict[str, Any],
    analytics: dict[str, Any],
    track_c: dict[str, Any],
    linkage_by_cid: dict[str, float],
) -> list[ConditionPoint]:
    points: list[ConditionPoint] = []
    for cid in cids:
        t4 = _frozen_t4(obs_metrics, cid)
        obs_cond = obs_metrics["conditions"][cid]
        points.append(
            ConditionPoint(
                condition_id=cid,
                u_obs=_u_obs(obs_metrics, cid),
                u_analytics_med=_u_ana(analytics, cid, "medication_class_macro_f1"),
                u_analytics_side=_u_ana(analytics, cid, "side_effect_signal_macro_f1"),
                u_analytics_adherence=_u_ana(
                    analytics, cid, "adherence_signal_macro_f1"
                ),
                u_analytics_composite=float(
                    (
                        _u_ana(analytics, cid, "medication_class_macro_f1")
                        + _u_ana(analytics, cid, "side_effect_signal_macro_f1")
                        + _u_ana(analytics, cid, "adherence_signal_macro_f1")
                    )
                    / 3.0
                ),
                u_cohort=float(
                    track_c["conditions"][cid]["track_c_assessor_symmetric"]
                ),
                linkage=float(linkage_by_cid[cid]),
                provenance_completeness=float(
                    obs_cond.get("provenance", {}).get("completeness", 1.0)
                ),
                token_recovery=float(t4.get("token_recovery_rate", 0.0)),
                persona_top1=float(t4.get("persona_top1", 0.0)),
            )
        )
    return points


def _winners_table(
    points: list[ConditionPoint], purposes: list[str]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for r_max in R_MAX_GRID:
        row: dict[str, Any] = {"r_max": r_max}
        for purpose in purposes:
            sel = risk_constrained_selection(
                points, purpose=purpose, r_max_grid=[r_max]
            )[0]
            row[purpose] = sel
        out[str(r_max)] = row
    return out


def _feasible_ids(points: list[ConditionPoint], r_max: float) -> list[str]:
    return [
        p.condition_id
        for p in points
        if p.linkage <= r_max + 1e-9
        and p.provenance_completeness >= DEFAULT_PROVENANCE_MIN
    ]


def _pareto_for_purpose(points: list[ConditionPoint], purpose: str) -> list[str]:
    scatter: list[_ScatterPoint] = []
    for p in points:
        if purpose == "observability":
            y = p.u_obs
        else:
            y = float(getattr(p, ANALYTICS_PURPOSE_ATTRS[purpose]))
        scatter.append(_ScatterPoint(cid=p.condition_id, x=p.linkage, y=y))
    return sorted(_pareto_frontier_ids(scatter))


def _error_stage_winner(
    obs_metrics: dict[str, Any],
    linkage_by_cid: dict[str, float],
    cids: list[str],
    r_max: float,
) -> dict[str, Any]:
    feasible = [
        cid
        for cid in cids
        if linkage_by_cid[cid] <= r_max + 1e-9
    ]
    if not feasible:
        return {"winner": None, "utility": None, "feasible": []}
    winner = max(feasible, key=lambda c: _u_obs_stage(obs_metrics, c))
    return {
        "winner": winner,
        "utility": _u_obs_stage(obs_metrics, winner),
        "feasible": feasible,
    }


def _purpose_specific_regret(
    obs_points: list[ConditionPoint],
    ana_points: list[ConditionPoint],
    *,
    r_max: float,
) -> dict[str, Any]:
    """Regret when forcing one condition ID across purposes.

    Existing formula (advisor_figures) uses a *shared* feasible set. That is
    not well-defined once R is purpose-specific. This formulation:

    * winner_T = argmax U(T) among c with R(z_{c,T}) <= R_max
    * forcing winner_i onto purpose j is infeasible if R(z_{c_i, T_j}) > R_max
    * otherwise regret = U_j(winner_j) - U_j(c_i)
    """
    obs_by = {p.condition_id: p for p in obs_points}
    ana_by = {p.condition_id: p for p in ana_points}
    purposes = [
        ("observability", "observability", obs_points, obs_by),
        ("analytics_med", "analytics", ana_points, ana_by),
        ("analytics_side", "analytics", ana_points, ana_by),
        ("analytics_adherence", "analytics", ana_points, ana_by),
        ("analytics_cohort", "analytics", ana_points, ana_by),
    ]
    winners: dict[str, str | None] = {}
    for name, _surf, pts, _by in purposes:
        sel = risk_constrained_selection(pts, purpose=name, r_max_grid=[r_max])[0]
        winners[name] = sel["winner"]

    matrix: list[list[Any]] = []
    notes: list[dict[str, Any]] = []
    names = [p[0] for p in purposes]
    for i, (name_i, _s_i, _pts_i, by_i) in enumerate(purposes):
        row: list[Any] = []
        c_i = winners[name_i]
        for j, (name_j, surf_j, pts_j, by_j) in enumerate(purposes):
            c_j = winners[name_j]
            if not c_i or not c_j:
                row.append(None)
                continue
            # Feasibility of c_i under purpose j's R surface.
            r_j = by_j[c_i].linkage
            feasible_j = r_j <= r_max + 1e-9
            u_star = getattr(
                by_j[c_j],
                "u_obs" if name_j == "observability" else ANALYTICS_PURPOSE_ATTRS[name_j],
            )
            u_forced = getattr(
                by_j[c_i],
                "u_obs" if name_j == "observability" else ANALYTICS_PURPOSE_ATTRS[name_j],
            )
            if not feasible_j:
                row.append("infeasible")
                notes.append(
                    {
                        "row": name_i,
                        "col": name_j,
                        "forced_condition": c_i,
                        "r_on_col_surface": r_j,
                        "r_max": r_max,
                    }
                )
            else:
                row.append(float(u_star) - float(u_forced))
        matrix.append(row)
    return {
        "r_max": r_max,
        "formula_note": (
            "Existing shared-R regret assumes one feasible set. Purpose-specific "
            "R splits feasibility; forced reuse is marked infeasible when the "
            "same condition ID fails the destination purpose's R constraint."
        ),
        "purposes": names,
        "winners": winners,
        "regret_or_infeasible": matrix,
        "infeasible_reuses": notes,
        "legacy_shared_r_assumption": "not reused",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Purpose-specific linkage audit (no frozen writes)"
    )
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    root = repo_root()
    cfg = load_config(args.config)
    proto = paper_protocol(cfg)
    tfidf = tfidf_params(cfg)
    if tfidf["fit"] != "train_only":
        raise ValueError(
            f"paper_protocol.linkage.fit must be train_only, got {tfidf['fit']}"
        )
    out_dir = purpose_specific_output_dir(cfg, root)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42))
    pilot_dir = frozen_pilot_dir(cfg, root)
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    raw_by_id = _load_raw(root, cfg)
    obs_metrics = json.loads((pilot_dir / "metrics.json").read_text(encoding="utf-8"))
    analytics_metrics = json.loads(
        (pilot_dir / "analytics_metrics.json").read_text(encoding="utf-8")
    )
    track_c = json.loads(track_c_scores_path(cfg, root).read_text(encoding="utf-8"))

    obs_root = root / cfg["paths"]["transformed"]
    ana_root = root / cfg["paths"]["transformed_analytics"]
    conditions = [cid for cid, _ in resolve_eval_conditions(cfg, root)]

    instrument: dict[str, Any] = {
        "git": _git_meta(root),
        "config": str(args.config or "configs/cikm_v0.1.yaml"),
        "paper_protocol": proto,
        "seed": seed,
        "tfidf": {
            "analyzer": tfidf["analyzer"],
            "ngram_range": list(tfidf["ngram_range"]),
            "max_features": tfidf["max_features"],
            "fit": tfidf["fit"],
        },
        "adversary": "evaluate_trial4_adversary with pre-fitted train-only TF-IDF",
        "do_not_write": [
            "outputs/pilot_v2/**",
            "data/**",
            "paper/**/*.tex",
            "src/eval/adversary_trial4.py",
        ],
        "n_raw_events": len(raw_by_id),
        "n_personas": len(persona_table),
        "conditions": conditions,
    }

    identity: dict[str, Any] = {"conditions": {}}
    text_z: dict[str, Any] = {}
    schemas: dict[str, Any] = {}
    linkage: dict[str, Any] = {"observability": {}, "analytics": {}}

    print("[audit] identity + payload comparison", file=sys.stderr)
    for cid in conditions:
        obs_ex = load_condition_exports(obs_root / cid)
        ana_ex = load_condition_exports(ana_root / cid)
        obs_ids, ana_ids = set(obs_ex), set(ana_ex)
        identity["conditions"][cid] = {
            "n_obs": len(obs_ids),
            "n_ana": len(ana_ids),
            "event_ids_equal": obs_ids == ana_ids,
            "symmetric_diff": len(obs_ids ^ ana_ids),
        }
        if cid in TEXT_ARMS:
            text_z[cid] = _compare_text_z(obs_ex, ana_ex)
        if cid in SEMANTIC_ARMS:
            schemas[cid] = _schema_compare(obs_ex, ana_ex)

    # Split counts from first aligned condition
    first = conditions[0]
    obs_ex0 = load_condition_exports(obs_root / first)
    train_rows0 = join_eval_rows(labels, obs_ex0, splits, split="train")
    test_rows0 = join_eval_rows(labels, obs_ex0, splits, split="test")
    val_rows0 = join_eval_rows(labels, obs_ex0, splits, split="val")
    instrument["n_train_events"] = len(train_rows0)
    instrument["n_test_events"] = len(test_rows0)
    instrument["n_val_events"] = len(val_rows0)
    instrument["n_test_personas"] = len({r["persona_id"] for r in test_rows0})
    instrument["n_train_personas"] = len({r["persona_id"] for r in train_rows0})
    instrument["expected"] = {
        "events": 3894,
        "train": 2777,
        "test": 630,
        "test_personas": 20,
        "conditions": 9,
    }
    instrument["counts_match_frozen"] = (
        len(raw_by_id) == 3894
        and len(train_rows0) == 2777
        and len(test_rows0) == 630
        and instrument["n_test_personas"] == 20
        and len(conditions) == 9
        and all(identity["conditions"][c]["event_ids_equal"] for c in conditions)
    )

    _dump(out_dir / "instrument.json", instrument)
    _dump(out_dir / "paper_protocol_snapshot.json", proto)
    _dump(out_dir / "identity.json", identity)
    _dump(out_dir / "text_z_equality.json", text_z)
    _dump(out_dir / "semantic_schemas.json", schemas)

    text_ok = all(text_z[c]["embed_text_identical"] for c in TEXT_ARMS)
    print(f"[audit] text embed-identical={text_ok}; running Trial4", file=sys.stderr)

    for cid in conditions:
        print(f"[audit] Trial4 {cid}", file=sys.stderr)
        obs_ex = load_condition_exports(obs_root / cid)
        ana_ex = load_condition_exports(ana_root / cid)
        obs_train = join_eval_rows(labels, obs_ex, splits, split="train")
        obs_test = join_eval_rows(labels, obs_ex, splits, split="test")
        ana_train = join_eval_rows(labels, ana_ex, splits, split="train")
        ana_test = join_eval_rows(labels, ana_ex, splits, split="test")
        linkage["observability"][cid] = _run_train_only_trial4(
            obs_train, obs_test, raw_by_id, persona_table, seed=seed, tfidf=tfidf
        )
        linkage["analytics"][cid] = _run_train_only_trial4(
            ana_train, ana_test, raw_by_id, persona_table, seed=seed, tfidf=tfidf
        )
        linkage["observability"][cid]["frozen_transductive_R"] = float(
            _frozen_t4(obs_metrics, cid)["combined_linkage_score"]
        )

    _dump(out_dir / "linkage_train_only.json", linkage)

    # Text-arm linkage sanity
    text_link_diag = {}
    text_link_ok = True
    for cid in TEXT_ARMS:
        ro = linkage["observability"][cid]
        ra = linkage["analytics"][cid]
        dR = float(ra["combined_linkage_score"]) - float(ro["combined_linkage_score"])
        text_link_diag[cid] = {
            "R_obs": ro["combined_linkage_score"],
            "R_ana": ra["combined_linkage_score"],
            "delta_R": dR,
            "persona_equal": ro["persona_top1"] == ra["persona_top1"],
            "attr_equal": ro["attribute_combined_macro_f1"]
            == ra["attribute_combined_macro_f1"],
            "long_equal": ro["longitudinal_linkage_auc"]
            == ra["longitudinal_linkage_auc"],
            "token_equal": ro["token_recovery_rate"] == ra["token_recovery_rate"],
        }
        if abs(dR) > 1e-12:
            text_link_ok = False
    _dump(out_dir / "text_linkage_sanity.json", {"ok": text_link_ok, "conditions": text_link_diag})

    comparison_rows = []
    for cid in conditions:
        o, a = linkage["observability"][cid], linkage["analytics"][cid]
        comparison_rows.append(
            {
                "condition": cid,
                "R_persona_obs": o["persona_top1"],
                "R_persona_ana": a["persona_top1"],
                "R_attr_obs": o["attribute_combined_macro_f1"],
                "R_attr_ana": a["attribute_combined_macro_f1"],
                "R_long_obs": o["longitudinal_linkage_auc"],
                "R_long_ana": a["longitudinal_linkage_auc"],
                "R_obs": o["combined_linkage_score"],
                "R_ana": a["combined_linkage_score"],
                "delta_R": float(a["combined_linkage_score"])
                - float(o["combined_linkage_score"]),
                "token_obs": o["token_recovery_rate"],
                "token_ana": a["token_recovery_rate"],
                "frozen_transductive_R_obs": o["frozen_transductive_R"],
                "delta_trainonly_vs_frozen_obs": float(o["combined_linkage_score"])
                - float(o["frozen_transductive_R"]),
            }
        )
    _write_csv(out_dir / "linkage_comparison.csv", comparison_rows)
    _dump(out_dir / "linkage_comparison.json", comparison_rows)

    rank_obs = sorted(conditions, key=lambda c: linkage["observability"][c]["combined_linkage_score"])
    rank_ana = sorted(conditions, key=lambda c: linkage["analytics"][c]["combined_linkage_score"])
    ranks = {
        "lowest_to_highest_obs": rank_obs,
        "lowest_to_highest_ana": rank_ana,
        "rank_changed": rank_obs != rank_ana,
    }
    _dump(out_dir / "ranks.json", ranks)

    crossings = []
    for row in comparison_rows:
        for thr in R_MAX_GRID:
            o_in = row["R_obs"] <= thr
            a_in = row["R_ana"] <= thr
            if o_in != a_in:
                crossings.append(
                    {
                        "condition": row["condition"],
                        "R_max": thr,
                        "obs_feasible": o_in,
                        "ana_feasible": a_in,
                    }
                )
    _dump(out_dir / "threshold_crossings.json", crossings)

    obs_R = {c: float(linkage["observability"][c]["combined_linkage_score"]) for c in conditions}
    ana_R = {c: float(linkage["analytics"][c]["combined_linkage_score"]) for c in conditions}
    frozen_R = {
        c: float(_frozen_t4(obs_metrics, c)["combined_linkage_score"]) for c in conditions
    }

    obs_pts = _make_points(
        conditions,
        obs_metrics=obs_metrics,
        analytics=analytics_metrics,
        track_c=track_c,
        linkage_by_cid=obs_R,
    )
    ana_pts = _make_points(
        conditions,
        obs_metrics=obs_metrics,
        analytics=analytics_metrics,
        track_c=track_c,
        linkage_by_cid=ana_R,
    )
    shared_frozen_pts = _make_points(
        conditions,
        obs_metrics=obs_metrics,
        analytics=analytics_metrics,
        track_c=track_c,
        linkage_by_cid=frozen_R,
    )

    purposes = [
        "observability",
        "analytics_med",
        "analytics_side",
        "analytics_adherence",
        "analytics_cohort",
    ]
    purpose_sel = {
        "observability_R_for_To": _winners_table(obs_pts, purposes),
        "analytics_R_for_Ta": _winners_table(ana_pts, purposes),
        "shared_frozen_obs_R": _winners_table(shared_frozen_pts, purposes),
    }
    # T_o-2 error_stage
    to2 = {
        str(r): {
            "obs_R": _error_stage_winner(obs_metrics, obs_R, conditions, r),
            "shared_frozen_R": _error_stage_winner(obs_metrics, frozen_R, conditions, r),
        }
        for r in R_MAX_GRID
    }
    purpose_sel["T_o_2_error_stage"] = to2
    _dump(out_dir / "operative_selection.json", purpose_sel)

    pareto = {}
    for purpose in purposes:
        shared_f = _pareto_for_purpose(shared_frozen_pts, purpose)
        if purpose == "observability":
            new_f = _pareto_for_purpose(obs_pts, purpose)
        else:
            new_f = _pareto_for_purpose(ana_pts, purpose)
        pareto[purpose] = {
            "shared_frozen_obs_R": shared_f,
            "purpose_specific": new_f,
            "enter": sorted(set(new_f) - set(shared_f)),
            "leave": sorted(set(shared_f) - set(new_f)),
        }
    _dump(out_dir / "pareto.json", pareto)

    balanced = next(b for b in TASK_BUNDLES if b["id"] == "dual_purpose_balanced")
    umin_obs = balanced["constraints"]["u_obs_min"]
    umin_med = balanced["constraints"]["u_analytics_med_min"]
    bundle = {"floors": {"U_obs_min": umin_obs, "U_med_min": umin_med}, "by_r_max": {}}
    for r_max in R_MAX_GRID:
        hits = []
        for cid in conditions:
            uo = _u_obs(obs_metrics, cid)
            um = _u_ana(analytics_metrics, cid, "medication_class_macro_f1")
            ok = (
                obs_R[cid] <= r_max + 1e-9
                and ana_R[cid] <= r_max + 1e-9
                and uo >= umin_obs
                and um >= umin_med
            )
            hits.append(
                {
                    "condition": cid,
                    "R_obs": obs_R[cid],
                    "R_ana": ana_R[cid],
                    "U_obs": uo,
                    "U_med": um,
                    "satisfies": ok,
                }
            )
        bundle["by_r_max"][str(r_max)] = {
            "satisfying": [h["condition"] for h in hits if h["satisfies"]],
            "n_satisfying": sum(h["satisfies"] for h in hits),
            "detail": hits,
        }
    bundle["no_single_condition_at_0.45"] = (
        bundle["by_r_max"]["0.45"]["n_satisfying"] == 0
    )
    _dump(out_dir / "dual_purpose_bundle.json", bundle)

    regret = _purpose_specific_regret(obs_pts, ana_pts, r_max=FOCAL_R_MAX)
    _dump(out_dir / "regret_purpose_specific.json", regret)

    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "output_dir": str(out_dir),
        "paper_protocol_locked_on": proto.get("locked_on"),
        "text_z_embed_identical": text_ok,
        "text_linkage_identical": text_link_ok,
        "instrument_counts_match": instrument["counts_match_frozen"],
        "stopped_before_semantic_interp": not (text_ok and text_link_ok),
    }
    _dump(out_dir / "run_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    if not text_ok or not text_link_ok:
        print(
            "[audit] TEXT SANITY FAILED — see text_z_equality.json / "
            "text_linkage_sanity.json before interpreting semantic ΔR",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
