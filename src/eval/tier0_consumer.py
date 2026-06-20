"""Tier-0 sklearn consumer: TF-IDF for text exports, dict features for semantic JSON."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

from eval.observability_task import condition_kind, consumer_input


def _fit_predict(
    train_x: list[Any],
    train_y: list[str],
    test_x: list[Any],
    *,
    kind: str,
    seed: int,
) -> list[str]:
    classes = sorted(set(train_y))
    if len(classes) < 2:
        clf = DummyClassifier(strategy="most_frequent")
        clf.fit(train_x, train_y)
        return list(clf.predict(test_x))

    if kind == "text":
        model: Any = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        max_features=5000,
                        ngram_range=(1, 2),
                        min_df=1,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=seed,
                    ),
                ),
            ]
        )
    else:
        model = Pipeline(
            [
                ("vec", DictVectorizer(sparse=True)),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=seed,
                    ),
                ),
            ]
        )

    model.fit(train_x, train_y)
    return list(model.predict(test_x))


def evaluate_tier0(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    *,
    seed: int = 42,
) -> dict[str, float]:
    if not test_rows:
        return {
            "failure_mode_macro_f1": 0.0,
            "error_stage_accuracy": 0.0,
            "n_train": len(train_rows),
            "n_test": 0,
        }

    condition_id = train_rows[0]["export"]["condition_id"]
    kind = condition_kind(condition_id)

    train_x = [consumer_input(r["export"]) for r in train_rows]
    test_x = [consumer_input(r["export"]) for r in test_rows]
    y_fail_train = [r["label"]["failure_mode"] for r in train_rows]
    y_fail_test = [r["label"]["failure_mode"] for r in test_rows]
    y_stage_train = [r["label"]["error_stage"] for r in train_rows]
    y_stage_test = [r["label"]["error_stage"] for r in test_rows]

    pred_fail = _fit_predict(train_x, y_fail_train, test_x, kind=kind, seed=seed)
    pred_stage = _fit_predict(train_x, y_stage_train, test_x, kind=kind, seed=seed)

    return {
        "failure_mode_macro_f1": float(
            f1_score(y_fail_test, pred_fail, average="macro", zero_division=0)
        ),
        "error_stage_accuracy": float(accuracy_score(y_stage_test, pred_stage)),
        "n_train": len(train_rows),
        "n_test": len(test_rows),
    }
