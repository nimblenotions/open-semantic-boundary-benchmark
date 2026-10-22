"""Smoke test for bootstrap CI script."""

from __future__ import annotations

import json

import numpy as np
import pytest

from eval.bootstrap_cis import _persona_block_bootstrap_linkage, run_bootstrap_cis
from sbb.config import load_config, repo_root


def _export_row(event_id: str, persona_id: str, text: str) -> dict:
    return {
        "event_id": event_id,
        "persona_id": persona_id,
        "export": {
            "condition_id": "raw",
            "z": {"journal_text": text, "assistant_text": ""},
        },
    }


def test_persona_block_bootstrap_fits_tfidf_on_train_only(monkeypatch):
    seen: dict[str, object] = {}

    def fake_fit(train_texts, test_texts, *, tfidf_fit_scope="train_only"):
        seen["scope"] = tfidf_fit_scope
        seen["n_train"] = len(train_texts)
        seen["n_test"] = len(test_texts)

        class _Embedder:
            def embed(self, texts):
                return np.zeros((len(texts), 2), dtype=np.float64)

        return _Embedder(), {"tfidf_fit_scope": tfidf_fit_scope}

    monkeypatch.setattr("eval.bootstrap_cis.fit_trial4_tfidf_embedder", fake_fit)
    monkeypatch.setattr(
        "eval.bootstrap_cis._linkage_score_on_test_rows",
        lambda *args, **kwargs: 0.1,
    )

    samples = _persona_block_bootstrap_linkage(
        [_export_row("e0", "p0", "training export")],
        [
            _export_row("e1", "p1", "held out one"),
            _export_row("e2", "p2", "held out two"),
        ],
        {},
        {},
        seed=0,
        n_bootstrap=2,
        rng=np.random.default_rng(0),
        tfidf_fit_scope="train_only",
    )

    assert seen["scope"] == "train_only"
    assert seen["n_train"] == 1
    assert seen["n_test"] == 2
    assert samples.shape == (2,)
    assert np.all(samples == 0.1)


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
    cfg = load_config(root / "configs" / "cikm_v0.1.yaml")
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
