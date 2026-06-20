"""Analytics eval consumer tests."""

from __future__ import annotations

from eval.analytics_task import (
    composite_utility,
    evaluate_analytics_tier0,
    ground_truth_adherence_signal,
    ground_truth_medication_class,
    ground_truth_side_effect_signal,
)
from eval.io import join_eval_rows, load_labels, load_splits
from sbb.config import load_config, repo_root
from transform.io import load_condition_exports

CFG = load_config()
ROOT = repo_root()


def _sample_rows(condition_id: str, n: int = 80):
    labels = load_labels(ROOT / CFG["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(ROOT / CFG["paths"]["ground_truth"] / "splits.json")
    exports = load_condition_exports(
        ROOT / CFG["paths"]["transformed"] / condition_id
    )
    train = join_eval_rows(labels, exports, splits, split="train")[:n]
    test = join_eval_rows(labels, exports, splits, split="test")[: max(n // 4, 10)]
    return train, test


def test_ground_truth_helpers():
    label = {
        "medication_class": "SNRI",
        "side_effect": True,
        "adherence_barrier": False,
    }
    assert ground_truth_medication_class(label) == "SNRI"
    assert ground_truth_side_effect_signal(label) == "present"
    assert ground_truth_adherence_signal(label) == "none"


def test_composite_utility_mean():
    u = composite_utility(
        {
            "medication_class_macro_f1": 0.6,
            "side_effect_signal_macro_f1": 0.8,
            "adherence_signal_macro_f1": 0.4,
        }
    )
    assert abs(u - 0.6) < 1e-6


def test_tier0_sem_medium_runs():
    train, test = _sample_rows("sem_medium")
    if not train or not test:
        return
    metrics = evaluate_analytics_tier0(train, test, seed=42)
    assert "medication_class_macro_f1" in metrics
    assert "side_effect_signal_macro_f1" in metrics
    assert "adherence_signal_macro_f1" in metrics
    assert metrics["n_test"] > 0
