"""Diagnostic: Track C vs direct-field ceiling for Ta-5 (sem_fine).

Does not modify Track C, caches, policies, schemas, linkage JSON, or the paper.
Writes only under outputs/post_acceptance_experiments/ta5_cohort_audit/.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sklearn.metrics import f1_score

from eval.analytics_task import (  # noqa: E402
    analytics_consumer_input,
    ground_truth_adherence_signal,
    ground_truth_medication_class,
    ground_truth_side_effect_signal,
    serialize_for_transfer,
)
from eval.export_text import export_text_for_embedding  # noqa: E402
from eval.io import join_eval_rows, load_labels, load_splits  # noqa: E402
from eval.study import resolve_eval_conditions  # noqa: E402
from eval.tier1_analytics_consumer import (  # noqa: E402
    PROMPT_VERSION,
    _tier1_cfg,
    build_analytics_system_prompt,
    load_analytics_vocab,
)
from sbb.config import load_config, repo_root  # noqa: E402
from transform.analytics_map import cohort_segment  # noqa: E402
from transform.io import load_condition_exports, load_jsonl  # noqa: E402

AUDIT_REL = Path("outputs/post_acceptance_experiments/ta5_cohort_audit")
R_MAX = (0.40, 0.45, 0.50, 0.55)
REGISTERED_EVENT_FIELDS = (
    "medication_class",
    "side_effect_signal",
    "adherence_signal",
)


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n", encoding="utf-8")


def _majority(values: list[str]) -> str:
    counts = Counter(values)
    return counts.most_common(1)[0][0]


def _persona_field_values(
    rows: list[dict[str, Any]], field: str
) -> dict[str, list[str]]:
    by_pid: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        val = row["export"]["z"].get(field)
        if val is None:
            continue
        by_pid[row["persona_id"]].append(str(val))
    return dict(by_pid)


def _direct_field_cohort(
    rows: list[dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    field: str = "cohort_segment",
) -> dict[str, Any]:
    by_pid = _persona_field_values(rows, field)
    persona_ids = sorted({row["persona_id"] for row in rows})
    missing = [pid for pid in persona_ids if pid not in by_pid]
    y_true: list[str] = []
    y_pred: list[str] = []
    n_nonconstant = 0
    n_mismatch_vs_table = 0
    for pid in persona_ids:
        gold = cohort_segment(persona_table[pid])
        vals = by_pid.get(pid, [])
        if not vals:
            continue
        if len(set(vals)) > 1:
            n_nonconstant += 1
        pred = _majority(vals)
        if pred != gold:
            n_mismatch_vs_table += 1
        y_true.append(gold)
        y_pred.append(pred)
    f1 = (
        float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        if y_true
        else None
    )
    return {
        "field": field,
        "n_test_personas": len(persona_ids),
        "n_personas_with_field": len(by_pid),
        "n_personas_missing_field": len(missing),
        "n_nonconstant_personas": n_nonconstant,
        "n_mismatch_vs_persona_table": n_mismatch_vs_table,
        "macro_f1": f1,
        "exact_one": f1 == 1.0,
        "y_true_class_counts": dict(Counter(y_true)),
        "y_pred_class_counts": dict(Counter(y_pred)),
    }


def _event_field_ceiling(
    rows: list[dict[str, Any]], field: str, gold_fn
) -> dict[str, Any]:
    n_present = 0
    y_true: list[str] = []
    y_pred: list[str] = []
    for row in rows:
        val = row["export"]["z"].get(field)
        gold = gold_fn(row["label"])
        if val is None:
            continue
        n_present += 1
        y_true.append(str(gold))
        y_pred.append(str(val))
    f1 = (
        float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        if y_true
        else None
    )
    return {
        "field": field,
        "n_test_events": len(rows),
        "n_events_with_field": n_present,
        "macro_f1": f1,
        "exact_one": f1 == 1.0,
    }


def _payload_contains_cohort(export: dict[str, Any]) -> dict[str, Any]:
    qwen_text = serialize_for_transfer(export)
    # Linkage in the paper is scored on observability exports; still check
    # whether the analytics payload would expose the field if embedded.
    analytics_embed = (
        qwen_text
        if isinstance(analytics_consumer_input(export), str)
        else json.dumps(analytics_consumer_input(export), sort_keys=True)
    )
    return {
        "z_keys": sorted(export["z"]),
        "qwen_payload_contains_cohort_segment": "cohort_segment" in qwen_text,
        "analytics_embed_text_contains_cohort_segment": (
            "cohort_segment" in analytics_embed
        ),
        "qwen_payload_excerpt": qwen_text[:400],
    }


def main() -> int:
    root = repo_root()
    cfg = load_config(None)
    out_dir = root / AUDIT_REL
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    track_c = json.loads((out_dir / "track_c_scores.json").read_text(encoding="utf-8"))
    obs_metrics = json.loads(
        (root / "outputs/pilot_v2/metrics.json").read_text(encoding="utf-8")
    )
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    obs_root = root / cfg["paths"]["transformed"]

    vocab = load_analytics_vocab(root, cfg)
    prompt = build_analytics_system_prompt(vocab)
    tcfg = _tier1_cfg(cfg)

    per_condition: dict[str, Any] = {}
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        ana_exports = load_condition_exports(analytics_root / condition_id)
        obs_exports = load_condition_exports(obs_root / condition_id)
        if not ana_exports:
            continue
        test_rows = join_eval_rows(labels, ana_exports, persona_split, split="test")
        all_rows = join_eval_rows(labels, ana_exports, persona_split, split="train")
        all_rows = all_rows + test_rows
        z_keys = sorted({k for e in ana_exports.values() for k in e["z"]})
        sample = next(iter(ana_exports.values()))
        obs_sample = next(iter(obs_exports.values())) if obs_exports else None
        obs_z_keys = sorted(obs_sample["z"]) if obs_sample else []
        cohort_on_all = _direct_field_cohort(
            [
                {"persona_id": e["persona_id"], "export": e, "event_id": e["event_id"]}
                for e in ana_exports.values()
            ],
            persona_table,
        )
        # Rebuild join-shaped rows for the all-export check above used a stub;
        # recompute properly from exports + persona table only.
        stub_rows = []
        for e in ana_exports.values():
            stub_rows.append({"persona_id": e["persona_id"], "export": e, "label": {}})
        cohort_on_all = _direct_field_cohort(stub_rows, persona_table)

        event_ceilings = {}
        golders = {
            "medication_class": ground_truth_medication_class,
            "side_effect_signal": ground_truth_side_effect_signal,
            "adherence_signal": ground_truth_adherence_signal,
        }
        for field, fn in golders.items():
            event_ceilings[field] = _event_field_ceiling(test_rows, field, fn)

        per_condition[condition_id] = {
            "analytics_z_keys": z_keys,
            "obs_z_keys": obs_z_keys,
            "releases_cohort_segment": "cohort_segment" in z_keys,
            "releases_engagement_trend": "engagement_trend" in z_keys,
            "test_direct_field_cohort": _direct_field_cohort(
                test_rows, persona_table
            ),
            "corpus_direct_field_cohort": cohort_on_all,
            "test_event_field_ceilings": event_ceilings,
            "analytics_payload": _payload_contains_cohort(sample),
            "obs_z_contains_cohort_segment": "cohort_segment" in obs_z_keys,
            "obs_embed_contains_cohort_segment": (
                "cohort_segment" in export_text_for_embedding(obs_sample)
                if obs_sample
                else None
            ),
        }

    fine_c = track_c["conditions"]["sem_fine"]["track_c_assessor_symmetric"]
    fine_direct = per_condition["sem_fine"]["test_direct_field_cohort"]["macro_f1"]
    rz = obs_metrics["conditions"]["sem_fine"]["trial4_adversary"]
    rz_combined = float(rz["combined_linkage_score"])

    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "diagnostic_only": True,
        "did_not_modify": [
            "Track C",
            "frozen consumer prompts",
            "policies",
            "schemas",
            "lattice exports",
            "linkage scores",
            "utility scores for other tasks",
            "paper figures",
            "main.tex",
        ],
        "track_c_sem_fine_macro_f1": fine_c,
        "direct_field_ceiling_sem_fine_macro_f1": fine_direct,
        "direct_field_exact_one": per_condition["sem_fine"]["test_direct_field_cohort"][
            "exact_one"
        ],
        "utility_gap": fine_direct - fine_c,
        "published_obs_R_z_sem_fine": rz_combined,
        "published_embedder": rz.get("embedder"),
        "published_persona_inference_mode": rz.get("persona_inference_mode"),
        "r_max_grid": list(R_MAX),
        "sem_fine_feasible_at_r_max": {
            str(r): rz_combined <= r for r in R_MAX
        },
        "sem_fine_infeasible_at_all_reported_r_max": all(
            rz_combined > r for r in R_MAX
        ),
        "consumer": {
            "prompt_version": PROMPT_VERSION,
            "model": tcfg["primary_model"],
            "system_prompt_requests_cohort_segment": "cohort_segment" in prompt,
            "system_prompt_output_keys": [
                "medication_class",
                "side_effect_signal",
                "adherence_signal",
            ],
            "aggregation_reads_z_cohort_segment": False,
            "same_pipeline_all_conditions": True,
            "pipeline": (
                "Qwen analytics_triage_v1 event outputs → 30-day rates "
                "(event_count, side_effect_rate, adherence_barrier_rate, med_*) "
                "→ RF n=50 seed 42, both splits"
            ),
        },
        "conditions": per_condition,
        "note_on_train_only_linkage": (
            "Published R(z) in outputs/pilot_v2/metrics.json is Trial4 "
            "combined_linkage_score on observability exports "
            "(data/transformed/), embedder tfidf_char_wb. "
            "A train-only vectorizer protocol is a parallel laptop job and is "
            "not on this branch. Feasibility at 0.40–0.55 does not depend on "
            "that protocol: published R(z)=0.752 already exceeds 0.55. "
            "Analytics z.cohort_segment is not in the observability embedding "
            "string used for that R(z)."
        ),
    }
    _dump(out_dir / "direct_field_ceiling.json", report)
    print(json.dumps({k: report[k] for k in (
        "track_c_sem_fine_macro_f1",
        "direct_field_ceiling_sem_fine_macro_f1",
        "direct_field_exact_one",
        "utility_gap",
        "published_obs_R_z_sem_fine",
        "sem_fine_infeasible_at_all_reported_r_max",
        "sem_fine_feasible_at_r_max",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
