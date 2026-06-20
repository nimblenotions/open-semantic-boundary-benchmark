"""Cross-condition transfer utility: train on raw train split, test per condition."""

from __future__ import annotations

from typing import Any

from sklearn.metrics import accuracy_score, f1_score

from eval.observability_task import (
    condition_kind,
    serialize_for_storage,
    serialize_text_export,
)
from eval.tier0_consumer import _fit_predict

TRAIN_CONDITION = "raw"


def _train_features(raw_train_rows: list[dict[str, Any]]) -> list[str]:
    """Serialize raw train exports as journal+assistant prose for TF-IDF."""
    return [serialize_text_export(r["export"]["z"]) for r in raw_train_rows]


def _test_features(
    test_rows: list[dict[str, Any]], *, test_kind: str
) -> list[str]:
    """Map each test export to a string the raw-trained TF-IDF model can score.

    Text conditions use ``serialize_text_export`` (journal + assistant layout).
    Semantic conditions use ``serialize_for_storage`` (canonical flattened JSON
    via ``json.dumps(flatten_semantic_z(z), sort_keys=True)``).
    """
    if test_kind == "text":
        return [serialize_text_export(r["export"]["z"]) for r in test_rows]
    return [serialize_for_storage(r["export"]) for r in test_rows]


def evaluate_transfer(
    raw_train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_condition_id: str,
    *,
    seed: int = 42,
) -> dict[str, Any]:
    """Train Tier-0 TF-IDF on raw train prose; predict on test_condition exports.

    Operational transfer: a consumer trained on raw logs triages each test export
    without retraining. Text tests feed transformed prose; semantic tests feed
    flattened JSON strings.
    """
    if not test_rows:
        return {
            "train_condition": TRAIN_CONDITION,
            "test_condition": test_condition_id,
            "transfer_failure_mode_macro_f1": 0.0,
            "transfer_error_stage_accuracy": 0.0,
            "n_train": len(raw_train_rows),
            "n_test": 0,
        }

    test_kind = condition_kind(test_condition_id)
    train_x = _train_features(raw_train_rows)
    test_x = _test_features(test_rows, test_kind=test_kind)
    y_fail_train = [r["label"]["failure_mode"] for r in raw_train_rows]
    y_fail_test = [r["label"]["failure_mode"] for r in test_rows]
    y_stage_train = [r["label"]["error_stage"] for r in raw_train_rows]
    y_stage_test = [r["label"]["error_stage"] for r in test_rows]

    pred_fail = _fit_predict(
        train_x, y_fail_train, test_x, kind="text", seed=seed
    )
    pred_stage = _fit_predict(
        train_x, y_stage_train, test_x, kind="text", seed=seed
    )

    return {
        "train_condition": TRAIN_CONDITION,
        "test_condition": test_condition_id,
        "transfer_failure_mode_macro_f1": float(
            f1_score(y_fail_test, pred_fail, average="macro", zero_division=0)
        ),
        "transfer_error_stage_accuracy": float(
            accuracy_score(y_stage_test, pred_stage)
        ),
        "n_train": len(raw_train_rows),
        "n_test": len(test_rows),
    }
