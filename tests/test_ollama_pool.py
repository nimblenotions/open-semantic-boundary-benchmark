"""Tests for parallel Ollama Tier-1 job planning."""

from __future__ import annotations

import pytest

from eval.ollama_pool import Tier1Job, plan_tier1_jobs, validate_parallel_batch
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


def test_plan_tier1_jobs_obs_primary(cfg):
    root = repo_root()
    jobs = plan_tier1_jobs(
        cfg,
        root,
        purpose="obs",
        models=["qwen3:8b"],
        conditions=["raw", "redact_llm_rephrase"],
    )
    keys = {j.cache_key() for j in jobs}
    assert keys == {
        "obs:qwen3:8b:raw",
        "obs:qwen3:8b:redact_llm_rephrase",
    }


def test_validate_parallel_batch_rejects_duplicate_cache():
    jobs = [
        Tier1Job("obs", "qwen3:8b", "raw"),
        Tier1Job("obs", "qwen3:8b", "raw"),
    ]
    with pytest.raises(ValueError, match="duplicate cache"):
        validate_parallel_batch(jobs)


def test_validate_parallel_batch_allows_disjoint_models():
    jobs = [
        Tier1Job("obs", "qwen3:8b", "raw"),
        Tier1Job("obs", "llama3.1:8b", "raw"),
    ]
    validate_parallel_batch(jobs)
