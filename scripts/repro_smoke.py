#!/usr/bin/env python3
"""Fast repro smoke: verify frozen artifacts and headline metrics (no Ollama)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "outputs" / "pilot_v2"
TOL = 0.02

REQUIRED_PATHS = [
    "configs/pilot_v0.1.1.yaml",
    "data/ground_truth/splits.json",
    "data/transformed/raw/events.jsonl",
    "data/policies/obs_policy_v1.json",
    "data/schemas/provenance_v1.json",
    "outputs/pilot_v2/metrics.json",
    "outputs/pilot_v2/analytics_metrics.json",
    "outputs/pilot_v2/boundary_bundle_v0.json",
]

# Paper headline table (obs + analytics primary-consumer F1, combined linkage R)
HEADLINE = {
    "raw": {"obs_tier1_f1": 0.63, "analytics_tier1_f1": 0.55, "linkage_r": 0.48},
    "redact_bracket": {"obs_tier1_f1": 0.67, "analytics_tier1_f1": 0.20, "linkage_r": 0.36},
    "redact_tokenize": {"obs_tier1_f1": 0.66, "analytics_tier1_f1": 0.23, "linkage_r": 0.66},
    "redact_surrogate": {"obs_tier1_f1": 0.66, "analytics_tier1_f1": 0.45, "linkage_r": 0.42},
}


def _close(actual: float, expected: float, tol: float = TOL) -> bool:
    return abs(actual - expected) <= tol


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).is_file():
            errors.append(f"missing file: {rel}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    obs = json.loads((PILOT / "metrics.json").read_text())
    ana = json.loads((PILOT / "analytics_metrics.json").read_text())

    for cond, exp in HEADLINE.items():
        o = obs["conditions"][cond]
        a = ana["conditions"][cond]
        obs_f1 = o["tier1"]["failure_mode_macro_f1"]
        ana_f1 = a["tier1"]["medication_class_macro_f1"]
        linkage = o["trial4_adversary"]["combined_linkage_score"]
        if not _close(obs_f1, exp["obs_tier1_f1"]):
            errors.append(
                f"{cond} obs primary-consumer F1: got {obs_f1:.3f}, expected ~{exp['obs_tier1_f1']}"
            )
        if not _close(ana_f1, exp["analytics_tier1_f1"]):
            errors.append(
                f"{cond} analytics primary-consumer F1: got {ana_f1:.3f}, expected ~{exp['analytics_tier1_f1']}"
            )
        if not _close(linkage, exp["linkage_r"]):
            errors.append(
                f"{cond} R(z): got {linkage:.3f}, expected ~{exp['linkage_r']}"
            )

    if errors:
        print("repro-smoke: headline metrics out of tolerance", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("repro-smoke: OK (artifacts present, headline metrics within tolerance)")
    print("SUCCESS: Local artifacts match published Open SBB v0.1.1 headline metrics.")
    print("  pilot alias: outputs/pilot_v2/ = frozen v0.1.1 published run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
