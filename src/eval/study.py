"""Orchestrate classical baseline, LLM consumer, and linkage observability study across export conditions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.adversary import evaluate_adversary
from eval.adversary_trial4 import evaluate_trial4_adversary
from eval.io import (
    join_eval_rows,
    load_condition_exports,
    load_labels,
    load_raw_events,
    load_splits,
)
from eval.provenance_score import evaluate_provenance
from eval.tier0_consumer import evaluate_tier0
import sys

from eval.tier1_consumer import _tier1_cfg, cache_stats_for_rows, evaluate_tier1
from eval.transfer_consumer import evaluate_transfer
from transform.io import condition_has_exports, load_jsonl

# Seven rule/semantic lattice arms (H1–H3 scope).
LATTICE_RULE_SEMANTIC = frozenset(
    {
        "raw",
        "redact_bracket",
        "redact_tokenize",
        "redact_surrogate",
        "sem_coarse",
        "sem_medium",
        "sem_fine",
    }
)
LLM_CONDITIONS = frozenset({"redact_llm_substitute", "redact_llm_rephrase"})


def resolve_eval_conditions(
    cfg: dict[str, Any], root: Path
) -> list[tuple[str, str]]:
    """Return (condition_id, role) pairs from lattice + legacy appendix pilots."""
    transformed_root = root / cfg["paths"]["transformed"]
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    default_role = cfg.get("lattice", {}).get("default_role", "primary")
    roles_cfg = cfg.get("lattice", {}).get("roles", {})

    for condition_id in cfg["lattice"]["conditions"]:
        role = roles_cfg.get(condition_id, default_role)
        ordered.append((condition_id, role))
        seen.add(condition_id)

    for condition_id in cfg.get("eval", {}).get("appendix_conditions", []):
        if condition_id in seen:
            continue
        cond_dir = transformed_root / condition_id
        if cond_dir.is_dir() and condition_has_exports(cond_dir):
            ordered.append((condition_id, "appendix"))
            seen.add(condition_id)

    return ordered


def _condition_trial4(metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics.get("trial4_adversary"):
        return metrics["trial4_adversary"]
    return metrics.get("tier0", {}).get("trial4_adversary", {})


def _utility_f1(metrics: dict[str, Any]) -> float:
    tier1 = metrics.get("tier1", {})
    if tier1.get("failure_mode_macro_f1") is not None:
        return float(tier1["failure_mode_macro_f1"])
    return float(
        metrics.get("tier0", {}).get("utility", {}).get("failure_mode_macro_f1", 0.0)
    )


def _trial4_linkage(condition_metrics: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {
        cid: float(_condition_trial4(m).get("combined_linkage_score", 0.0))
        for cid, m in condition_metrics.items()
    }


def _legacy_linkage(condition_metrics: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {
        cid: m["tier0"]["risk"]["persona_top1"]
        for cid, m in condition_metrics.items()
        if "tier0" in m
    }


def _legacy_contradiction_note(
    *,
    hypothesis: str,
    legacy_supported: bool,
    trial4_supported: bool,
    legacy_detail: str,
) -> str | None:
    if legacy_supported == trial4_supported:
        return None
    return (
        f"legacy persona_top1 would {'support' if legacy_supported else 'not support'} "
        f"{hypothesis} ({legacy_detail}); Trial4 combined_linkage verdict differs"
    )


def _evaluate_hypotheses(
    condition_metrics: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    lattice_7 = {
        cid: m for cid, m in condition_metrics.items() if cid in LATTICE_RULE_SEMANTIC
    }
    llm_arms = {cid: m for cid, m in condition_metrics.items() if cid in LLM_CONDITIONS}

    utility = {cid: _utility_f1(m) for cid, m in lattice_7.items()}
    linkage = _trial4_linkage(lattice_7)
    legacy_linkage = _legacy_linkage(lattice_7)

    transfer = {
        cid: m.get("transfer", {}).get("transfer_failure_mode_macro_f1", 0.0)
        for cid, m in lattice_7.items()
    }

    raw_f1 = utility.get("raw", 0.0)
    bracket_f1 = utility.get("redact_bracket", 0.0)
    medium_f1 = utility.get("sem_medium", 0.0)
    coarse_f1 = utility.get("sem_coarse", 0.0)
    fine_f1 = utility.get("sem_fine", 0.0)
    raw_transfer = transfer.get("raw", 0.0)
    bracket_transfer = transfer.get("redact_bracket", 0.0)

    per_cond_ok = bracket_f1 < raw_f1 * 0.8
    transfer_ok = bracket_transfer < raw_transfer * 0.8
    h1 = {
        "supported": per_cond_ok or transfer_ok,
        "detail": (
            f"redact_bracket F1 ({bracket_f1:.3f}) vs raw ({raw_f1:.3f}); "
            f"transfer F1 ({bracket_transfer:.3f}) vs raw transfer ({raw_transfer:.3f})"
        ),
        "per_condition": {
            "supported": per_cond_ok,
            "detail": f"redact_bracket F1 ({bracket_f1:.3f}) vs raw ({raw_f1:.3f})",
        },
        "transfer": {
            "supported": transfer_ok,
            "detail": (
                f"redact_bracket transfer F1 ({bracket_transfer:.3f}) "
                f"vs raw transfer ({raw_transfer:.3f})"
            ),
        },
    }

    h2_linkage_ok = linkage.get("sem_medium", 1.0) <= linkage.get("raw", 1.0)
    h2_legacy_linkage_ok = legacy_linkage.get("sem_medium", 1.0) <= legacy_linkage.get(
        "raw", 1.0
    )
    h2 = {
        "supported": medium_f1 >= raw_f1 * 0.7 and h2_linkage_ok,
        "detail": (
            f"sem_medium F1 ({medium_f1:.3f}) vs raw ({raw_f1:.3f}); "
            f"Trial4 combined_linkage {linkage.get('sem_medium', 0):.3f} "
            f"vs raw {linkage.get('raw', 0):.3f}"
        ),
    }
    h2_note = _legacy_contradiction_note(
        hypothesis="H2 linkage arm",
        legacy_supported=h2_legacy_linkage_ok,
        trial4_supported=h2_linkage_ok,
        legacy_detail=(
            f"{legacy_linkage.get('sem_medium', 0):.3f} vs raw "
            f"{legacy_linkage.get('raw', 0):.3f}"
        ),
    )
    if h2_note:
        h2["detail"] = f"{h2['detail']}; note: {h2_note}"

    h3_linkage_ok = linkage.get("sem_fine", 0.0) > linkage.get("sem_medium", 0.0)
    h3_legacy_linkage_ok = legacy_linkage.get("sem_fine", 0.0) > legacy_linkage.get(
        "sem_medium", 0.0
    )
    h3 = {
        "supported": fine_f1 > medium_f1 and h3_linkage_ok,
        "detail": (
            f"sem_fine F1 ({fine_f1:.3f}) vs sem_medium ({medium_f1:.3f}); "
            f"Trial4 combined_linkage {linkage.get('sem_fine', 0):.3f} "
            f"vs {linkage.get('sem_medium', 0):.3f}"
        ),
    }
    h3_note = _legacy_contradiction_note(
        hypothesis="H3 linkage arm",
        legacy_supported=h3_legacy_linkage_ok,
        trial4_supported=h3_linkage_ok,
        legacy_detail=(
            f"{legacy_linkage.get('sem_fine', 0):.3f} vs "
            f"{legacy_linkage.get('sem_medium', 0):.3f}"
        ),
    )
    if h3_note:
        h3["detail"] = f"{h3['detail']}; note: {h3_note}"

    llm_utility = {cid: _utility_f1(m) for cid, m in llm_arms.items()}
    llm_linkage = _trial4_linkage(llm_arms)
    subst_f1 = llm_utility.get("redact_llm_substitute", 0.0)
    reph_f1 = llm_utility.get("redact_llm_rephrase", 0.0)
    subst_link = llm_linkage.get("redact_llm_substitute", 1.0)
    reph_link = llm_linkage.get("redact_llm_rephrase", 1.0)
    raw_link = linkage.get("raw", 1.0)
    bracket_link = linkage.get("redact_bracket", 1.0)
    medium_link = linkage.get("sem_medium", 1.0)

    subst_utility_ok = subst_f1 >= bracket_f1 * 0.9
    reph_utility_ok = reph_f1 >= bracket_f1 * 0.9
    subst_link_ok = subst_link <= raw_link
    reph_link_ok = reph_link <= raw_link
    h4 = {
        "supported": (subst_utility_ok and subst_link_ok)
        or (reph_utility_ok and reph_link_ok),
        "detail": (
            f"substitute F1 ({subst_f1:.3f}) rephrase F1 ({reph_f1:.3f}) "
            f"vs bracket ({bracket_f1:.3f}) sem_medium ({medium_f1:.3f}); "
            f"linkage subst {subst_link:.3f} rephrase {reph_link:.3f} "
            f"vs raw {raw_link:.3f} bracket {bracket_link:.3f} sem_medium {medium_link:.3f}"
        ),
        "substitute": {
            "utility_ok": subst_utility_ok,
            "linkage_ok": subst_link_ok,
        },
        "rephrase": {
            "utility_ok": reph_utility_ok,
            "linkage_ok": reph_link_ok,
        },
    }

    return {
        "H1": h1,
        "H2": h2,
        "H3": h3,
        "H4": h4,
        "sem_coarse_f1": coarse_f1,
    }


def merge_obs_metrics(
    existing: dict[str, Any] | None, new: dict[str, Any]
) -> dict[str, Any]:
    """Merge per-condition blocks so linkage + tier1 runs compose into one metrics.json."""
    if not existing:
        return new

    merged = dict(new)
    existing_conds = existing.get("conditions", {})
    new_conds = merged.setdefault("conditions", {})
    all_ids = set(existing_conds) | set(new_conds)
    for cid in all_ids:
        new_conds[cid] = {**existing_conds.get(cid, {}), **new_conds.get(cid, {})}

    if not merged.get("hypotheses") and existing.get("hypotheses"):
        merged["hypotheses"] = existing["hypotheses"]
    return merged


def run_study(
    cfg: dict[str, Any],
    root: Path,
    *,
    tier: str,
    max_tier1_events: int | None = None,
) -> dict[str, Any]:
    eval_conditions = resolve_eval_conditions(cfg, root)
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    raw_by_id = load_raw_events(root / cfg["paths"]["raw"] / "events.jsonl")
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }
    seed = int(cfg.get("eval", {}).get("tier0", {}).get("random_seed", 42))

    raw_exports = load_condition_exports(
        root / cfg["paths"]["transformed"] / "raw"
    )
    raw_train_rows = (
        join_eval_rows(labels, raw_exports, persona_split, split="train")
        if raw_exports
        else []
    )

    run_tier0 = tier in ("0", "all")
    run_linkage = tier in ("linkage", "1-linkage", "all")
    run_tier1 = tier in ("1", "1-linkage", "all")

    condition_metrics: dict[str, dict[str, Any]] = {}
    tier1_cfg_logged = False
    for condition_id, role in eval_conditions:
        exports = load_condition_exports(
            root / cfg["paths"]["transformed"] / condition_id
        )
        if not exports:
            continue
        train_rows = join_eval_rows(labels, exports, persona_split, split="train")
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")

        metrics: dict[str, Any] = {
            "role": role,
            "provenance": evaluate_provenance(exports),
        }
        if run_linkage:
            metrics["trial4_adversary"] = evaluate_trial4_adversary(
                train_rows,
                test_rows,
                raw_by_id,
                persona_table,
                seed=seed,
            )
            metrics["transfer"] = evaluate_transfer(
                raw_train_rows,
                test_rows,
                condition_id,
                seed=seed,
            )
        if run_tier0:
            trial4 = evaluate_trial4_adversary(
                train_rows,
                test_rows,
                raw_by_id,
                persona_table,
                seed=seed,
            )
            metrics["tier0"] = {
                "utility": evaluate_tier0(train_rows, test_rows, seed=seed),
                "risk": evaluate_adversary(
                    train_rows, test_rows, raw_by_id, seed=seed
                ),
                "trial4_adversary": trial4,
            }
            if not run_linkage:
                metrics["transfer"] = evaluate_transfer(
                    raw_train_rows,
                    test_rows,
                    condition_id,
                    seed=seed,
                )
        if run_tier1:
            tcfg = _tier1_cfg(cfg)
            if not tier1_cfg_logged:
                print(
                    f"[tier1] batch_size={tcfg['batch_size']} "
                    f"batch_by_persona=True primary_model={tcfg['primary_model']}",
                    file=sys.stderr,
                )
                tier1_cfg_logged = True
            stats = cache_stats_for_rows(
                test_rows[:max_tier1_events] if max_tier1_events else test_rows,
                model=tcfg["primary_model"],
                condition_id=condition_id,
                root=root,
            )
            print(
                f"[tier1] {condition_id}: cache_hit={stats['hit']} "
                f"cache_miss={stats['miss']} total={stats['total']}",
                file=sys.stderr,
            )
            metrics["tier1"] = evaluate_tier1(
                train_rows,
                test_rows,
                cfg,
                root=root,
                max_events=max_tier1_events,
            )
            print(
                f"[tier1] {condition_id}: done "
                f"f1={metrics['tier1'].get('failure_mode_macro_f1')}",
                file=sys.stderr,
            )

        condition_metrics[condition_id] = metrics

    primary_metrics = {
        cid: m
        for cid, m in condition_metrics.items()
        if m.get("role") in ("primary", "frozen")
    }
    appendix_ids = [
        cid for cid, m in condition_metrics.items() if m.get("role") == "appendix"
    ]
    eval_hypotheses = tier in ("0", "all", "linkage", "1-linkage")

    return {
        "study": cfg.get("study", {}).get("name", "sbb-obs"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "tier": tier,
        "primary_metric": cfg.get("metrics", {}).get("primary", "failure_mode_macro_f1"),
        "conditions": condition_metrics,
        "hypotheses": _evaluate_hypotheses(primary_metrics) if eval_hypotheses else {},
        "notes": {
            "eval_split": "test",
            "train_split": "train",
            "primary_conditions": list(cfg["lattice"]["conditions"]),
            "llm_conditions": [
                c for c in cfg["lattice"]["conditions"] if c in LLM_CONDITIONS
            ],
            "appendix_conditions_evaluated": appendix_ids,
            "hypotheses_scope": "7 lattice (H1–H3) + LLM arms (H4)",
            "tier1_consumer": "active" if run_tier1 else "inactive",
            "linkage_tier": run_linkage,
        },
    }
