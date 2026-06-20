"""Corpus validation against config floors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generate.ground_truth import BENIGN_MODE, FAILURE_MODES
from sbb.config import repo_root


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _tier(persona_count: int) -> str:
    return "smoke" if persona_count < 50 else "paper"


def validate_corpus(cfg: dict[str, Any], root: Path | None = None) -> tuple[bool, dict[str, Any]]:
    root = root or repo_root()
    corpus_cfg = cfg["corpus"]
    persona_count = int(cfg.get("persona_count", corpus_cfg.get("persona_count", 10)))
    floors = corpus_cfg[_tier(persona_count)]

    labels = _load_jsonl(root / cfg["paths"]["ground_truth"] / "labels.jsonl")
    personas = _load_jsonl(root / cfg["paths"]["ground_truth"] / "persona_table.jsonl")
    events = _load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")

    failures: list[str] = []
    counts = {m: 0 for m in FAILURE_MODES + [BENIGN_MODE]}
    for lab in labels:
        mode = lab.get("failure_mode", "")
        counts[mode] = counts.get(mode, 0) + 1

    failure_labeled = sum(1 for lab in labels if lab.get("failure_mode") != BENIGN_MODE)
    rare_count = sum(1 for p in personas if p.get("quasi_id_rarity") == "rare")

    if len(personas) != persona_count:
        failures.append(f"persona_count: got {len(personas)}, want {persona_count}")
    if len(events) < floors["min_events"]:
        failures.append(f"min_events: got {len(events)}, want {floors['min_events']}")
    if len(events) != len(labels):
        failures.append(f"events/labels mismatch: {len(events)} vs {len(labels)}")
    if failure_labeled < floors["min_failure_labeled"]:
        failures.append(
            f"min_failure_labeled: got {failure_labeled}, want {floors['min_failure_labeled']}"
        )
    if counts.get("missed_safety_escalation", 0) < floors["min_missed_safety_escalation"]:
        failures.append(
            "min_missed_safety_escalation: "
            f"got {counts.get('missed_safety_escalation', 0)}, "
            f"want {floors['min_missed_safety_escalation']}"
        )
    for mode in FAILURE_MODES:
        if counts.get(mode, 0) < floors["min_per_failure_mode"]:
            failures.append(
                f"min_per_failure_mode[{mode}]: got {counts.get(mode, 0)}, "
                f"want {floors['min_per_failure_mode']}"
            )
    if rare_count < floors["min_rare_personas"]:
        failures.append(f"min_rare_personas: got {rare_count}, want {floors['min_rare_personas']}")

    provenance_path = root / cfg["paths"]["ground_truth"] / "provenance_targets.jsonl"
    if provenance_path.is_file():
        provenance_rows = _load_jsonl(provenance_path)
        if len(provenance_rows) != len(events):
            failures.append(
                "provenance_targets row count: "
                f"got {len(provenance_rows)}, want {len(events)}"
            )
        else:
            from generate.provenance_targets import validate_provenance_targets

            ok, prov_failures = validate_provenance_targets(
                provenance_rows, expected_event_count=len(events)
            )
            if not ok:
                failures.extend(prov_failures[:5])
                if len(prov_failures) > 5:
                    failures.append(
                        f"provenance_targets: +{len(prov_failures) - 5} more errors"
                    )

    report = {
        "tier": _tier(persona_count),
        "persona_count": len(personas),
        "event_count": len(events),
        "failure_labeled": failure_labeled,
        "failure_mode_counts": counts,
        "rare_persona_count": rare_count,
        "ok": len(failures) == 0,
        "failures": failures,
    }
    return report["ok"], report


def main(argv: list[str] | None = None) -> int:
    import argparse

    from sbb.config import load_config

    parser = argparse.ArgumentParser(description="Validate SBB-Obs corpus")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    ok, report = validate_corpus(cfg)
    print(json.dumps(report, indent=2))
    return 0 if ok else 1
