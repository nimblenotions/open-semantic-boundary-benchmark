"""Figure generation tests for v0.1.1 published metrics (outputs/pilot_v2)."""

from __future__ import annotations

import pytest

from eval.figures import generate_all_figures, load_metrics
from sbb.config import repo_root


@pytest.fixture
def pilot_v2_metrics():
    path = repo_root() / "outputs" / "pilot_v2" / "metrics.json"
    if not path.is_file():
        pytest.skip("pilot_v2 metrics.json not present")
    return load_metrics(path)


def test_generate_pilot_v2_figures(pilot_v2_metrics, tmp_path):
    out_dir = tmp_path / "figures"
    paths = generate_all_figures(pilot_v2_metrics, out_dir)

    for stem in (
        "h1_transfer.png",
        "h1_token_recovery.png",
        "h2_utility_recovery.png",
        "h3_granularity.png",
        "h4_llm_arms.png",
        "adversary_pareto.png",
        "adversary_bars.png",
        "r4_summary.csv",
    ):
        assert (out_dir / stem).is_file(), f"missing {stem}"

    if _has_sensitivity_data(pilot_v2_metrics):
        assert "sensitivity_png" in paths
        assert paths["sensitivity_png"].stat().st_size > 0
    else:
        assert "sensitivity_png" not in paths

    assert paths["h4_png"].stat().st_size > 0


def _has_sensitivity_data(metrics: dict) -> bool:
    from eval.figures import _has_sensitivity, _primary_conditions

    primary = _primary_conditions(metrics)
    return _has_sensitivity(metrics, conditions=primary)
