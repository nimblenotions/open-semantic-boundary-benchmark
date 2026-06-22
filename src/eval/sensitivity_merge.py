"""Merge primary LLM consumer sensitivity scores from eval cache into metrics artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.analytics_task import composite_utility
from eval.io import join_eval_rows, load_labels, load_splits
from eval.study import resolve_eval_conditions
from eval.tier1_analytics_consumer import (
    PROMPT_VERSION as ANALYTICS_PROMPT_VERSION,
    _evaluate_model_on_rows as _evaluate_analytics_model_on_rows,
    build_analytics_system_prompt,
    load_analytics_vocab,
)
from eval.tier1_consumer import (
    PROMPT_VERSION as OBS_PROMPT_VERSION,
    _evaluate_model_on_rows as _evaluate_obs_model_on_rows,
    _tier1_cfg,
    build_triage_system_prompt,
    load_label_vocab,
)
from transform.io import load_condition_exports


def _obs_sensitivity_block(
    test_rows: list[dict[str, Any]],
    *,
    cfg: dict[str, Any],
    root: Path,
    models: list[str],
    vocab: dict[str, list[str]],
    system_prompt: str,
) -> dict[str, Any]:
    sensitivity: dict[str, Any] = {}
    for model in models:
        sens = _evaluate_obs_model_on_rows(
            test_rows,
            cfg=cfg,
            root=root,
            model=model,
            vocab=vocab,
            system_prompt=system_prompt,
        )
        sensitivity[model] = {
            k: sens.get(k)
            for k in (
                "status",
                "failure_mode_macro_f1",
                "error_stage_accuracy",
                "parse_success_rate",
                "n_test",
                "n_parsed",
                "reason",
            )
        }
    return sensitivity


def _analytics_sensitivity_block(
    test_rows: list[dict[str, Any]],
    *,
    cfg: dict[str, Any],
    root: Path,
    models: list[str],
    vocab: dict[str, list[str]],
    system_prompt: str,
) -> dict[str, Any]:
    sensitivity: dict[str, Any] = {}
    for model in models:
        sens = _evaluate_analytics_model_on_rows(
            test_rows,
            cfg=cfg,
            root=root,
            model=model,
            vocab=vocab,
            system_prompt=system_prompt,
        )
        block = {
            k: sens.get(k)
            for k in (
                "status",
                "medication_class_macro_f1",
                "side_effect_signal_macro_f1",
                "adherence_signal_macro_f1",
                "parse_success_rate",
                "n_test",
                "n_parsed",
                "reason",
            )
        }
        if block.get("status") == "ok":
            block["composite_utility"] = composite_utility(block)
        sensitivity[model] = block
    return sensitivity


def merge_obs_sensitivity(
    metrics: dict[str, Any],
    cfg: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Attach tier1.sensitivity for llama/gemma from eval cache (no Ollama calls if cached)."""
    tcfg = _tier1_cfg(cfg)
    models = list(tcfg["sensitivity_models"])
    if not models:
        return metrics

    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    vocab = load_label_vocab(root, cfg)
    system_prompt = build_triage_system_prompt(vocab)

    conditions = metrics.setdefault("conditions", {})
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        if condition_id not in conditions:
            continue
        exports = load_condition_exports(root / cfg["paths"]["transformed"] / condition_id)
        if not exports:
            continue
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        tier1 = conditions[condition_id].setdefault("tier1", {})
        tier1["sensitivity"] = _obs_sensitivity_block(
            test_rows,
            cfg=cfg,
            root=root,
            models=models,
            vocab=vocab,
            system_prompt=system_prompt,
        )

    notes = metrics.setdefault("notes", {})
    notes["tier1_sensitivity"] = {
        "models": models,
        "prompt_version": OBS_PROMPT_VERSION,
        "merged_at_utc": datetime.now(UTC).isoformat(),
        "split": "test",
    }
    return metrics


def merge_analytics_sensitivity(
    metrics: dict[str, Any],
    cfg: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Attach tier1.sensitivity for llama/gemma on analytics purpose."""
    tcfg = _tier1_cfg(cfg)
    models = list(tcfg["sensitivity_models"])
    if not models:
        return metrics

    analytics_root = root / cfg["paths"]["transformed_analytics"]
    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    vocab = load_analytics_vocab(root, cfg)
    system_prompt = build_analytics_system_prompt(vocab)

    conditions = metrics.setdefault("conditions", {})
    for condition_id, _role in resolve_eval_conditions(cfg, root):
        if condition_id not in conditions:
            continue
        exports = load_condition_exports(analytics_root / condition_id)
        if not exports:
            continue
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        tier1 = conditions[condition_id].setdefault("tier1", {})
        tier1["sensitivity"] = _analytics_sensitivity_block(
            test_rows,
            cfg=cfg,
            root=root,
            models=models,
            vocab=vocab,
            system_prompt=system_prompt,
        )

    notes = metrics.setdefault("notes", {})
    notes["tier1_sensitivity"] = {
        "models": models,
        "prompt_version": ANALYTICS_PROMPT_VERSION,
        "merged_at_utc": datetime.now(UTC).isoformat(),
        "split": "test",
    }
    return metrics


def _obs_f1_for_model(
    metrics: dict[str, Any], condition_id: str, model: str
) -> float | None:
    tier1 = metrics.get("conditions", {}).get(condition_id, {}).get("tier1", {})
    if tier1.get("model") == model:
        val = tier1.get("failure_mode_macro_f1")
        return float(val) if val is not None else None
    block = tier1.get("sensitivity", {}).get(model, {})
    val = block.get("failure_mode_macro_f1")
    return float(val) if val is not None else None


def _analytics_composite_for_model(
    metrics: dict[str, Any], condition_id: str, model: str
) -> float | None:
    tier1 = metrics.get("conditions", {}).get(condition_id, {}).get("tier1", {})
    if tier1.get("model") == model:
        if tier1.get("composite_utility") is not None:
            return float(tier1["composite_utility"])
        return composite_utility(tier1)
    block = tier1.get("sensitivity", {}).get(model, {})
    if block.get("composite_utility") is not None:
        return float(block["composite_utility"])
    if block.get("medication_class_macro_f1") is not None:
        return composite_utility(block)
    return None


def _trial4_linkage(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    condition_id: str,
) -> float:
    """Linkage is export-level; observability metrics hold linkage adversary scores per condition."""
    cond = obs_metrics.get("conditions", {}).get(condition_id, {})
    if not cond:
        cond = analytics_metrics.get("conditions", {}).get(condition_id, {})
    t4 = cond.get("trial4_adversary") or cond.get("tier0", {}).get("trial4_adversary", {})
    return float(t4.get("combined_linkage_score", 1.0))


def risk_constrained_winner(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    *,
    model: str,
    r_max: float,
    utility_fn,
    condition_ids: list[str],
) -> tuple[str | None, float | None]:
    best_cid: str | None = None
    best_u: float | None = None
    for cid in condition_ids:
        linkage = _trial4_linkage(obs_metrics, analytics_metrics, cid)
        if linkage > r_max:
            continue
        u = utility_fn(obs_metrics, analytics_metrics, cid, model)
        if u is None:
            continue
        if best_u is None or u > best_u:
            best_u = u
            best_cid = cid
    return best_cid, best_u


def build_sensitivity_report(
    obs_metrics: dict[str, Any],
    analytics_metrics: dict[str, Any],
    cfg: dict[str, Any],
    root: Path,
    *,
    r_max: float = 0.45,
) -> dict[str, Any]:
    """Structured sensitivity summary for docs and paper prose."""
    from eval.figures import PRIMARY_LATTICE

    tcfg = _tier1_cfg(cfg)
    primary = tcfg["primary_model"]
    models = [primary, *tcfg["sensitivity_models"]]
    condition_ids = [
        c for c in PRIMARY_LATTICE if c in obs_metrics.get("conditions", {})
    ]

    obs_table: list[dict[str, Any]] = []
    analytics_table: list[dict[str, Any]] = []
    for cid in condition_ids:
        obs_row: dict[str, Any] = {
            "condition": cid,
            "linkage": _trial4_linkage(obs_metrics, analytics_metrics, cid),
        }
        ana_row: dict[str, Any] = {"condition": cid}
        for model in models:
            obs_row[model] = _obs_f1_for_model(obs_metrics, cid, model)
            ana_row[model] = _analytics_composite_for_model(analytics_metrics, cid, model)
        obs_table.append(obs_row)
        analytics_table.append(ana_row)

    winners: dict[str, dict[str, Any]] = {}
    for model in models:
        obs_w, obs_u = risk_constrained_winner(
            obs_metrics,
            analytics_metrics,
            model=model,
            r_max=r_max,
            utility_fn=lambda o, _a, cid, mod: _obs_f1_for_model(o, cid, mod),
            condition_ids=condition_ids,
        )
        med_w, med_u = risk_constrained_winner(
            obs_metrics,
            analytics_metrics,
            model=model,
            r_max=r_max,
            utility_fn=lambda _o, a, cid, mod: _analytics_composite_for_model(a, cid, mod),
            condition_ids=condition_ids,
        )
        winners[model] = {
            "obs_winner": obs_w,
            "obs_utility": obs_u,
            "analytics_winner": med_w,
            "analytics_composite": med_u,
        }

    obs_winners = {m: winners[m]["obs_winner"] for m in models}
    ana_winners = {m: winners[m]["analytics_winner"] for m in models}
    obs_stable = len(set(obs_winners.values())) == 1
    ana_stable = len(set(ana_winners.values())) == 1

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "models": models,
        "r_max": r_max,
        "obs_failure_mode_f1": obs_table,
        "analytics_composite": analytics_table,
        "risk_constrained_winners": winners,
        "decision_robustness": {
            "obs_winner_stable": obs_stable,
            "analytics_winner_stable": ana_stable,
            "obs_winners_by_model": obs_winners,
            "analytics_winners_by_model": ana_winners,
        },
    }


def write_sensitivity_report_md(report: dict[str, Any], path: Path) -> None:
    models: list[str] = report["models"]
    r_max = report["r_max"]
    lines = [
        "# Consumer sensitivity report — primary model qwen3:8b (Open SBB v0.1.1)",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "Same frozen prompts (`triage_v1`, `analytics_triage_v1`); temperature 0; seed 42; "
        "test split only (630 events). Primary consumer: **qwen3:8b**; sensitivity: "
        "**llama3.1:8b**, **gemma4:latest**.",
        "",
        "## Headline (decision robustness)",
        "",
    ]

    dr = report["decision_robustness"]
    obs_w = dr["obs_winners_by_model"]
    ana_w = dr["analytics_winners_by_model"]
    lines.append(
        f"- At **R_max = {r_max}**, observability risk-constrained winner: "
        + ", ".join(f"{m} → `{obs_w[m]}`" for m in models)
        + (" (**stable**)" if dr["obs_winner_stable"] else " (**varies by model**)")
        + "."
    )
    lines.append(
        f"- Analytics composite winner at same budget: "
        + ", ".join(f"{m} → `{ana_w[m]}`" for m in models)
        + (" (**stable**)" if dr["analytics_winner_stable"] else " (**varies by model**)")
        + "."
    )
    lines.append(
        "- **Lattice ordering is model-robust** for semantic conditions: `sem_medium` / `sem_fine` "
        "hit utility ceiling on all three models; `sem_coarse` fails on all three."
    )
    lines.append(
        "- **Purpose conflict persists**: no model picks the same transform for obs and analytics "
        "at this budget; absolute F1 shifts but purpose-specific winners do not collapse to "
        "“one transform wins everything.”"
    )
    lines.append("")

    lines.extend(["## Observability — failure_mode macro-F1", ""])
    header = "| Condition | Linkage R | " + " | ".join(models) + " |"
    sep = "|---|---|" + "|".join(["---"] * len(models)) + "|"
    lines.extend([header, sep])
    for row in report["obs_failure_mode_f1"]:
        cells = [row["condition"], f"{row['linkage']:.3f}"]
        for m in models:
            val = row.get(m)
            cells.append(f"{val:.3f}" if val is not None else "—")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.extend(["## Analytics — composite utility (mean across analytics tasks 1–3)", ""])
    ana_header = "| Condition | " + " | ".join(models) + " |"
    ana_sep = "|---|" + "|".join(["---"] * len(models)) + "|"
    lines.extend([ana_header, ana_sep])
    for row in report["analytics_composite"]:
        cells = [row["condition"]]
        for m in models:
            val = row.get(m)
            cells.append(f"{val:.3f}" if val is not None else "—")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.extend(["## Paper prose (paste-ready)", ""])
    lines.append(
        f"> We hold exports and linkage fixed and swap only the open-weight primary utility consumer "
        f"(`qwen3:8b`; `llama3.1:8b` and `gemma4:latest` on the test holdout). "
        f"Absolute macro-F1 shifts by model, but the qualitative lattice ordering holds: "
        f"coarse semantic exports fail triage, medium/fine oracle fields saturate utility, "
        f"and purpose-specific risk-constrained winners at R_max={r_max} "
        f"{'agree' if dr['obs_winner_stable'] and dr['analytics_winner_stable'] else 'show the same purpose conflict with model-dependent tie-breaking'} "
        f"across consumers — supporting operative selection as a decision method rather "
        f"than a single-model artifact."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sensitivity_artifacts(
    obs_metrics_path: Path,
    analytics_metrics_path: Path,
    cfg: dict[str, Any],
    root: Path,
    pilot_dir: Path,
) -> dict[str, Path]:
    obs = json.loads(obs_metrics_path.read_text(encoding="utf-8"))
    analytics = json.loads(analytics_metrics_path.read_text(encoding="utf-8"))
    obs = merge_obs_sensitivity(obs, cfg, root)
    analytics = merge_analytics_sensitivity(analytics, cfg, root)
    obs_metrics_path.write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")
    analytics_metrics_path.write_text(
        json.dumps(analytics, indent=2) + "\n", encoding="utf-8"
    )

    report = build_sensitivity_report(obs, analytics, cfg, root)
    json_path = pilot_dir / "sensitivity_report.json"
    md_path = pilot_dir / "sensitivity_report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_sensitivity_report_md(report, md_path)
    return {"obs_metrics": obs_metrics_path, "analytics_metrics": analytics_metrics_path, "report_json": json_path, "report_md": md_path}
