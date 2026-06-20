"""Parallel Tier-1 Ollama workers for disjoint model×condition×purpose jobs."""

from __future__ import annotations

import copy
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from eval.eval_cache_io import eval_condition_cache_dir
from eval.io import join_eval_rows, load_condition_exports, load_labels, load_splits
from eval.study import resolve_eval_conditions
from eval.tier1_analytics_consumer import (
    _evaluate_model_on_rows as _evaluate_analytics_model_on_rows,
    build_analytics_system_prompt,
    load_analytics_vocab,
)
from eval.tier1_consumer import (
    _evaluate_model_on_rows,
    _tier1_cfg,
    build_triage_system_prompt,
    load_label_vocab,
)
from transform.io import condition_has_exports

Purpose = Literal["obs", "analytics"]


@dataclass(frozen=True)
class Tier1Job:
    purpose: Purpose
    model: str
    condition_id: str

    def cache_key(self) -> str:
        return f"{self.purpose}:{self.model}:{self.condition_id}"


def job_cache_dir(root: Path, job: Tier1Job) -> Path:
    return eval_condition_cache_dir(
        root,
        job.model,
        job.condition_id,
        analytics=job.purpose == "analytics",
    )


def plan_tier1_jobs(
    cfg: dict[str, Any],
    root: Path,
    *,
    purpose: Purpose | Literal["both"] = "obs",
    models: list[str] | None = None,
    conditions: list[str] | None = None,
) -> list[Tier1Job]:
    """Build jobs for each (purpose, model, condition) triple."""
    tcfg = _tier1_cfg(cfg)
    if models is None:
        models = [tcfg["primary_model"], *tcfg["sensitivity_models"]]
    purposes: list[Purpose]
    if purpose == "both":
        purposes = ["obs", "analytics"]
    else:
        purposes = [purpose]

    resolved = resolve_eval_conditions(cfg, root)
    if conditions is not None:
        allowed = set(conditions)
        resolved = [(cid, role) for cid, role in resolved if cid in allowed]

    jobs: list[Tier1Job] = []
    analytics_root = root / cfg["paths"]["transformed_analytics"]
    obs_root = root / cfg["paths"]["transformed"]

    for purpose_id in purposes:
        for model in models:
            for condition_id, _role in resolved:
                if purpose_id == "analytics":
                    if not (analytics_root / condition_id).is_dir():
                        continue
                    if not condition_has_exports(analytics_root / condition_id):
                        continue
                else:
                    if not (obs_root / condition_id).is_dir():
                        continue
                    if not condition_has_exports(obs_root / condition_id):
                        continue
                jobs.append(
                    Tier1Job(
                        purpose=purpose_id,
                        model=model,
                        condition_id=condition_id,
                    )
                )
    return jobs


def validate_parallel_batch(jobs: list[Tier1Job]) -> None:
    keys = [job.cache_key() for job in jobs]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"parallel batch has duplicate cache targets: {sorted(dupes)}")


def run_tier1_job(cfg: dict[str, Any], root: Path, job: Tier1Job) -> dict[str, Any]:
    """Run Tier-1 inference for one model×condition×purpose (test split only)."""
    os.environ["SBB_OLLAMA_PARALLEL"] = "1"
    cfg_local = copy.deepcopy(cfg)
    cfg_local["eval"]["tier1"]["eval_seeds"] = [42]

    persona_split = load_splits(root / cfg["paths"]["ground_truth"] / "splits.json")
    labels = load_labels(root / cfg["paths"]["ground_truth"] / "labels.jsonl")

    if job.purpose == "analytics":
        exports = load_condition_exports(
            root / cfg["paths"]["transformed_analytics"] / job.condition_id
        )
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        vocab = load_analytics_vocab(root, cfg_local)
        system_prompt = build_analytics_system_prompt(vocab)
        result = _evaluate_analytics_model_on_rows(
            test_rows,
            cfg=cfg_local,
            root=root,
            model=job.model,
            vocab=vocab,
            system_prompt=system_prompt,
        )
        metric_key = "medication_class_macro_f1"
    else:
        exports = load_condition_exports(
            root / cfg["paths"]["transformed"] / job.condition_id
        )
        test_rows = join_eval_rows(labels, exports, persona_split, split="test")
        vocab = load_label_vocab(root, cfg_local)
        system_prompt = build_triage_system_prompt(vocab)
        result = _evaluate_model_on_rows(
            test_rows,
            cfg=cfg_local,
            root=root,
            model=job.model,
            vocab=vocab,
            system_prompt=system_prompt,
        )
        metric_key = "failure_mode_macro_f1"

    return {
        "job": {
            "purpose": job.purpose,
            "model": job.model,
            "condition_id": job.condition_id,
            "cache_dir": str(
                job_cache_dir(root, job).relative_to(root)
            ),
        },
        "status": result.get("status"),
        "metric": result.get(metric_key),
        "n_test": result.get("n_test"),
        "n_parsed": result.get("n_parsed"),
        "reason": result.get("reason"),
    }


def run_jobs_parallel(
    jobs: list[Tier1Job],
    cfg: dict[str, Any],
    root: Path,
    *,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    """Run up to max_workers disjoint Tier-1 jobs concurrently."""
    if not jobs:
        return []
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    results: list[dict[str, Any]] = []
    for offset in range(0, len(jobs), max_workers):
        batch = jobs[offset : offset + max_workers]
        validate_parallel_batch(batch)
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = {
                pool.submit(run_tier1_job, cfg, root, job): job for job in batch
            }
            for future in as_completed(futures):
                job = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        {
                            "job": {
                                "purpose": job.purpose,
                                "model": job.model,
                                "condition_id": job.condition_id,
                            },
                            "status": "error",
                            "reason": str(exc),
                        }
                    )
    return results
