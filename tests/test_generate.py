"""Phase 1 generator tests."""

from __future__ import annotations

import json

import pytest

from generate.corpus import generate_corpus
from generate.validate import validate_corpus
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def tmp_corpus(tmp_path, cfg, monkeypatch):
    """Generate into a temp directory."""
    cfg = dict(cfg)
    cfg["paths"] = dict(cfg["paths"])
    cfg["paths"]["raw"] = str(tmp_path / "raw")
    cfg["paths"]["ground_truth"] = str(tmp_path / "ground_truth")
    cfg["persona_count"] = 10
    cfg["corpus"] = dict(cfg["corpus"])
    cfg["corpus"]["persona_count"] = 10
    generate_corpus(cfg, tmp_path)
    return tmp_path, cfg


def test_generate_meets_smoke_floors(tmp_corpus):
    root, cfg = tmp_corpus
    ok, report = validate_corpus(cfg, root)
    assert ok, report["failures"]
    assert report["event_count"] >= cfg["corpus"]["smoke"]["min_events"]


def test_events_have_journal_and_assistant(tmp_corpus):
    root, cfg = tmp_corpus
    events_path = root / cfg["paths"]["raw"] / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    assert events
    for ev in events[:5]:
        assert ev["journal_text"]
        assert ev["assistant_text"]
        assert ev["event_id"].startswith("evt_")


def test_labels_align_with_events(tmp_corpus):
    root, cfg = tmp_corpus
    events = [
        json.loads(line)
        for line in (root / cfg["paths"]["raw"] / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    labels = [
        json.loads(line)
        for line in (root / cfg["paths"]["ground_truth"] / "labels.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert {e["event_id"] for e in events} == {label["event_id"] for label in labels}


def test_anchor_failure_mode_present(tmp_corpus):
    root, cfg = tmp_corpus
    labels = [
        json.loads(line)
        for line in (root / cfg["paths"]["ground_truth"] / "labels.jsonl").read_text().splitlines()
        if line.strip()
    ]
    modes = {label["failure_mode"] for label in labels}
    assert "missed_safety_escalation" in modes
    anchor = [label for label in labels if label["failure_mode"] == "missed_safety_escalation"][0]
    assert anchor["error_stage"] == "risk_recognition"


def test_repo_smoke_generate(cfg):
    """Optional: run against repo data if present."""
    root = repo_root()
    events = root / "data/raw/events.jsonl"
    if not events.exists():
        pytest.skip("run make generate first")
    ok, report = validate_corpus(cfg, root)
    assert ok, report.get("failures")
