"""Analytics consumer inputs and Tier-0 evaluators for Ta-1/2/3."""

from __future__ import annotations

import json
from typing import Any

from sklearn.metrics import accuracy_score, f1_score

from eval.observability_task import condition_kind, consumer_input
from eval.tier0_consumer import _fit_predict

TEXT_CONDITIONS = frozenset(
    {"raw", "redact_bracket", "redact_tokenize", "redact_surrogate"}
)
SEMANTIC_CONDITIONS = frozenset({"sem_coarse", "sem_medium", "sem_fine"})

ANALYTICS_TASKS = {
    "ta_med_class": "medication_class",
    "ta_side_effect": "side_effect_signal",
    "ta_adherence": "adherence_signal",
}


def ground_truth_medication_class(label: dict[str, Any]) -> str:
    return label["medication_class"]


def ground_truth_side_effect_signal(label: dict[str, Any]) -> str:
    return "present" if label.get("side_effect") else "absent"


def ground_truth_adherence_signal(label: dict[str, Any]) -> str:
    return "barrier" if label.get("adherence_barrier") else "none"


def ground_truth_side_effect_present(label: dict[str, Any]) -> bool:
    return bool(label.get("side_effect"))


def ground_truth_adherence_friction(label: dict[str, Any]) -> bool:
    return bool(label.get("adherence_barrier"))


def ground_truth_for_task(task_id: str, label: dict[str, Any]) -> Any:
    if task_id == "ta_med_class":
        return ground_truth_medication_class(label)
    if task_id == "ta_side_effect":
        return ground_truth_side_effect_signal(label)
    if task_id == "ta_adherence":
        return ground_truth_adherence_signal(label)
    raise ValueError(f"Unknown analytics task: {task_id}")


def _coarse_consumer_input(export: dict[str, Any]) -> dict[str, Any]:
    z = export["z"]
    flat: dict[str, Any] = {}
    for key, value in z.items():
        if isinstance(value, list):
            flat[key] = "|".join(str(v) for v in value)
        else:
            flat[key] = value
    return flat


def analytics_consumer_input(export: dict[str, Any]) -> str | dict[str, Any]:
    condition_id = export["condition_id"]
    if condition_id == "sem_coarse":
        return _coarse_consumer_input(export)
    return consumer_input(export)


def serialize_for_transfer(export: dict[str, Any]) -> str:
    payload = analytics_consumer_input(export)
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, sort_keys=True)


def evaluate_analytics_tier0(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    *,
    seed: int = 42,
) -> dict[str, float]:
    if not test_rows:
        return {
            "medication_class_macro_f1": 0.0,
            "side_effect_signal_macro_f1": 0.0,
            "adherence_signal_macro_f1": 0.0,
            "side_effect_present_f1": 0.0,
            "adherence_friction_f1": 0.0,
            "n_train": len(train_rows),
            "n_test": 0,
        }

    condition_id = train_rows[0]["export"]["condition_id"]
    kind = condition_kind(condition_id)
    if condition_id == "sem_coarse":
        kind = "semantic"

    train_x = [analytics_consumer_input(r["export"]) for r in train_rows]
    test_x = [analytics_consumer_input(r["export"]) for r in test_rows]

    y_med_train = [ground_truth_medication_class(r["label"]) for r in train_rows]
    y_med_test = [ground_truth_medication_class(r["label"]) for r in test_rows]
    y_se_train = [ground_truth_side_effect_signal(r["label"]) for r in train_rows]
    y_se_test = [ground_truth_side_effect_signal(r["label"]) for r in test_rows]
    y_ad_train = [ground_truth_adherence_signal(r["label"]) for r in train_rows]
    y_ad_test = [ground_truth_adherence_signal(r["label"]) for r in test_rows]

    pred_med = _fit_predict(train_x, y_med_train, test_x, kind=kind, seed=seed)
    pred_se = _fit_predict(train_x, y_se_train, test_x, kind=kind, seed=seed)
    pred_ad = _fit_predict(train_x, y_ad_train, test_x, kind=kind, seed=seed)

    result = {
        "medication_class_macro_f1": float(
            f1_score(y_med_test, pred_med, average="macro", zero_division=0)
        ),
        "side_effect_signal_macro_f1": float(
            f1_score(y_se_test, pred_se, average="macro", zero_division=0)
        ),
        "adherence_signal_macro_f1": float(
            f1_score(y_ad_test, pred_ad, average="macro", zero_division=0)
        ),
        "n_train": len(train_rows),
        "n_test": len(test_rows),
    }

    if condition_id == "sem_coarse":
        y_sep_train = [ground_truth_side_effect_present(r["label"]) for r in train_rows]
        y_sep_test = [ground_truth_side_effect_present(r["label"]) for r in test_rows]
        y_af_train = [ground_truth_adherence_friction(r["label"]) for r in train_rows]
        y_af_test = [ground_truth_adherence_friction(r["label"]) for r in test_rows]
        pred_sep = _fit_predict(train_x, y_sep_train, test_x, kind=kind, seed=seed)
        pred_af = _fit_predict(train_x, y_af_train, test_x, kind=kind, seed=seed)
        result["side_effect_present_f1"] = float(
            f1_score(y_sep_test, pred_sep, average="binary", zero_division=0)
        )
        result["adherence_friction_f1"] = float(
            f1_score(y_af_test, pred_af, average="binary", zero_division=0)
        )

    return result


def evaluate_analytics_transfer(
    raw_train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_condition_id: str,
    *,
    seed: int = 42,
) -> dict[str, Any]:
    if not test_rows:
        return {
            "train_condition": "raw",
            "test_condition": test_condition_id,
            "transfer_medication_class_macro_f1": 0.0,
            "transfer_side_effect_signal_macro_f1": 0.0,
            "transfer_adherence_signal_macro_f1": 0.0,
            "n_train": len(raw_train_rows),
            "n_test": 0,
        }

    from eval.observability_task import serialize_text_export

    train_x = [serialize_text_export(r["export"]["z"]) for r in raw_train_rows]
    test_kind = condition_kind(test_condition_id)
    if test_kind == "text":
        test_x = [serialize_text_export(r["export"]["z"]) for r in test_rows]
    else:
        test_x = [serialize_for_transfer(r["export"]) for r in test_rows]

    y_med_train = [ground_truth_medication_class(r["label"]) for r in raw_train_rows]
    y_med_test = [ground_truth_medication_class(r["label"]) for r in test_rows]
    y_se_train = [ground_truth_side_effect_signal(r["label"]) for r in raw_train_rows]
    y_se_test = [ground_truth_side_effect_signal(r["label"]) for r in test_rows]
    y_ad_train = [ground_truth_adherence_signal(r["label"]) for r in raw_train_rows]
    y_ad_test = [ground_truth_adherence_signal(r["label"]) for r in test_rows]

    pred_med = _fit_predict(train_x, y_med_train, test_x, kind="text", seed=seed)
    pred_se = _fit_predict(train_x, y_se_train, test_x, kind="text", seed=seed)
    pred_ad = _fit_predict(train_x, y_ad_train, test_x, kind="text", seed=seed)

    return {
        "train_condition": "raw",
        "test_condition": test_condition_id,
        "transfer_medication_class_macro_f1": float(
            f1_score(y_med_test, pred_med, average="macro", zero_division=0)
        ),
        "transfer_side_effect_signal_macro_f1": float(
            f1_score(y_se_test, pred_se, average="macro", zero_division=0)
        ),
        "transfer_adherence_signal_macro_f1": float(
            f1_score(y_ad_test, pred_ad, average="macro", zero_division=0)
        ),
        "n_train": len(raw_train_rows),
        "n_test": len(test_rows),
    }


def composite_utility(utility: dict[str, float]) -> float:
    """Primary U_analytics: mean of Ta-1/2/3 macro-F1 (event-level)."""
    keys = (
        "medication_class_macro_f1",
        "side_effect_signal_macro_f1",
        "adherence_signal_macro_f1",
    )
    vals = [utility.get(k, 0.0) for k in keys]
    return sum(vals) / len(vals) if vals else 0.0
