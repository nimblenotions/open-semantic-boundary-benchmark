"""Tests for advisor-consolidation paper figures."""

from __future__ import annotations

import pytest

from eval.advisor_figures import run_advisor_figures
from sbb.config import repo_root


@pytest.fixture
def pilot_v2_paths():
    pilot = repo_root() / "outputs" / "pilot_v2"
    obs = pilot / "metrics.json"
    analytics = pilot / "analytics_metrics.json"
    if not obs.is_file() or not analytics.is_file():
        pytest.skip("pilot_v2 metrics not present")
    return obs, analytics


def test_advisor_figures_generate(pilot_v2_paths, tmp_path):
    obs_path, analytics_path = pilot_v2_paths
    out_dir = tmp_path / "figures"
    result = run_advisor_figures(obs_path, analytics_path, out_dir)

    assert len(result["conditions"]) == 9
    for stem in (
        "utility_matrix_heatmap.png",
        "linkage_decomposition.png",
        "cross_purpose_regret_matrix.png",
    ):
        path = out_dir / stem
        assert path.is_file(), f"missing {stem}"
        assert path.stat().st_size > 0

    table_dir = out_dir / "tables"
    for stem in (
        "utility_matrix.csv",
        "linkage_decomposition.csv",
        "cross_purpose_regret_matrix.csv",
    ):
        path = table_dir / stem
        assert path.is_file(), f"missing {stem}"

    # Focal regret: obs winner deployed on med-class at R_max=0.45
    assert result["r_max"] == 0.45
    winners = result["regret_winners"]
    assert winners["observability"] == "redact_bracket"
    assert winners["analytics_med"] == "redact_surrogate"
