"""Cross-condition transfer utility tests."""

from __future__ import annotations

import pytest

from eval.io import join_eval_rows, load_labels, load_splits
from eval.study import run_study
from eval.observability_task import serialize_for_storage, serialize_text_export
from eval.transfer_consumer import (
    TRAIN_CONDITION,
    _test_features,
    _train_features,
    evaluate_transfer,
)
from sbb.config import load_config, repo_root
from transform.io import load_condition_exports


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


@pytest.fixture
def eval_rows(cfg):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    raw_exports = load_condition_exports(root / cfg["paths"]["transformed"] / "raw")
    bracket_exports = load_condition_exports(
        root / cfg["paths"]["transformed"] / "redact_bracket"
    )
    return {
        "raw_train": join_eval_rows(labels, raw_exports, splits, split="train"),
        "raw_test": join_eval_rows(labels, raw_exports, splits, split="test"),
        "bracket_test": join_eval_rows(
            labels, bracket_exports, splits, split="test"
        ),
    }


def test_train_features_always_raw_prose(eval_rows):
    feats = _train_features(eval_rows["raw_train"])
    assert all(isinstance(x, str) for x in feats)
    assert feats[0] == serialize_text_export(eval_rows["raw_train"][0]["export"]["z"])


def test_semantic_test_features_use_flattened_json(eval_rows, cfg):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    sem_test = join_eval_rows(
        labels,
        load_condition_exports(root / cfg["paths"]["transformed"] / "sem_coarse"),
        splits,
        split="test",
    )
    feats = _test_features(sem_test, test_kind="semantic")
    assert all(isinstance(x, str) for x in feats)
    assert feats[0] == serialize_for_storage(sem_test[0]["export"])


def test_semantic_transfer_not_dict_vectorizer_artifact(eval_rows, cfg):
    """Semantic transfer must use TF-IDF strings, not ~0.01 DictVectorizer artifact."""
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    sem_test = join_eval_rows(
        labels,
        load_condition_exports(root / cfg["paths"]["transformed"] / "sem_coarse"),
        splits,
        split="test",
    )
    sem_transfer = evaluate_transfer(
        eval_rows["raw_train"],
        sem_test,
        "sem_coarse",
        seed=42,
    )
    assert sem_transfer["transfer_failure_mode_macro_f1"] > 0.05


def test_transfer_trains_on_raw_only(eval_rows):
    result = evaluate_transfer(
        eval_rows["raw_train"],
        eval_rows["bracket_test"],
        "redact_bracket",
        seed=42,
    )
    assert result["train_condition"] == TRAIN_CONDITION
    assert result["test_condition"] == "redact_bracket"
    assert 0.0 <= result["transfer_failure_mode_macro_f1"] <= 1.0
    assert 0.0 <= result["transfer_error_stage_accuracy"] <= 1.0
    assert result["n_train"] == len(eval_rows["raw_train"])
    assert result["n_test"] == len(eval_rows["bracket_test"])


def test_raw_transfer_matches_tier0_raw_ceiling(eval_rows):
    from eval.tier0_consumer import evaluate_tier0

    transfer = evaluate_transfer(
        eval_rows["raw_train"],
        eval_rows["raw_test"],
        "raw",
        seed=42,
    )
    tier0 = evaluate_tier0(
        eval_rows["raw_train"], eval_rows["raw_test"], seed=42
    )
    assert transfer["transfer_failure_mode_macro_f1"] == pytest.approx(
        tier0["failure_mode_macro_f1"], abs=1e-6
    )


def test_text_transfer_does_not_exceed_raw_ceiling(eval_rows):
    raw_transfer = evaluate_transfer(
        eval_rows["raw_train"],
        eval_rows["raw_test"],
        "raw",
        seed=42,
    )
    bracket_transfer = evaluate_transfer(
        eval_rows["raw_train"],
        eval_rows["bracket_test"],
        "redact_bracket",
        seed=42,
    )
    assert (
        bracket_transfer["transfer_failure_mode_macro_f1"]
        <= raw_transfer["transfer_failure_mode_macro_f1"]
    )


def test_semantic_transfer_below_raw_transfer(eval_rows, cfg):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    sem_test = join_eval_rows(
        labels,
        load_condition_exports(root / cfg["paths"]["transformed"] / "sem_coarse"),
        splits,
        split="test",
    )
    raw_transfer = evaluate_transfer(
        eval_rows["raw_train"],
        eval_rows["raw_test"],
        "raw",
        seed=42,
    )
    sem_transfer = evaluate_transfer(
        eval_rows["raw_train"],
        sem_test,
        "sem_coarse",
        seed=42,
    )
    assert (
        sem_transfer["transfer_failure_mode_macro_f1"]
        < raw_transfer["transfer_failure_mode_macro_f1"] * 0.8
    )


def test_run_study_includes_transfer_block(cfg):
    result = run_study(cfg, repo_root(), tier="0")
    for condition_id, metrics in result["conditions"].items():
        assert "transfer" in metrics, condition_id
        transfer = metrics["transfer"]
        assert "transfer_failure_mode_macro_f1" in transfer
        assert "transfer_error_stage_accuracy" in transfer
        assert transfer["train_condition"] == "raw"
        assert transfer["test_condition"] == condition_id

    h1 = result["hypotheses"]["H1"]
    assert "transfer" in h1
    assert "per_condition" in h1


def test_h1_transfer_hypothesis_supported_when_bracket_drops(cfg):
    result = run_study(cfg, repo_root(), tier="0")
    h1_transfer = result["hypotheses"]["H1"]["transfer"]
    raw_t = result["conditions"]["raw"]["transfer"]["transfer_failure_mode_macro_f1"]
    bracket_t = result["conditions"]["redact_bracket"]["transfer"][
        "transfer_failure_mode_macro_f1"
    ]
    assert h1_transfer["supported"] == (bracket_t < raw_t * 0.8)
