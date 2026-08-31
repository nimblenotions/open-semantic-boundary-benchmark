"""Paper protocol declared in configs/cikm_v0.1.yaml.

Replay of train-only TF-IDF, assessor-symmetric Ta-5, and purpose-specific
linkage writes under outputs/post_acceptance_experiments/. Frozen utility
caches remain in outputs/pilot_v2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def paper_protocol(cfg: dict[str, Any]) -> dict[str, Any]:
    proto = cfg.get("paper_protocol")
    if not isinstance(proto, dict):
        raise KeyError("config is missing paper_protocol")
    return proto


def tfidf_params(cfg: dict[str, Any]) -> dict[str, Any]:
    link = paper_protocol(cfg)["linkage"]
    ngram = link["ngram_range"]
    return {
        "analyzer": str(link["analyzer"]),
        "ngram_range": (int(ngram[0]), int(ngram[1])),
        "max_features": int(link["max_features"]),
        "fit": str(link["fit"]),
    }


def purpose_specific_output_dir(cfg: dict[str, Any], root: Path) -> Path:
    rel = paper_protocol(cfg)["purpose_specific_linkage"]["outputs"]
    return root / rel


def track_c_scores_path(cfg: dict[str, Any], root: Path) -> Path:
    return root / paper_protocol(cfg)["ta5_cohort"]["scores"]


def ta5_output_dir(cfg: dict[str, Any], root: Path) -> Path:
    return root / paper_protocol(cfg)["ta5_cohort"]["outputs"]


def frozen_pilot_dir(cfg: dict[str, Any], root: Path) -> Path:
    rel = cfg.get("outputs", {}).get("pilot_dir", "outputs/pilot_v2")
    return root / rel
