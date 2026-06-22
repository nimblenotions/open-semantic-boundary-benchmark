"""Tests for embedding retention diagnostic (Option D)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from eval.embeddings import MockEmbedder, cosine_similarity
from eval.retention import (
    evaluate_condition_retention,
    export_text_for_retention,
    raw_text_reference,
    retention_pair,
    run_retention,
)
from eval.observability_task import serialize_text_export
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


@pytest.fixture
def sample_raw_event():
    return {
        "event_id": "evt_test",
        "journal_text": "Patient took meds, feeling anxious.",
        "assistant_text": "Noted. Continue monitoring.",
    }


@pytest.fixture
def sample_text_export(sample_raw_event):
    return {
        "event_id": "evt_test",
        "condition_id": "redact_bracket",
        "z": {
            "journal_text": "Patient took [MED], feeling [SYMPTOM].",
            "assistant_text": "Noted. Continue monitoring.",
        },
    }


@pytest.fixture
def sample_sem_export():
    return {
        "event_id": "evt_test",
        "condition_id": "sem_medium",
        "z": {
            "medication_class": "SSRI",
            "symptom_categories": ["anxiety"],
            "failure_mode": "assistant_ok",
            "error_stage": "none",
        },
    }


def test_cosine_identical_vectors():
    v = np.array([1.0, 0.0, 0.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_raw_text_reference_matches_serialize(sample_raw_event):
    ref = raw_text_reference(sample_raw_event)
    assert "Patient took meds" in ref
    assert "assistant:" in ref


def test_retention_pair_text(sample_raw_event, sample_text_export):
    ref, exp = retention_pair(sample_raw_event, sample_text_export)
    assert ref == raw_text_reference(sample_raw_event)
    assert "[MED]" in exp


def test_retention_pair_semantic_json(sample_raw_event, sample_sem_export):
    ref, exp = retention_pair(sample_raw_event, sample_sem_export)
    assert ref == raw_text_reference(sample_raw_event)
    parsed = json.loads(exp)
    assert parsed["medication_class"] == "SSRI"


def test_export_text_for_retention_text(sample_text_export):
    text = export_text_for_retention(sample_text_export)
    assert text == serialize_text_export(sample_text_export["z"])


def test_mock_embedder_deterministic():
    emb = MockEmbedder(dim=8)
    a = emb.embed(["hello world"])
    b = emb.embed(["hello world"])
    np.testing.assert_allclose(a, b)


def test_evaluate_condition_retention_identity_on_raw(sample_raw_event):
    raw_export = {
        "event_id": "evt_test",
        "condition_id": "raw",
        "z": {
            "journal_text": sample_raw_event["journal_text"],
            "assistant_text": sample_raw_event["assistant_text"],
        },
    }
    exports = {"evt_test": raw_export}
    raw_by_id = {"evt_test": sample_raw_event}
    result = evaluate_condition_retention(
        exports, raw_by_id, MockEmbedder(dim=16)
    )
    assert result["aggregate"]["mean"] == pytest.approx(1.0, abs=1e-6)
    assert result["aggregate"]["n_events"] == 1


def test_run_retention_mock_smoke(cfg, tmp_path, monkeypatch):
    root = repo_root()
    exports_dir = root / cfg["paths"]["transformed"] / "raw"
    if not exports_dir.is_dir():
        pytest.skip("transformed/raw not present")

    result = run_retention(
        cfg,
        root,
        MockEmbedder(dim=16),
        event_ids=["evt_000001", "evt_000002"],
    )
    assert result["metric"] == "embedding_retention_cosine"
    assert result["notes"]["not_primary_metric"] is True
    assert "raw" in result["conditions"]
    raw_row = result["conditions"]["raw"]
    assert raw_row["cosine_mean"] == pytest.approx(1.0, abs=1e-6)
    assert raw_row["kind"] == "text"


def test_run_retention_cli_mock(cfg, tmp_path):
    root = repo_root()
    exports_dir = root / cfg["paths"]["transformed"] / "raw"
    if not exports_dir.is_dir():
        pytest.skip("transformed/raw not present")

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_retention", root / "eval" / "run_retention.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = tmp_path / "retention.json"
    rc = mod.main(
        [
            "--config",
            str(root / "configs" / "pilot_v0.1.1.yaml"),
            "--output",
            str(out),
            "--mock",
            "--sample",
            "5",
        ]
    )
    assert rc == 0
    data = json.loads(out.read_text())
    assert len(data["conditions"]) >= 1
    assert data["notes"]["sampled"] is True


def test_condition_kinds_in_retention(cfg):
    root = repo_root()
    if not (root / cfg["paths"]["transformed"] / "sem_medium").is_dir():
        pytest.skip("transformed exports not present")
    result = run_retention(
        cfg, root, MockEmbedder(), event_ids=["evt_000001"]
    )
    if "sem_medium" in result["conditions"]:
        assert result["conditions"]["sem_medium"]["kind"] == "semantic"
    if "redact_bracket" in result["conditions"]:
        assert result["conditions"]["redact_bracket"]["kind"] == "text"
