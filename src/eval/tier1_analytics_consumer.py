"""Tier-1 Ollama consumer: frozen analytics triage over lattice exports."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
from sklearn.metrics import f1_score

from eval.analytics_task import (
    ground_truth_adherence_signal,
    ground_truth_medication_class,
    ground_truth_side_effect_signal,
    serialize_for_transfer,
)
from eval.eval_cache_io import eval_condition_cache_dir, get_eval_cache_entry, upsert_eval_cache_entries
from eval.tier1_consumer import _chat_completion, _tier1_cfg
from transform.llm_sanitize import _extract_json_payload

PROMPT_VERSION = "analytics_triage_v1"
DEFAULT_BATCH_SIZE = 30

SIDE_EFFECT_SIGNALS = ("present", "absent")
ADHERENCE_SIGNALS = ("barrier", "none")


def load_analytics_vocab(root: Path, cfg: dict[str, Any]) -> dict[str, list[str]]:
    """Derive medication_class vocab from labels; fixed signal vocabularies for Ta-2/3."""
    labels_path = root / cfg["paths"]["ground_truth"] / "labels.jsonl"
    medication_classes: set[str] = set()
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        medication_classes.add(row["medication_class"])
    return {
        "medication_classes": sorted(medication_classes),
        "side_effect_signals": list(SIDE_EFFECT_SIGNALS),
        "adherence_signals": list(ADHERENCE_SIGNALS),
    }


def build_analytics_system_prompt(vocab: dict[str, list[str]]) -> str:
    med_classes = ", ".join(vocab["medication_classes"])
    side_effect = ", ".join(vocab["side_effect_signals"])
    adherence = ", ".join(vocab["adherence_signals"])
    return (
        "You are a BI/analytics agent for health-adjacent assistant traces. "
        "Each input is a policy-governed analytics export (text or semantic JSON). "
        "Classify each event using ONLY labels from the frozen vocabularies below. "
        "Do not infer observability failure modes or error stages.\n\n"
        f"medication_class (choose one): {med_classes}\n"
        f"side_effect_signal (choose one): {side_effect}\n"
        f"adherence_signal (choose one): {adherence}\n\n"
        "Return ONLY valid JSON. For a batch of events, return a JSON array of objects "
        "with keys event_id, medication_class, side_effect_signal, adherence_signal — "
        "same length and order as the input events array. "
        "For a single event, return one object with keys medication_class, "
        "side_effect_signal, and adherence_signal. "
        "No markdown fences or commentary."
    )


def _export_body(export: dict[str, Any]) -> str:
    return serialize_for_transfer(export)


def build_batch_user_message(rows: list[dict[str, Any]]) -> str:
    events = [
        {"event_id": row["event_id"], "export": _export_body(row["export"])}
        for row in rows
    ]
    return json.dumps({"events": events}, ensure_ascii=False)


def build_single_user_message(row: dict[str, Any]) -> str:
    return json.dumps(
        {"event_id": row["event_id"], "export": _export_body(row["export"])},
        ensure_ascii=False,
    )


def load_cached_prediction(
    root: Path, model: str, condition_id: str, event_id: str
) -> dict[str, str] | None:
    entry = get_eval_cache_entry(
        eval_condition_cache_dir(root, model, condition_id, analytics=True),
        event_id,
    )
    if entry is None:
        return None
    pred = entry.get("prediction")
    if (
        isinstance(pred, dict)
        and isinstance(pred.get("medication_class"), str)
        and isinstance(pred.get("side_effect_signal"), str)
        and isinstance(pred.get("adherence_signal"), str)
        and entry.get("prompt_version") == PROMPT_VERSION
    ):
        return {
            "medication_class": pred["medication_class"],
            "side_effect_signal": pred["side_effect_signal"],
            "adherence_signal": pred["adherence_signal"],
        }
    return None


def write_eval_cache(
    root: Path,
    *,
    model: str,
    condition_id: str,
    event_id: str,
    seed: int,
    prediction: dict[str, str],
    raw_completion: str,
) -> None:
    upsert_eval_cache_entries(
        eval_condition_cache_dir(root, model, condition_id, analytics=True),
        [
            {
                "event_id": event_id,
                "condition_id": condition_id,
                "model": model,
                "seed": seed,
                "prompt_version": PROMPT_VERSION,
                "prediction": prediction,
                "raw_completion": raw_completion,
            }
        ],
    )


def _validate_labels(
    pred: dict[str, str], vocab: dict[str, list[str]]
) -> dict[str, str]:
    # JSON null → .get returns None; coerce to "" for sklearn metrics.
    med = pred.get("medication_class") or ""
    se = pred.get("side_effect_signal") or ""
    ad = pred.get("adherence_signal") or ""
    # Keep out-of-vocab labels for scoring (macro-F1 treats them as incorrect).
    return {
        "medication_class": med,
        "side_effect_signal": se,
        "adherence_signal": ad,
    }


def _parse_single_prediction(content: str, vocab: dict[str, list[str]]) -> dict[str, str]:
    data = _extract_json_payload(content)
    if isinstance(data, list):
        if len(data) != 1:
            raise ValueError("Expected single-object response")
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("Prediction must be a JSON object")
    return _validate_labels(data, vocab)


def _parse_batch_predictions(
    content: str,
    rows: list[dict[str, Any]],
    vocab: dict[str, list[str]],
) -> dict[str, dict[str, str]]:
    data = _extract_json_payload(content)
    if isinstance(data, dict):
        for key in ("events", "predictions", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            if "medication_class" in data and len(rows) == 1:
                return {rows[0]["event_id"]: _validate_labels(data, vocab)}
            raise ValueError("Batch response missing predictions array")
    if not isinstance(data, list):
        raise ValueError("Batch response must be a JSON array")
    if len(data) != len(rows):
        raise ValueError(f"Expected {len(rows)} predictions, got {len(data)}")

    out: dict[str, dict[str, str]] = {}
    for row, item in zip(rows, data, strict=True):
        if not isinstance(item, dict):
            raise ValueError("Each batch prediction must be an object")
        event_id = item.get("event_id", row["event_id"])
        if event_id != row["event_id"]:
            raise ValueError(
                f"event_id mismatch: expected {row['event_id']}, got {event_id}"
            )
        out[row["event_id"]] = _validate_labels(item, vocab)
    return out


def _group_by_persona(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["persona_id"]].append(row)
    return dict(groups)


def _chunk_rows(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0:
        return [rows]
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def cache_stats_for_rows(
    rows: list[dict[str, Any]],
    *,
    model: str,
    condition_id: str,
    root: Path,
) -> dict[str, int]:
    """Count eval-cache hits vs misses for a model/condition (seed-independent)."""
    hit = miss = 0
    for row in rows:
        if load_cached_prediction(root, model, condition_id, row["event_id"]) is not None:
            hit += 1
        else:
            miss += 1
    return {"hit": hit, "miss": miss, "total": len(rows)}


def _predict_batch_chunk(
    rows: list[dict[str, Any]],
    *,
    system_prompt: str,
    vocab: dict[str, list[str]],
    model: str,
    seed: int,
    condition_id: str,
    root: Path,
    tcfg: dict[str, Any],
    client: httpx.Client | None,
) -> dict[str, dict[str, str]]:
    if len(rows) == 1:
        return _predict_single_row(
            rows[0],
            system_prompt=system_prompt,
            vocab=vocab,
            model=model,
            seed=seed,
            condition_id=condition_id,
            root=root,
            tcfg=tcfg,
            client=client,
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_batch_user_message(rows)},
    ]
    try:
        content = _chat_completion(
            messages,
            base_url=tcfg["base_url"],
            model=model,
            temperature=tcfg["temperature"],
            timeout=tcfg["timeout"],
            seed=seed,
            client=client,
        )
        parsed = _parse_batch_predictions(content, rows, vocab)
        upsert_eval_cache_entries(
            eval_condition_cache_dir(root, model, condition_id, analytics=True),
            [
                {
                    "event_id": row["event_id"],
                    "condition_id": condition_id,
                    "model": model,
                    "seed": seed,
                    "prompt_version": PROMPT_VERSION,
                    "prediction": parsed[row["event_id"]],
                    "raw_completion": content,
                }
                for row in rows
            ],
        )
        return parsed
    except (ValueError, httpx.HTTPError, KeyError, json.JSONDecodeError):
        if len(rows) <= 1:
            raise
        mid = len(rows) // 2
        left = _predict_batch_chunk(
            rows[:mid],
            system_prompt=system_prompt,
            vocab=vocab,
            model=model,
            seed=seed,
            condition_id=condition_id,
            root=root,
            tcfg=tcfg,
            client=client,
        )
        right = _predict_batch_chunk(
            rows[mid:],
            system_prompt=system_prompt,
            vocab=vocab,
            model=model,
            seed=seed,
            condition_id=condition_id,
            root=root,
            tcfg=tcfg,
            client=client,
        )
        left.update(right)
        return left


def _predict_single_row(
    row: dict[str, Any],
    *,
    system_prompt: str,
    vocab: dict[str, list[str]],
    model: str,
    seed: int,
    condition_id: str,
    root: Path,
    tcfg: dict[str, Any],
    client: httpx.Client | None,
) -> dict[str, dict[str, str]]:
    cached = load_cached_prediction(root, model, condition_id, row["event_id"])
    if cached is not None:
        return {row["event_id"]: cached}

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_single_user_message(row)},
    ]
    content = _chat_completion(
        messages,
        base_url=tcfg["base_url"],
        model=model,
        temperature=tcfg["temperature"],
        timeout=tcfg["timeout"],
        seed=seed,
        client=client,
    )
    pred = _parse_single_prediction(content, vocab)
    write_eval_cache(
        root,
        model=model,
        condition_id=condition_id,
        event_id=row["event_id"],
        seed=seed,
        prediction=pred,
        raw_completion=content,
    )
    return {row["event_id"]: pred}


def predict_rows(
    rows: list[dict[str, Any]],
    *,
    cfg: dict[str, Any],
    root: Path,
    model: str,
    seed: int,
    condition_id: str,
    vocab: dict[str, list[str]],
    system_prompt: str,
    client: httpx.Client | None = None,
    use_cache: bool = True,
) -> dict[str, dict[str, str]]:
    if not rows:
        return {}

    tcfg = _tier1_cfg(cfg)
    predictions: dict[str, dict[str, str]] = {}
    pending: list[dict[str, Any]] = []

    for row in rows:
        if use_cache:
            cached = load_cached_prediction(root, model, condition_id, row["event_id"])
            if cached is not None:
                predictions[row["event_id"]] = cached
                continue
        pending.append(row)

    if not pending:
        return predictions

    for _pid, persona_rows in sorted(_group_by_persona(pending).items()):
        for chunk in _chunk_rows(persona_rows, tcfg["batch_size"]):
            chunk_preds = _predict_batch_chunk(
                chunk,
                system_prompt=system_prompt,
                vocab=vocab,
                model=model,
                seed=seed,
                condition_id=condition_id,
                root=root,
                tcfg=tcfg,
                client=client,
            )
            predictions.update(chunk_preds)

    return predictions


def _score_predictions(
    rows: list[dict[str, Any]],
    predictions: dict[str, dict[str, str]],
) -> dict[str, Any]:
    scored_rows = [
        r
        for r in rows
        if r["event_id"] in predictions
        and all(
            isinstance(predictions[r["event_id"]].get(k), str)
            for k in ("medication_class", "side_effect_signal", "adherence_signal")
        )
    ]
    if not scored_rows:
        return {
            "medication_class_macro_f1": 0.0,
            "side_effect_signal_macro_f1": 0.0,
            "adherence_signal_macro_f1": 0.0,
            "parse_success_rate": 0.0,
            "n_test": len(rows),
            "n_parsed": 0,
        }

    y_med = [ground_truth_medication_class(r["label"]) for r in scored_rows]
    y_se = [ground_truth_side_effect_signal(r["label"]) for r in scored_rows]
    y_ad = [ground_truth_adherence_signal(r["label"]) for r in scored_rows]
    pred_med = [predictions[r["event_id"]]["medication_class"] for r in scored_rows]
    pred_se = [predictions[r["event_id"]]["side_effect_signal"] for r in scored_rows]
    pred_ad = [predictions[r["event_id"]]["adherence_signal"] for r in scored_rows]

    parse_rate = len(scored_rows) / len(rows) if rows else 0.0
    return {
        "medication_class_macro_f1": float(
            f1_score(y_med, pred_med, average="macro", zero_division=0)
        ),
        "side_effect_signal_macro_f1": float(
            f1_score(y_se, pred_se, average="macro", zero_division=0)
        ),
        "adherence_signal_macro_f1": float(
            f1_score(y_ad, pred_ad, average="macro", zero_division=0)
        ),
        "parse_success_rate": float(parse_rate),
        "n_test": len(rows),
        "n_parsed": len(scored_rows),
    }


def _aggregate_seed_metrics(seed_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not seed_metrics:
        return {
            "medication_class_macro_f1": None,
            "side_effect_signal_macro_f1": None,
            "adherence_signal_macro_f1": None,
            "parse_success_rate": None,
        }
    keys = (
        "medication_class_macro_f1",
        "side_effect_signal_macro_f1",
        "adherence_signal_macro_f1",
        "parse_success_rate",
    )
    out: dict[str, Any] = {}
    for key in keys:
        vals = [m[key] for m in seed_metrics if m.get(key) is not None]
        out[key] = float(sum(vals) / len(vals)) if vals else None
    out["n_test"] = seed_metrics[0].get("n_test", 0)
    out["n_parsed"] = seed_metrics[0].get("n_parsed", 0)
    return out


def _evaluate_model_on_rows(
    rows: list[dict[str, Any]],
    *,
    cfg: dict[str, Any],
    root: Path,
    model: str,
    vocab: dict[str, list[str]],
    system_prompt: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    tcfg = _tier1_cfg(cfg)
    seed_metrics: list[dict[str, Any]] = []
    per_seed: dict[str, dict[str, Any]] = {}

    for seed in tcfg["eval_seeds"]:
        try:
            preds = predict_rows(
                rows,
                cfg=cfg,
                root=root,
                model=model,
                seed=seed,
                condition_id=rows[0]["export"]["condition_id"],
                vocab=vocab,
                system_prompt=system_prompt,
                client=client,
            )
            scored = _score_predictions(rows, preds)
            seed_metrics.append(scored)
            per_seed[str(seed)] = scored
        except (httpx.HTTPError, httpx.ConnectError, OSError) as exc:
            return {
                "status": "error",
                "reason": str(exc),
                "model": model,
                "medication_class_macro_f1": None,
                "side_effect_signal_macro_f1": None,
                "adherence_signal_macro_f1": None,
            }

    agg = _aggregate_seed_metrics(seed_metrics)
    return {
        "status": "ok",
        "model": model,
        "prompt_version": PROMPT_VERSION,
        **agg,
        "per_seed": per_seed,
    }


def evaluate_tier1_analytics(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    cfg: dict[str, Any],
    *,
    root: Path | None = None,
    max_events: int | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Run Tier-1 LLM analytics triage on test exports; sensitivity models test-only."""
    del train_rows  # zero-shot consumer; train rows unused

    if not test_rows:
        return {
            "status": "ok",
            "reason": "no test rows",
            "medication_class_macro_f1": None,
            "side_effect_signal_macro_f1": None,
            "adherence_signal_macro_f1": None,
            "n_test": 0,
        }

    from sbb.config import repo_root as get_repo_root

    data_root = get_repo_root()
    cache_root = root or data_root
    tcfg = _tier1_cfg(cfg)
    vocab = load_analytics_vocab(data_root, cfg)
    system_prompt = build_analytics_system_prompt(vocab)

    eval_rows = test_rows[:max_events] if max_events else test_rows

    primary = _evaluate_model_on_rows(
        eval_rows,
        cfg=cfg,
        root=cache_root,
        model=tcfg["primary_model"],
        vocab=vocab,
        system_prompt=system_prompt,
        client=client,
    )
    if primary.get("status") == "error":
        return primary

    result: dict[str, Any] = {
        "status": "ok",
        "model": tcfg["primary_model"],
        "prompt_version": PROMPT_VERSION,
        "medication_class_macro_f1": primary["medication_class_macro_f1"],
        "side_effect_signal_macro_f1": primary["side_effect_signal_macro_f1"],
        "adherence_signal_macro_f1": primary["adherence_signal_macro_f1"],
        "parse_success_rate": primary.get("parse_success_rate"),
        "n_test": primary.get("n_test", len(eval_rows)),
        "n_parsed": primary.get("n_parsed"),
        "per_seed": primary.get("per_seed", {}),
    }

    if tcfg["run_sensitivity_on_test_only"] and tcfg["sensitivity_models"]:
        sensitivity: dict[str, Any] = {}
        for model in tcfg["sensitivity_models"]:
            sens = _evaluate_model_on_rows(
                eval_rows,
                cfg=cfg,
                root=cache_root,
                model=model,
                vocab=vocab,
                system_prompt=system_prompt,
                client=client,
            )
            sensitivity[model] = {
                k: sens.get(k)
                for k in (
                    "status",
                    "medication_class_macro_f1",
                    "side_effect_signal_macro_f1",
                    "adherence_signal_macro_f1",
                    "parse_success_rate",
                    "n_test",
                    "reason",
                )
            }
        result["sensitivity"] = sensitivity

    return result
