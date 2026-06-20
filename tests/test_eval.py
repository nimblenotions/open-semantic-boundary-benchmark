"""Phase 3 eval harness tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.adversary import token_recovery_rate
from eval.io import join_eval_rows, load_labels, load_splits
from transform.io import condition_has_exports, load_condition_exports
from eval.observability_task import condition_kind, consumer_input, serialize_text_export
from eval.provenance_score import provenance_complete
from eval.io import load_raw_events
from eval.study import (
    LLM_CONDITIONS,
    LATTICE_RULE_SEMANTIC,
    merge_obs_metrics,
    resolve_eval_conditions,
    run_study,
)
from sbb.config import repo_root


@pytest.fixture
def cfg():
    from sbb.config import load_config

    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


def test_condition_kind_matches_lattice(cfg):
    for condition_id in cfg["lattice"]["conditions"]:
        assert condition_kind(condition_id) in {"text", "semantic"}


def test_lattice_has_nine_primary_conditions(cfg):
    assert len(cfg["lattice"]["conditions"]) == 9
    assert LLM_CONDITIONS.issubset(set(cfg["lattice"]["conditions"]))
    assert LATTICE_RULE_SEMANTIC.issubset(set(cfg["lattice"]["conditions"]))


def test_config_pilot_v2_split(cfg):
    assert cfg["corpus"]["persona_count"] == 100
    assert cfg["corpus"]["train_ratio"] == 0.70
    assert cfg["corpus"]["test_ratio"] == 0.20
    assert cfg["outputs"]["pilot_dir"] == "outputs/pilot_v2"


def test_join_eval_rows_respects_split(cfg):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    exports = load_condition_exports(root / cfg["paths"]["transformed"] / "raw")
    test_rows = join_eval_rows(labels, exports, splits, split="test")
    assert test_rows
    assert all(r["split"] == "test" for r in test_rows)


def test_provenance_complete_on_transformed_raw(cfg):
    root = repo_root()
    exports = load_condition_exports(root / cfg["paths"]["transformed"] / "raw")
    assert provenance_complete(exports["evt_000001"])


def test_token_recovery_lower_for_bracket_than_raw(cfg):
    root = repo_root()
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    splits = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    raw_by_id = load_raw_events(root / cfg["paths"]["raw"] / "events.jsonl")
    train_rows = join_eval_rows(
        labels,
        load_condition_exports(root / cfg["paths"]["transformed"] / "redact_bracket"),
        splits,
        split="train",
    )
    raw_rows = join_eval_rows(
        labels,
        load_condition_exports(root / cfg["paths"]["transformed"] / "raw"),
        splits,
        split="train",
    )
    bracket_recovery = token_recovery_rate(train_rows[:50], raw_by_id)
    raw_recovery = token_recovery_rate(raw_rows[:50], raw_by_id)
    assert bracket_recovery <= raw_recovery


def test_resolve_eval_conditions_includes_primary_lattice(cfg):
    root = repo_root()
    resolved = resolve_eval_conditions(cfg, root)
    primary = [cid for cid, role in resolved if role == "primary"]
    assert primary == cfg["lattice"]["conditions"]


def test_run_study_writes_metrics(cfg, tmp_path):
    root = repo_root()
    result = run_study(cfg, root, tier="0")
    assert "conditions" in result
    primary_in_result = {
        cid for cid, m in result["conditions"].items() if m.get("role") == "primary"
    }
    assert primary_in_result == set(cfg["lattice"]["conditions"])
    for metrics in result["conditions"].values():
        assert "tier0" in metrics
        assert "failure_mode_macro_f1" in metrics["tier0"]["utility"]
        assert "persona_top1" in metrics["tier0"]["risk"]
        assert "trial4_adversary" in metrics["tier0"]
        assert "combined_linkage_score" in metrics["tier0"]["trial4_adversary"]
        assert "transfer" in metrics
        assert "transfer_failure_mode_macro_f1" in metrics["transfer"]
    assert "hypotheses" in result
    assert "H4" in result["hypotheses"]


def test_run_study_linkage_tier(cfg):
    root = repo_root()
    result = run_study(cfg, root, tier="linkage")
    assert result["tier"] == "linkage"
    raw = result["conditions"]["raw"]
    assert "tier0" not in raw
    assert "tier1" not in raw
    assert "trial4_adversary" in raw
    assert "combined_linkage_score" in raw["trial4_adversary"]
    assert "token_recovery_rate" in raw["trial4_adversary"]
    assert "transfer" in raw
    assert "H4" in result["hypotheses"]


def test_merge_obs_metrics_preserves_linkage_when_adding_tier1():
    existing = {
        "conditions": {
            "raw": {
                "role": "primary",
                "trial4_adversary": {"combined_linkage_score": 0.42},
                "transfer": {"transfer_failure_mode_macro_f1": 0.5},
            }
        },
        "hypotheses": {"H1": {"supported": True}},
    }
    new = {
        "conditions": {
            "raw": {
                "role": "primary",
                "tier1": {"failure_mode_macro_f1": 0.6, "status": "ok"},
            }
        },
        "hypotheses": {},
    }
    merged = merge_obs_metrics(existing, new)
    raw = merged["conditions"]["raw"]
    assert raw["trial4_adversary"]["combined_linkage_score"] == 0.42
    assert raw["tier1"]["failure_mode_macro_f1"] == 0.6
    assert merged["hypotheses"]["H1"]["supported"] is True


def test_text_consumer_input_is_string():
    export = {
        "condition_id": "raw",
        "z": {"journal_text": "hello", "assistant_text": "world"},
    }
    assert isinstance(consumer_input(export), str)
    assert "hello" in serialize_text_export(export["z"])
