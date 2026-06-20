"""Opt 5: persona-level cohort analytics (Ta-5) from 30-day event aggregates."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, f1_score

from transform.analytics_map import cohort_segment


def _persona_features(
    persona_events: list[dict[str, Any]],
    *,
    condition_id: str,
) -> dict[str, Any]:
    """Aggregate event-level exports into 30-day persona feature vector."""
    side_effect_count = 0
    adherence_barrier_count = 0
    med_classes: dict[str, int] = defaultdict(int)
    symptom_cats: dict[str, int] = defaultdict(int)
    time_buckets: dict[str, int] = defaultdict(int)

    for row in persona_events:
        z = row["export"]["z"]
        if condition_id == "sem_coarse":
            if z.get("side_effect_present"):
                side_effect_count += 1
            if z.get("adherence_friction_present"):
                adherence_barrier_count += 1
        else:
            if z.get("side_effect_signal") == "present":
                side_effect_count += 1
            if z.get("adherence_signal") == "barrier":
                adherence_barrier_count += 1
            med = z.get("medication_class")
            if med:
                med_classes[med] += 1
            for cat in z.get("symptom_categories", []):
                symptom_cats[cat] += 1
            tb = z.get("time_bucket")
            if tb:
                time_buckets[tb] += 1

    n = max(len(persona_events), 1)
    features: dict[str, Any] = {
        "event_count": len(persona_events),
        "side_effect_rate": side_effect_count / n,
        "adherence_barrier_rate": adherence_barrier_count / n,
    }
    for med, count in med_classes.items():
        features[f"med_{med}"] = count / n
    for cat, count in symptom_cats.items():
        features[f"sym_{cat}"] = count / n
    for tb, count in time_buckets.items():
        features[f"time_{tb}"] = count / n
    return features


def _persona_features_from_predictions(
    persona_events: list[dict[str, Any]],
    predictions: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Aggregate Tier-1 event predictions into persona feature vector."""
    side_effect_count = 0
    adherence_barrier_count = 0
    med_classes: dict[str, int] = defaultdict(int)

    for row in persona_events:
        pred = predictions.get(row["event_id"], {})
        if pred.get("side_effect_signal") == "present":
            side_effect_count += 1
        if pred.get("adherence_signal") == "barrier":
            adherence_barrier_count += 1
        med = pred.get("medication_class")
        if med:
            med_classes[str(med)] += 1

    n = max(len(persona_events), 1)
    features: dict[str, Any] = {
        "event_count": len(persona_events),
        "side_effect_rate": side_effect_count / n,
        "adherence_barrier_rate": adherence_barrier_count / n,
    }
    for med, count in med_classes.items():
        features[f"med_{med}"] = count / n
    return features


def evaluate_cohort_from_tier1_predictions(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_predictions: dict[str, dict[str, str]],
    persona_table: dict[str, dict[str, Any]],
    *,
    condition_id: str,
    seed: int = 42,
) -> dict[str, float]:
    """Persona-level cohort Ta-5: train on export aggregates, test on Tier-1 prediction aggregates."""
    train_by_persona = _group_by_persona(train_rows)
    test_by_persona = _group_by_persona(test_rows)
    train_personas = sorted(train_by_persona)
    test_personas = sorted(test_by_persona)

    if not test_personas:
        return {
            "adherence_trajectory_macro_f1": 0.0,
            "quasi_id_rarity_accuracy": 0.0,
            "cohort_segment_macro_f1": 0.0,
            "n_train_personas": len(train_personas),
            "n_test_personas": 0,
            "source": "tier1_predictions",
        }

    train_x = [
        _persona_features(train_by_persona[pid], condition_id=condition_id)
        for pid in train_personas
    ]
    test_x = [
        _persona_features_from_predictions(test_by_persona[pid], test_predictions)
        for pid in test_personas
    ]

    y_traj_train = [persona_table[pid]["adherence_trajectory"] for pid in train_personas]
    y_traj_test = [persona_table[pid]["adherence_trajectory"] for pid in test_personas]
    y_rarity_train = [persona_table[pid]["quasi_id_rarity"] for pid in train_personas]
    y_rarity_test = [persona_table[pid]["quasi_id_rarity"] for pid in test_personas]
    y_cohort_train = [cohort_segment(persona_table[pid]) for pid in train_personas]
    y_cohort_test = [cohort_segment(persona_table[pid]) for pid in test_personas]

    def _fit_predict(train_f, train_y, test_f, test_y):
        classes = sorted(set(train_y))
        if len(classes) < 2:
            clf = DummyClassifier(strategy="most_frequent")
            clf.fit(train_f, train_y)
            return list(clf.predict(test_f))
        vec = DictVectorizer(sparse=False)
        train_xm = vec.fit_transform(train_f)
        test_xm = vec.transform(test_f)
        clf = RandomForestClassifier(
            n_estimators=50, random_state=seed, class_weight="balanced"
        )
        clf.fit(train_xm, train_y)
        return list(clf.predict(test_xm))

    pred_traj = _fit_predict(train_x, y_traj_train, test_x, y_traj_test)
    pred_rarity = _fit_predict(train_x, y_rarity_train, test_x, y_rarity_test)
    pred_cohort = _fit_predict(train_x, y_cohort_train, test_x, y_cohort_test)

    return {
        "adherence_trajectory_macro_f1": float(
            f1_score(y_traj_test, pred_traj, average="macro", zero_division=0)
        ),
        "quasi_id_rarity_accuracy": float(accuracy_score(y_rarity_test, pred_rarity)),
        "cohort_segment_macro_f1": float(
            f1_score(y_cohort_test, pred_cohort, average="macro", zero_division=0)
        ),
        "n_train_personas": len(train_personas),
        "n_test_personas": len(test_personas),
        "source": "tier1_predictions",
    }


def _group_by_persona(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["persona_id"]].append(row)
    return grouped


def evaluate_cohort_tasks(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    condition_id: str,
    seed: int = 42,
) -> dict[str, float]:
    """Predict adherence_trajectory and quasi_id_rarity from persona aggregates."""
    train_by_persona = _group_by_persona(train_rows)
    test_by_persona = _group_by_persona(test_rows)

    train_personas = sorted(train_by_persona)
    test_personas = sorted(test_by_persona)

    if not test_personas:
        return {
            "adherence_trajectory_macro_f1": 0.0,
            "quasi_id_rarity_accuracy": 0.0,
            "cohort_segment_macro_f1": 0.0,
            "n_train_personas": len(train_personas),
            "n_test_personas": 0,
        }

    train_x = [
        _persona_features(train_by_persona[pid], condition_id=condition_id)
        for pid in train_personas
    ]
    test_x = [
        _persona_features(test_by_persona[pid], condition_id=condition_id)
        for pid in test_personas
    ]

    y_traj_train = [
        persona_table[pid]["adherence_trajectory"] for pid in train_personas
    ]
    y_traj_test = [persona_table[pid]["adherence_trajectory"] for pid in test_personas]
    y_rarity_train = [persona_table[pid]["quasi_id_rarity"] for pid in train_personas]
    y_rarity_test = [persona_table[pid]["quasi_id_rarity"] for pid in test_personas]
    y_cohort_train = [cohort_segment(persona_table[pid]) for pid in train_personas]
    y_cohort_test = [cohort_segment(persona_table[pid]) for pid in test_personas]

    def _fit_predict(train_f, train_y, test_f, test_y):
        classes = sorted(set(train_y))
        if len(classes) < 2:
            clf = DummyClassifier(strategy="most_frequent")
            clf.fit(train_f, train_y)
            return list(clf.predict(test_f))
        vec = DictVectorizer(sparse=False)
        train_x = vec.fit_transform(train_f)
        test_x = vec.transform(test_f)
        clf = RandomForestClassifier(
            n_estimators=50, random_state=seed, class_weight="balanced"
        )
        clf.fit(train_x, train_y)
        return list(clf.predict(test_x))

    pred_traj = _fit_predict(train_x, y_traj_train, test_x, y_traj_test)
    pred_rarity = _fit_predict(train_x, y_rarity_train, test_x, y_rarity_test)
    pred_cohort = _fit_predict(train_x, y_cohort_train, test_x, y_cohort_test)

    return {
        "adherence_trajectory_macro_f1": float(
            f1_score(y_traj_test, pred_traj, average="macro", zero_division=0)
        ),
        "quasi_id_rarity_accuracy": float(
            accuracy_score(y_rarity_test, pred_rarity)
        ),
        "cohort_segment_macro_f1": float(
            f1_score(y_cohort_test, pred_cohort, average="macro", zero_division=0)
        ),
        "n_train_personas": len(train_personas),
        "n_test_personas": len(test_personas),
    }
