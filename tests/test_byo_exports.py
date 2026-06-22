"""BYO sample export: load → join → assessor smoke tests."""

from __future__ import annotations

import pytest

from eval.io import join_eval_rows, load_labels, load_splits
from eval.observability_task import condition_kind
from eval.provenance_score import evaluate_provenance, provenance_complete
from sbb.config import load_config, repo_root
from transform.io import index_by_event_id, load_condition_exports, load_jsonl, write_jsonl_bundle

SAMPLE_PATH = repo_root() / "examples" / "bring_your_own" / "sample_events.jsonl"


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


@pytest.fixture
def sample_exports() -> dict[str, dict]:
    rows = load_jsonl(SAMPLE_PATH)
    assert rows, "sample_events.jsonl must not be empty"
    return index_by_event_id(rows)


def test_byo_sample_file_exists():
    assert SAMPLE_PATH.is_file()


def test_byo_sample_joins_pilot_test_split(cfg, sample_exports):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    rows = join_eval_rows(labels, sample_exports, splits, split="test")
    assert len(rows) == len(sample_exports)
    assert all(r["split"] == "test" for r in rows)
    for row in rows:
        assert row["export"]["condition_id"] == "sem_medium"
        assert condition_kind(row["export"]["condition_id"]) == "semantic"


def test_byo_sample_provenance_complete(sample_exports):
    for event_id, export in sample_exports.items():
        assert provenance_complete(export), event_id
    metrics = evaluate_provenance(sample_exports)
    assert metrics["n_exports"] == len(sample_exports)
    assert metrics["completeness"] == 1.0


def test_byo_sample_via_condition_dir_layout(sample_exports, tmp_path):
    """Mirrors placing exports under data/transformed/{condition}/events.jsonl."""
    condition_dir = tmp_path / "sem_medium"
    write_jsonl_bundle(condition_dir / "events.jsonl", list(sample_exports.values()))
    loaded = load_condition_exports(condition_dir)
    assert loaded == sample_exports
