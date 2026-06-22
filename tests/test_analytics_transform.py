"""Analytics transform pipeline tests."""

from __future__ import annotations


import pytest

from sbb.config import load_config, repo_root
from transform.io import EVENTS_BUNDLE_NAME, load_jsonl
from transform.run_analytics_transforms import run_analytics_lattice

ROOT = repo_root()
CFG = load_config()
PROHIBITED = {
    "failure_mode",
    "error_stage",
    "specific_medication",
    "occupation_sector",
    "journal_text",
    "assistant_text",
}


@pytest.fixture(scope="module")
def analytics_stats(tmp_path_factory):
    obs_src = ROOT / CFG["paths"]["transformed"]
    if not (obs_src / "raw" / EVENTS_BUNDLE_NAME).is_file():
        pytest.skip("observability transforms required")
    out_root = tmp_path_factory.mktemp("transformed_analytics")
    cfg_copy = dict(CFG)
    cfg_copy["paths"] = dict(CFG["paths"])
    cfg_copy["paths"]["transformed_analytics"] = str(out_root)
    stats = run_analytics_lattice(cfg_copy, ROOT)
    return stats, out_root


def test_analytics_lattice_all_conditions(analytics_stats):
    stats, out_root = analytics_stats
    assert stats["event_count"] > 0
    assert stats["verify_failures"] == 0
    for cond in CFG["lattice"]["conditions"]:
        bundle = out_root / cond / EVENTS_BUNDLE_NAME
        assert bundle.is_file(), cond
        assert len(load_jsonl(bundle)) == stats["event_count"]


def test_sem_medium_no_failure_mode(analytics_stats):
    _, out_root = analytics_stats
    records = load_jsonl(out_root / "sem_medium" / EVENTS_BUNDLE_NAME)
    for rec in records[:20]:
        assert PROHIBITED.isdisjoint(rec["z"].keys())
        assert rec["r"]["policy_id"] == "analytics_policy_v1"
        assert rec["verify_outcome"] == "pass"


def test_text_arms_reuse_same_z(analytics_stats):
    _, out_root = analytics_stats
    obs_raw = load_jsonl(ROOT / CFG["paths"]["transformed"] / "raw" / EVENTS_BUNDLE_NAME)
    ana_raw = load_jsonl(out_root / "raw" / EVENTS_BUNDLE_NAME)
    assert len(obs_raw) == len(ana_raw)
    for obs, ana in zip(obs_raw[:5], ana_raw[:5], strict=True):
        assert obs["z"] == ana["z"]
