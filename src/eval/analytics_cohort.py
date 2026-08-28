"""Opt 5: persona-level cohort analytics (Ta-5) from 30-day event aggregates.

Cohort evaluation modes (post-acceptance audit; frozen paper uses mixed_frozen):

* ``mixed_frozen`` — train on export aggregates, test on assessor aggregates
  (``evaluate_cohort_from_tier1_predictions``; reported ``tier1_cohort``).
* ``export_symmetric`` — train and test on export aggregates
  (``evaluate_cohort_tasks``; reported ``cohort``).
* ``assessor_symmetric`` — train and test on analytics-assessor aggregates
  (``evaluate_cohort_from_assessor_predictions``).
"""

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


COHORT_MODES = ("mixed_frozen", "export_symmetric", "assessor_symmetric")
FEATURE_MODES = ("all", "event_count_only", "no_event_count", "shared")


def apply_feature_mode(
    train_x: list[dict[str, Any]],
    test_x: list[dict[str, Any]],
    mode: str = "all",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Restrict persona feature dicts. Does not mutate inputs."""
    if mode in (None, "all"):
        return train_x, test_x
    if mode == "event_count_only":
        return (
            [{"event_count": d.get("event_count", 0)} for d in train_x],
            [{"event_count": d.get("event_count", 0)} for d in test_x],
        )
    if mode == "no_event_count":

        def _drop(d: dict[str, Any]) -> dict[str, Any]:
            return {k: v for k, v in d.items() if k != "event_count"}

        return [_drop(d) for d in train_x], [_drop(d) for d in test_x]
    if mode == "shared":
        train_keys: set[str] = set()
        test_keys: set[str] = set()
        for d in train_x:
            train_keys.update(d)
        for d in test_x:
            test_keys.update(d)
        shared = train_keys & test_keys

        def _keep(d: dict[str, Any]) -> dict[str, Any]:
            return {k: v for k, v in d.items() if k in shared}

        return [_keep(d) for d in train_x], [_keep(d) for d in test_x]
    raise ValueError(f"unknown feature mode: {mode}")


def inspect_feature_schema(
    train_x: list[dict[str, Any]],
    test_x: list[dict[str, Any]],
) -> dict[str, Any]:
    """Train/test key overlap and DictVectorizer drop/zero rates."""
    train_keys = sorted({k for d in train_x for k in d})
    test_keys = sorted({k for d in test_x for k in d})
    train_set, test_set = set(train_keys), set(test_keys)
    intersection = sorted(train_set & test_set)
    train_only = sorted(train_set - test_set)
    test_only = sorted(test_set - train_set)

    vec = DictVectorizer(sparse=False)
    vec.fit_transform(train_x) if train_x else None
    test_m = vec.transform(test_x) if train_x and test_x else None
    feature_names = list(vec.get_feature_names_out()) if train_x else []

    always_zero = 0
    if test_m is not None and test_m.size:
        always_zero = int((test_m == 0).all(axis=0).sum())
    n_dim = len(feature_names)
    dropped_test_keys = [k for k in test_keys if k not in feature_names]

    return {
        "train_keys": train_keys,
        "test_keys": test_keys,
        "intersection": intersection,
        "train_only_keys": train_only,
        "test_only_keys": test_only,
        "n_train_keys": len(train_keys),
        "n_test_keys": len(test_keys),
        "n_vectorizer_dims": n_dim,
        "n_train_dims_always_zero_at_test": always_zero,
        "frac_train_dims_always_zero_at_test": (
            always_zero / n_dim if n_dim else None
        ),
        "test_keys_dropped": dropped_test_keys,
        "n_test_keys_dropped": len(dropped_test_keys),
        "frac_test_keys_dropped": (
            len(dropped_test_keys) / len(test_keys) if test_keys else None
        ),
        "event_count_in_train": "event_count" in train_set,
        "event_count_in_test": "event_count" in test_set,
    }


def _fit_predict_features(
    train_f: list[dict[str, Any]],
    train_y: list[Any],
    test_f: list[dict[str, Any]],
    *,
    seed: int,
) -> list[Any]:
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


def evaluate_cohort_from_assessor_predictions(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    train_predictions: dict[str, dict[str, str]],
    test_predictions: dict[str, dict[str, str]],
    persona_table: dict[str, dict[str, Any]],
    *,
    seed: int = 42,
    feature_mode: str = "all",
) -> dict[str, float]:
    """Track C: train and test on analytics-assessor 30-day aggregates."""
    train_by_persona = _group_by_persona(train_rows)
    test_by_persona = _group_by_persona(test_rows)
    train_personas = sorted(train_by_persona)
    test_personas = sorted(test_by_persona)

    if not test_personas:
        return {
            "cohort_segment_macro_f1": 0.0,
            "n_train_personas": len(train_personas),
            "n_test_personas": 0,
            "source": "assessor_predictions",
            "cohort_mode": "assessor_symmetric",
            "feature_mode": feature_mode,
        }

    train_x = [
        _persona_features_from_predictions(train_by_persona[pid], train_predictions)
        for pid in train_personas
    ]
    test_x = [
        _persona_features_from_predictions(test_by_persona[pid], test_predictions)
        for pid in test_personas
    ]
    train_x, test_x = apply_feature_mode(train_x, test_x, feature_mode)
    y_train = [cohort_segment(persona_table[pid]) for pid in train_personas]
    y_test = [cohort_segment(persona_table[pid]) for pid in test_personas]
    pred = _fit_predict_features(train_x, y_train, test_x, seed=seed)
    return {
        "cohort_segment_macro_f1": float(
            f1_score(y_test, pred, average="macro", zero_division=0)
        ),
        "n_train_personas": len(train_personas),
        "n_test_personas": len(test_personas),
        "source": "assessor_predictions",
        "cohort_mode": "assessor_symmetric",
        "feature_mode": feature_mode,
    }


def evaluate_cohort_export_symmetric(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    condition_id: str,
    seed: int = 42,
    feature_mode: str = "all",
) -> dict[str, Any]:
    """Track B with optional feature-mode controls."""
    train_by_persona = _group_by_persona(train_rows)
    test_by_persona = _group_by_persona(test_rows)
    train_personas = sorted(train_by_persona)
    test_personas = sorted(test_by_persona)
    train_x = [
        _persona_features(train_by_persona[pid], condition_id=condition_id)
        for pid in train_personas
    ]
    test_x = [
        _persona_features(test_by_persona[pid], condition_id=condition_id)
        for pid in test_personas
    ]
    schema = inspect_feature_schema(train_x, test_x)
    train_x, test_x = apply_feature_mode(train_x, test_x, feature_mode)
    y_train = [cohort_segment(persona_table[pid]) for pid in train_personas]
    y_test = [cohort_segment(persona_table[pid]) for pid in test_personas]
    pred = _fit_predict_features(train_x, y_train, test_x, seed=seed)
    return {
        "cohort_segment_macro_f1": float(
            f1_score(y_test, pred, average="macro", zero_division=0)
        ),
        "n_train_personas": len(train_personas),
        "n_test_personas": len(test_personas),
        "source": "export_aggregates",
        "cohort_mode": "export_symmetric",
        "feature_mode": feature_mode,
        "schema": schema,
    }


def evaluate_cohort_mixed_frozen(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_predictions: dict[str, dict[str, str]],
    persona_table: dict[str, dict[str, Any]],
    *,
    condition_id: str,
    seed: int = 42,
    feature_mode: str = "all",
) -> dict[str, Any]:
    """Track A with optional feature-mode controls (does not replace frozen JSON)."""
    train_by_persona = _group_by_persona(train_rows)
    test_by_persona = _group_by_persona(test_rows)
    train_personas = sorted(train_by_persona)
    test_personas = sorted(test_by_persona)
    train_x = [
        _persona_features(train_by_persona[pid], condition_id=condition_id)
        for pid in train_personas
    ]
    test_x = [
        _persona_features_from_predictions(test_by_persona[pid], test_predictions)
        for pid in test_personas
    ]
    schema = inspect_feature_schema(train_x, test_x)
    train_x, test_x = apply_feature_mode(train_x, test_x, feature_mode)
    y_train = [cohort_segment(persona_table[pid]) for pid in train_personas]
    y_test = [cohort_segment(persona_table[pid]) for pid in test_personas]
    pred = _fit_predict_features(train_x, y_train, test_x, seed=seed)
    return {
        "cohort_segment_macro_f1": float(
            f1_score(y_test, pred, average="macro", zero_division=0)
        ),
        "n_train_personas": len(train_personas),
        "n_test_personas": len(test_personas),
        "source": "tier1_predictions",
        "cohort_mode": "mixed_frozen",
        "feature_mode": feature_mode,
        "schema": schema,
    }
