"""Smoke test for post-hoc additional analyses (writes under a temp pilot dir)."""

from __future__ import annotations

import shutil

import pytest

from eval.additional_analyses import run_all_analyses
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "cikm_v0.1.yaml")


def test_run_additional_analyses(cfg, tmp_path):
    root = repo_root()
    src = root / cfg["outputs"]["pilot_dir"]
    if not (src / "metrics.json").is_file():
        pytest.skip("pilot_v2 metrics missing")

    dest = tmp_path / "pilot"
    dest.mkdir()
    shutil.copy(src / "metrics.json", dest / "metrics.json")
    analytics = src / "analytics_metrics.json"
    if analytics.is_file():
        shutil.copy(analytics, dest / "analytics_metrics.json")
    op_src = src / "operative_selection"
    if op_src.is_dir():
        shutil.copytree(op_src, dest / "operative_selection")

    cfg_local = dict(cfg)
    cfg_local["outputs"] = dict(cfg["outputs"])
    cfg_local["outputs"]["pilot_dir"] = str(dest)

    outputs = run_all_analyses(root, cfg_local)
    assert outputs.figures
    assert outputs.json_summary.is_file()
    assert dest.resolve() in outputs.json_summary.resolve().parents
