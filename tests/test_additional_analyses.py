"""Smoke test for post-hoc additional analyses."""

from __future__ import annotations

import pytest

from eval.additional_analyses import run_all_analyses
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


def test_run_additional_analyses(cfg, tmp_path):
    root = repo_root()
    pilot = root / cfg["outputs"]["pilot_dir"]
    if not (pilot / "metrics.json").is_file():
        pytest.skip("pilot_v2 metrics missing")

    cfg_local = dict(cfg)
    cfg_local["outputs"] = dict(cfg["outputs"])
    cfg_local["outputs"]["pilot_dir"] = str(pilot.relative_to(root))

    outputs = run_all_analyses(root, cfg_local)
    assert outputs.figures
    assert outputs.json_summary.is_file()
