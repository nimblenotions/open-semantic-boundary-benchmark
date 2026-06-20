"""Boundary bundle v0 and operative bundle validation."""

from __future__ import annotations

import json

import pytest

from eval.boundary_bundle import (
    build_boundary_bundle,
    choose_recommended_condition,
    export_kind_for_condition,
    schema_for_condition,
)
from eval.figures import load_metrics
from eval.operative_selection import build_operative_boundary_bundle, run_operative_selection
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


@pytest.fixture
def pilot_v2_metrics():
    path = repo_root() / "outputs" / "pilot_v2" / "metrics.json"
    if not path.is_file():
        pytest.skip("pilot_v2 metrics.json not present")
    return load_metrics(path)


@pytest.fixture
def pilot_v2_analytics():
    path = repo_root() / "outputs" / "pilot_v2" / "analytics_metrics.json"
    if not path.is_file():
        pytest.skip("pilot_v2 analytics_metrics.json not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_pilot_v2_obs_bundle_recommendation(pilot_v2_metrics, cfg):
    """I1 bundle: bracket wins among Trial4-feasible arms on Tier-1 obs utility."""
    primary = {
        cid: m
        for cid, m in pilot_v2_metrics["conditions"].items()
        if m.get("role") in ("primary", "frozen")
    }
    recommended, rule = choose_recommended_condition(primary)
    assert recommended == "redact_bracket"
    assert "linkage <= redact_bracket" in rule

    bundle = build_boundary_bundle(pilot_v2_metrics, cfg)
    assert bundle["recommended_condition"] == "redact_bracket"
    assert bundle["export_kind"] == "text_redaction"
    assert bundle["schema"] is None
    assert bundle["sbb_version"] == "0.1.1"
    assert bundle["transform_ladder"] == cfg["lattice"]["conditions"]
    assert bundle["i1_metrics_ref"] == "outputs/pilot_v2/metrics.json"


def test_schema_maps_only_semantic_arms(cfg):
    assert schema_for_condition("sem_medium", cfg) == {
        "id": "obs_schema_medium",
        "path": "data/schemas/obs_schema_medium.json",
    }
    assert schema_for_condition("redact_bracket", cfg) is None
    assert export_kind_for_condition("sem_fine") == "semantic"
    assert export_kind_for_condition("raw") == "text_redaction"


def test_operative_bundle_avoids_dominated_raw(pilot_v2_metrics, pilot_v2_analytics, cfg, tmp_path):
    """Operative bundle must not recommend raw when sem_medium is feasible and raw is dominated."""
    out = run_operative_selection(
        pilot_v2_metrics,
        pilot_v2_analytics,
        cfg,
        tmp_path / "operative_selection",
    )
    bundle_path = tmp_path / "operative_selection" / "operative_boundary_bundle_v0.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    assert bundle["artifact_type"] == "operative_boundary_bundle_v0"
    assert bundle["per_perspective_at_r_max_0_45"]["observability"] == "redact_bracket"
    assert bundle["per_perspective_at_r_max_0_45"]["analytics_med_class"] == "redact_surrogate"
    assert bundle["recommended_condition"] == "sem_medium"
    assert "raw" in bundle["conditions_never_deploy_obs"]
    assert "sem_medium" in bundle["task_bundle_dual_purpose_balanced"]["feasible_conditions"]
    assert out["operative_boundary_bundle"].endswith("operative_boundary_bundle_v0.json")


def test_operative_bundle_matches_selection_core(pilot_v2_metrics, pilot_v2_analytics, cfg):
    selection = json.loads(
        (
            repo_root() / "outputs" / "pilot_v2" / "operative_selection" / "operative_selection.json"
        ).read_text(encoding="utf-8")
    )
    bundle = build_operative_boundary_bundle(
        pilot_v2_metrics,
        pilot_v2_analytics,
        cfg,
        selection=selection,
    )
    assert bundle["recommended_condition"] == "sem_medium"
    assert bundle["recommended_condition"] not in bundle["conditions_never_deploy_obs"]
