#!/usr/bin/env python3
"""Historical v0.1.1 regression smoke test; not the CIKM 2026 protocol.

Checks retained pilot_v2 artifacts against the v0.1.1 reference numbers.
For the published CIKM artifact, use `make repro-cikm-2026`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "outputs" / "pilot_v2"
TOL = 0.02

REQUIRED_PATHS = [
    "outputs/pilot_v2/config_snapshot/pilot_v0.1.1.yaml",
    "data/ground_truth/splits.json",
    "data/transformed/raw/events.jsonl",
    "data/policies/obs_policy_v1.json",
    "data/schemas/provenance_v1.json",
    "outputs/pilot_v2/metrics.json",
    "outputs/pilot_v2/analytics_metrics.json",
    "outputs/pilot_v2/boundary_bundle_v0.json",
]

# Retained v0.1.1 regression reference (obs + analytics F1, combined linkage R)
HISTORICAL_REFERENCE = {
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

    for cond, exp in HISTORICAL_REFERENCE.items():
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
        print("repro-smoke: historical v0.1.1 reference out of tolerance", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("repro-smoke: OK (artifacts present, historical v0.1.1 reference within tolerance)")
    print("Historical pilot_v2 artifacts match the retained v0.1.1 regression reference.")
    print("  Published artifact: make repro-cikm-2026")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
