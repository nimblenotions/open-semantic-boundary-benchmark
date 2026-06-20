"""Phase 4 figure generation tests."""

from __future__ import annotations

import shutil

import pytest

from eval.boundary_bundle import build_boundary_bundle, choose_recommended_condition
from eval.figures import generate_all_figures, load_metrics
from sbb.config import load_config, repo_root


@pytest.fixture
def metrics():
    path = repo_root() / "outputs" / "pilot_v1" / "metrics.json"
    if not path.is_file():
        pytest.skip("I0 metrics.json not present")
    return load_metrics(path)


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


def test_choose_recommended_condition(metrics):
    primary = {
        cid: m
        for cid, m in metrics["conditions"].items()
        if m.get("role") in ("primary", "frozen")
    }
    recommended, rule = choose_recommended_condition(primary)
    assert recommended in primary
    assert "failure_mode_macro_f1" in rule or "linkage" in rule


def test_build_boundary_bundle(metrics, cfg):
    bundle = build_boundary_bundle(metrics, cfg)
    assert bundle["sbb_version"] == "0.1.1"
    assert bundle["recommended_condition"] in cfg["lattice"]["conditions"]
    assert bundle["split_manifest"].endswith("splits.json")
    rec = bundle["recommended_condition"]
    if rec.startswith("sem_"):
        assert bundle["schema"] is not None
        assert bundle["export_kind"] == "semantic"
    else:
        assert bundle["schema"] is None
        assert bundle["export_kind"] == "text_redaction"


def test_generate_figures_from_metrics(metrics, tmp_path):
    out_dir = tmp_path / "figures"
    paths = generate_all_figures(metrics, out_dir)

    expected_stems = [
        "h2_utility_recovery.png",
        "h2_utility_recovery.pdf",
        "r4_summary.csv",
        "r4_summary_table.png",
        "r4_summary_table.pdf",
    ]
    from eval.figures import (
        _has_tier0,
        _has_trial4,
        _has_trial4_components,
        FROZEN_LATTICE,
        H1_CONDITIONS,
    )

    if _has_tier0(metrics, FROZEN_LATTICE):
        expected_stems.extend(
            [
                "pareto.png",
                "pareto.pdf",
                "h1_redaction_paradox.png",
                "h1_redaction_paradox.pdf",
                "h3_granularity.png",
                "h3_granularity.pdf",
            ]
        )
        if any(
            metrics["conditions"].get(cid, {}).get("transfer") for cid in H1_CONDITIONS
        ):
            expected_stems.extend(["h1_transfer.png", "h1_transfer.pdf"])
    if _has_trial4(metrics):
        expected_stems.extend(
            [
                "adversary_pareto.png",
                "adversary_pareto.pdf",
            ]
        )
        if _has_trial4_components(metrics):
            expected_stems.extend(
                [
                    "adversary_bars.png",
                    "adversary_bars.pdf",
                ]
            )

    for stem in expected_stems:
        assert (out_dir / stem).is_file(), f"missing {stem}"
    assert paths["h2_png"].stat().st_size > 0


def test_run_figures_cli(tmp_path):
    root = repo_root()
    metrics_src = root / "outputs" / "pilot_v1" / "metrics.json"
    if not metrics_src.is_file():
        pytest.skip("I0 metrics.json not present")

    pilot = tmp_path / "pilot"
    pilot.mkdir()
    shutil.copy(metrics_src, pilot / "metrics.json")

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_figures", root / "eval" / "run_figures.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rc = mod.main(
        [
            "--config",
            str(root / "configs" / "pilot_v0.1.1.yaml"),
            "--metrics",
            str(pilot / "metrics.json"),
            "--output-dir",
            str(pilot / "figures"),
        ]
    )
    assert rc == 0
    assert (pilot / "figures" / "h2_utility_recovery.png").is_file()
    assert (pilot / "boundary_bundle_v0.json").is_file()
