"""Smoke test for bootstrap CI script."""

from __future__ import annotations

import json

import pytest

from eval.bootstrap_cis import run_bootstrap_cis
from sbb.config import load_config, repo_root


@pytest.fixture
def pilot_ready():
    root = repo_root()
    pilot = root / "outputs" / "pilot_v2"
    if not (pilot / "metrics.json").is_file():
        pytest.skip("pilot_v2 metrics not present")
    return root


def test_bootstrap_cis_smoke(pilot_ready):
    import shutil

    root = pilot_ready
    cfg = load_config(root / "configs" / "pilot_v0.1.1.yaml")
    cfg = dict(cfg)
    out_rel = "outputs/_test_bootstrap_tmp"
    cfg["outputs"] = {"pilot_dir": out_rel}
    out_dir = root / out_rel
    if out_dir.exists():
        shutil.rmtree(out_dir)

    try:
        outputs = run_bootstrap_cis(root, cfg, n_bootstrap=20, seed=0)
        assert outputs.json_path.is_file()
        assert outputs.tex_path.is_file()
        data = json.loads(outputs.json_path.read_text())
        assert len(data["conditions"]) >= 7
        first = data["conditions"][0]
        assert "obs_failure_mode_macro_f1" in first
        assert (
            first["obs_failure_mode_macro_f1"]["ci95_lo"]
            <= first["obs_failure_mode_macro_f1"]["point"]
        )
        assert outputs.tex_path.read_text().startswith("% Auto-generated")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
