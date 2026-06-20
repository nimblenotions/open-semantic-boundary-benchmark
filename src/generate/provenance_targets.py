"""Build per-event provenance oracle rows for Sikkim / Trial4 alignment."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from eval.adversary import _sensitive_surface_forms
from transform.io import load_jsonl, write_jsonl_bundle

TRIAL4_ATTRIBUTE_INFERENCE = [
    "medication_class",
    "occupation_sector",
    "symptom_categories",
    "quasi_id_rarity",
]

TRIAL4_ATTACK_MAP: dict[str, Any] = {
    "persona_membership": "persona_id",
    "attribute_inference": list(TRIAL4_ATTRIBUTE_INFERENCE),
    "longitudinal_linkage": "persona_id",
    "token_recovery": "raw_surface_forms",
}

PROVENANCE_CONTRACT: dict[str, Any] = {
    "schema_ref": "data/schemas/provenance_v1.json",
    "required_r_fields": [
        "policy_id",
        "policy_version",
        "schema_id",
        "transform_id",
        "event_id",
        "verify_outcome",
    ],
    "expected_verify_outcome": "pass",
}

REQUIRED_TOP_LEVEL_KEYS = (
    "event_id",
    "persona_id",
    "split",
    "linkage_oracle",
    "trial4_attack_map",
    "leakage_oracle",
    "provenance_contract",
    "observability_oracle",
    "exemplar_id",
)

REQUIRED_LINKAGE_KEYS = (
    "persona_id",
    "medication_class",
    "occupation_sector",
    "symptom_categories",
    "quasi_id_rarity",
    "time_bucket",
)

REQUIRED_LEAKAGE_KEYS = (
    "medication_brand",
    "medication_generic",
    "specific_medication",
    "occupation",
    "raw_surface_forms",
)

_OCCUPATION_STOPWORDS = frozenset({"a", "an", "the", "at", "of", "and", "or", "my"})


def _occupation_tokens(occupation: str) -> list[str]:
    words = re.findall(r"[A-Za-z]+", occupation)
    return [w for w in words if w.lower() not in _OCCUPATION_STOPWORDS]


def raw_surface_forms_for_event(
    event: dict[str, Any],
    persona: dict[str, Any],
) -> list[str]:
    """Token-recovery oracle: persona secrets + span-detected surfaces in raw prose."""
    hidden = persona.get("hidden_attributes", {})
    raw_text = f"{event.get('journal_text', '')} {event.get('assistant_text', '')}"
    surfaces: set[str] = set()

    brand = hidden.get("medication_brand")
    generic = hidden.get("medication_generic")
    occupation = hidden.get("occupation", "")

    if isinstance(brand, str) and brand:
        surfaces.add(brand)
    if isinstance(generic, str) and generic:
        surfaces.add(generic)
    for token in _occupation_tokens(str(occupation)):
        surfaces.add(token)

    for token in _sensitive_surface_forms(raw_text):
        if token:
            surfaces.add(token)

    return sorted(surfaces, key=str.lower)


def build_linkage_oracle(
    label: dict[str, Any],
    persona: dict[str, Any],
) -> dict[str, Any]:
    symptom_categories = label.get("symptom_categories") or []
    if not isinstance(symptom_categories, list):
        symptom_categories = [str(symptom_categories)]
    return {
        "persona_id": label["persona_id"],
        "medication_class": label["medication_class"],
        "occupation_sector": label["occupation_sector"],
        "symptom_categories": list(symptom_categories),
        "quasi_id_rarity": persona.get("quasi_id_rarity", "unknown"),
        "time_bucket": label["time_bucket"],
    }


def build_leakage_oracle(
    label: dict[str, Any],
    event: dict[str, Any],
    persona: dict[str, Any],
) -> dict[str, Any]:
    hidden = persona.get("hidden_attributes", {})
    return {
        "medication_brand": hidden.get("medication_brand", ""),
        "medication_generic": hidden.get("medication_generic", ""),
        "specific_medication": label.get("specific_medication", ""),
        "occupation": hidden.get("occupation", ""),
        "raw_surface_forms": raw_surface_forms_for_event(event, persona),
    }


def build_provenance_row(
    label: dict[str, Any],
    event: dict[str, Any],
    persona: dict[str, Any],
    *,
    exemplar_id: str | None = None,
) -> dict[str, Any]:
    return {
        "event_id": label["event_id"],
        "persona_id": label["persona_id"],
        "split": label["split"],
        "linkage_oracle": build_linkage_oracle(label, persona),
        "trial4_attack_map": dict(TRIAL4_ATTACK_MAP),
        "leakage_oracle": build_leakage_oracle(label, event, persona),
        "provenance_contract": dict(PROVENANCE_CONTRACT),
        "observability_oracle": {
            "failure_mode": label["failure_mode"],
            "error_stage": label["error_stage"],
        },
        "exemplar_id": exemplar_id,
    }


def _pick_e1(labels: list[dict[str, Any]]) -> str:
    preferred = "evt_000010"
    if any(l["event_id"] == preferred for l in labels):
        return preferred
    for label in labels:
        if label.get("failure_mode") == "missed_safety_escalation":
            return label["event_id"]
    raise ValueError("no E1 candidate (missed_safety_escalation)")


def _pick_e2(
    labels: list[dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
) -> str:
    test_labels = [l for l in labels if l.get("split") == "test"]
    for label in test_labels:
        persona = persona_table.get(label["persona_id"], {})
        if persona.get("quasi_id_rarity") == "rare":
            return label["event_id"]
    raise ValueError("no E2 candidate (test split + quasi_id_rarity=rare)")


def _pick_e3(labels: list[dict[str, Any]]) -> str:
    test_labels = [l for l in labels if l.get("split") == "test"]
    for label in test_labels:
        if label.get("failure_mode") != "assistant_ok" and label.get("error_stage") != "none":
            return label["event_id"]
    raise ValueError(
        "no E3 candidate (test split, failure_mode != assistant_ok, error_stage != none)"
    )


def build_exemplars(
    labels: list[dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    e1_id = _pick_e1(labels)
    e2_id = _pick_e2(labels, persona_table)
    e3_id = _pick_e3(labels)

    e1_label = next(l for l in labels if l["event_id"] == e1_id)
    e2_label = next(l for l in labels if l["event_id"] == e2_id)
    e3_label = next(l for l in labels if l["event_id"] == e3_id)

    return {
        "E1": {
            "event_id": e1_id,
            "title": "Missed escalation (H1/H2 showcase)",
            "failure_mode": e1_label["failure_mode"],
        },
        "E2": {
            "event_id": e2_id,
            "title": "Rare quasi-ID still linkable under sem_fine",
            "persona_query": "quasi_id_rarity=rare AND split=test",
            "persona_id": e2_label["persona_id"],
        },
        "E3": {
            "event_id": e3_id,
            "title": "Redaction preserves categories, breaks error_stage",
            "failure_mode_query": "non-assistant_ok with error_stage != none",
            "failure_mode": e3_label["failure_mode"],
            "error_stage": e3_label["error_stage"],
        },
    }


def generate_provenance_targets(
    cfg: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    gt_root = root / cfg["paths"]["ground_truth"]
    labels = load_jsonl(gt_root / "labels.jsonl")
    events = {row["event_id"]: row for row in load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")}
    persona_table = {
        row["persona_id"]: row
        for row in load_jsonl(gt_root / "persona_table.jsonl")
    }

    exemplars = build_exemplars(labels, persona_table)
    exemplar_by_event = {meta["event_id"]: eid for eid, meta in exemplars.items()}

    rows: list[dict[str, Any]] = []
    for label in labels:
        event_id = label["event_id"]
        if event_id not in events:
            raise KeyError(f"missing raw event for label {event_id}")
        persona = persona_table.get(label["persona_id"])
        if persona is None:
            raise KeyError(f"missing persona_table row for {label['persona_id']}")
        rows.append(
            build_provenance_row(
                label,
                events[event_id],
                persona,
                exemplar_id=exemplar_by_event.get(event_id),
            )
        )

    rows.sort(key=lambda r: r["event_id"])
    return rows, exemplars


def validate_provenance_targets(
    rows: list[dict[str, Any]],
    *,
    expected_event_count: int | None = None,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if expected_event_count is not None and len(rows) != expected_event_count:
        failures.append(
            f"row count: got {len(rows)}, want {expected_event_count}"
        )

    seen: set[str] = set()
    for row in rows:
        event_id = row.get("event_id")
        if not event_id:
            failures.append("row missing event_id")
            continue
        if event_id in seen:
            failures.append(f"duplicate event_id: {event_id}")
        seen.add(event_id)

        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in row:
                failures.append(f"{event_id}: missing top-level key {key}")

        linkage = row.get("linkage_oracle", {})
        for key in REQUIRED_LINKAGE_KEYS:
            if key not in linkage:
                failures.append(f"{event_id}: linkage_oracle missing {key}")
        if linkage.get("persona_id") != row.get("persona_id"):
            failures.append(
                f"{event_id}: linkage_oracle.persona_id != row.persona_id"
            )

        leakage = row.get("leakage_oracle", {})
        for key in REQUIRED_LEAKAGE_KEYS:
            if key not in leakage:
                failures.append(f"{event_id}: leakage_oracle missing {key}")
        if not isinstance(leakage.get("raw_surface_forms"), list):
            failures.append(f"{event_id}: raw_surface_forms must be a list")

    return len(failures) == 0, failures


def write_provenance_targets(
    cfg: dict[str, Any],
    root: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
    exemplars: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    gt_root = root / cfg["paths"]["ground_truth"]
    if rows is None or exemplars is None:
        rows, exemplars = generate_provenance_targets(cfg, root)

    event_count = len(load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl"))
    ok, failures = validate_provenance_targets(rows, expected_event_count=event_count)
    if not ok:
        raise ValueError("provenance_targets validation failed: " + "; ".join(failures))

    targets_path = gt_root / "provenance_targets.jsonl"
    exemplars_path = gt_root / "exemplars.json"
    write_jsonl_bundle(targets_path, rows)
    exemplars_path.write_text(json.dumps(exemplars, indent=2) + "\n", encoding="utf-8")

    return {
        "provenance_targets": str(targets_path.relative_to(root)),
        "exemplars_path": str(exemplars_path.relative_to(root)),
        "row_count": len(rows),
        "exemplars": exemplars,
        "ok": True,
    }
