"""Linkage risk: persona re-identification, attribute inference, token recovery."""

from __future__ import annotations

import re
from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

from eval.observability_task import condition_kind, consumer_input, serialize_text_export
from transform.spans import RULES


def _fit_predict_classifier(
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
                ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)),
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


def _sensitive_surface_forms(text: str) -> set[str]:
    surfaces: set[str] = set()
    for _name, rules, _tag in RULES:
        for rule in rules:
            if isinstance(rule, str):
                for match in re.finditer(re.escape(rule), text, flags=re.I):
                    surfaces.add(match.group(0).lower())
            else:
                for match in rule.finditer(text):
                    surfaces.add(match.group(0).lower())
    return surfaces


def token_recovery_rate(
    rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
) -> float:
    if not rows:
        return 0.0
    if condition_kind(rows[0]["export"]["condition_id"]) != "text":
        return 0.0

    recovered = 0
    total = 0
    for row in rows:
        raw = raw_by_id[row["event_id"]]
        raw_text = f"{raw['journal_text']} {raw['assistant_text']}"
        export_text = serialize_text_export(row["export"]["z"])
        for token in _sensitive_surface_forms(raw_text):
            total += 1
            if token in export_text.lower():
                recovered += 1
    if total == 0:
        return 0.0
    return recovered / total


def evaluate_adversary(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    *,
    seed: int = 42,
) -> dict[str, float]:
    if not test_rows:
        return {
            "persona_top1": 0.0,
            "medication_class_macro_f1": 0.0,
            "token_recovery_rate": 0.0,
            "n_test": 0,
        }

    condition_id = train_rows[0]["export"]["condition_id"]
    kind = condition_kind(condition_id)
    train_x = [consumer_input(r["export"]) for r in train_rows]
    test_x = [consumer_input(r["export"]) for r in test_rows]

    persona_train = [r["persona_id"] for r in train_rows]
    persona_test = [r["persona_id"] for r in test_rows]
    med_train = [r["label"]["medication_class"] for r in train_rows]
    med_test = [r["label"]["medication_class"] for r in test_rows]

    pred_persona = _fit_predict_classifier(
        train_x, persona_train, test_x, kind=kind, seed=seed
    )
    pred_med = _fit_predict_classifier(
        train_x, med_train, test_x, kind=kind, seed=seed
    )

    return {
        "persona_top1": float(accuracy_score(persona_test, pred_persona)),
        "medication_class_macro_f1": float(
            f1_score(med_test, pred_med, average="macro", zero_division=0)
        ),
        "token_recovery_rate": float(token_recovery_rate(test_rows, raw_by_id)),
        "n_test": len(test_rows),
    }
