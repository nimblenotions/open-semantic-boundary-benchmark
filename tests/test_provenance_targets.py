"""Tests for provenance_targets.jsonl generator."""

from __future__ import annotations

import pytest

from generate.provenance_targets import (
    build_provenance_row,
    generate_provenance_targets,
    validate_provenance_targets,
    write_provenance_targets,
)
from sbb.config import load_config, repo_root
from transform.io import load_jsonl


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "cikm_v0.1.yaml")


def test_build_provenance_row_evt_000010(cfg):
    root = repo_root()
    labels = {
        r["event_id"]: r
        for r in load_jsonl(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    }
    events = {
        r["event_id"]: r for r in load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")
    }
    personas = {
        r["persona_id"]: r
        for r in load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    }

    label = labels["evt_000010"]
    row = build_provenance_row(label, events["evt_000010"], personas[label["persona_id"]])

    assert row["event_id"] == "evt_000010"
    assert row["persona_id"] == "persona_001"
    assert row["linkage_oracle"]["persona_id"] == "persona_001"
    assert row["linkage_oracle"]["medication_class"] == "SNRI"
    assert row["linkage_oracle"]["symptom_categories"] == [
        "vestibular",
        "gastrointestinal",
    ]
    assert row["observability_oracle"]["failure_mode"] == "missed_safety_escalation"
    assert row["trial4_attack_map"]["token_recovery"] == "raw_surface_forms"
    assert isinstance(row["leakage_oracle"]["raw_surface_forms"], list)


def test_generate_provenance_targets_row_count(cfg):
    root = repo_root()
    rows, exemplars = generate_provenance_targets(cfg, root)
    events = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")

    assert len(rows) == len(events) == 3894
    ok, failures = validate_provenance_targets(rows, expected_event_count=len(events))
    assert ok, failures
    assert set(exemplars) == {"E1", "E2", "E3"}
    assert exemplars["E1"]["event_id"] == "evt_000010"

    e2_id = exemplars["E2"]["event_id"]
    e2_row = next(r for r in rows if r["event_id"] == e2_id)
    assert e2_row["split"] == "test"
    assert e2_row["linkage_oracle"]["quasi_id_rarity"] == "rare"
    assert e2_row["exemplar_id"] == "E2"

    e3_id = exemplars["E3"]["event_id"]
    e3_row = next(r for r in rows if r["event_id"] == e3_id)
    assert e3_row["split"] == "test"
    assert e3_row["observability_oracle"]["failure_mode"] != "assistant_ok"
    assert e3_row["observability_oracle"]["error_stage"] != "none"
    assert e3_row["exemplar_id"] == "E3"


def test_write_provenance_targets_creates_files(cfg, tmp_path):
    root = repo_root()
    stats = write_provenance_targets(cfg, root, output_dir=tmp_path)
    assert stats["row_count"] == 3894
    assert (tmp_path / "provenance_targets.jsonl").is_file()
    assert (tmp_path / "exemplars.json").is_file()


def test_committed_provenance_targets_match_generator_sets(cfg):
    """Committed JSONL must match generator content; list order of case variants is ignored."""
    root = repo_root()
    rows, _ = generate_provenance_targets(cfg, root)
    committed = load_jsonl(root / cfg["paths"]["ground_truth"] / "provenance_targets.jsonl")
    assert [r["event_id"] for r in committed] == [r["event_id"] for r in rows]
    for got, want in zip(committed, rows, strict=True):
        got_forms = got["leakage_oracle"]["raw_surface_forms"]
        want_forms = want["leakage_oracle"]["raw_surface_forms"]
        assert set(got_forms) == set(want_forms), got["event_id"]
        got_rest = {k: v for k, v in got.items() if k != "leakage_oracle"}
        want_rest = {k: v for k, v in want.items() if k != "leakage_oracle"}
        assert got_rest == want_rest, got["event_id"]
        got_leak = {k: v for k, v in got["leakage_oracle"].items() if k != "raw_surface_forms"}
        want_leak = {k: v for k, v in want["leakage_oracle"].items() if k != "raw_surface_forms"}
        assert got_leak == want_leak, got["event_id"]
