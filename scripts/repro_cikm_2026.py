#!/usr/bin/env python3
"""Verify the CIKM 2026 paper protocol and cite-surface checksums (no Ollama)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases" / "cikm-2026"
PROTOCOL_JSON = RELEASE / "experimental_protocol.json"
CHECKSUMS = RELEASE / "checksums.sha256"
CONFIG = ROOT / "configs" / "cikm_v0.1.yaml"
TABLE3 = (
    ROOT
    / "outputs"
    / "post_acceptance_experiments"
    / "ta5_cohort_audit"
    / "snapshot_track_c"
    / "table3_operative_grid.json"
)
CAMERA_READY = ROOT / "outputs" / "pilot_v2_camera_ready" / "CAMERA_READY_PROTOCOL.json"

REQUIRED_PATHS = [
    "configs/cikm_v0.1.yaml",
    "src/eval/paper_protocol.py",
    "tests/test_paper_protocol.py",
    "releases/cikm-2026/experimental_protocol.json",
    "releases/cikm-2026/experimental_protocol.md",
    "releases/cikm-2026/checksums.sha256",
    "releases/cikm-2026/figures/linkage_decomposition.pdf",
    "releases/cikm-2026/figures/utility_matrix_heatmap.pdf",
    "releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf",
    "outputs/pilot_v2_camera_ready/CAMERA_READY_PROTOCOL.json",
    "outputs/pilot_v2_camera_ready/CAMERA_READY_PROTOCOL.md",
    "outputs/post_acceptance_experiments/purpose_specific_linkage/REPORT.md",
    "outputs/post_acceptance_experiments/ta5_cohort_audit/track_c_scores.json",
    "outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/table3_operative_grid.md",
    "outputs/post_acceptance_experiments/purpose_specific_linkage/analytics_linkage_decomposition/figures/linkage_decomposition_observability_surface.pdf",
    "outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/figures/utility_matrix_heatmap.pdf",
    "outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/figures/cross_purpose_regret_matrix.pdf",
]

TABLE3_AT_045 = {
    "T_o-1": "bracket (0.67)",
    "T_a-1": "surrogate (0.45)",
    "T_a-2": "coarse (1.00)",
    "T_a-3": "coarse (1.00)",
    "T_a-5": "surrogate (0.26)",
}

TOKEN_TOL = 1e-6
PERSONA_TOL = 1e-6


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_checksums(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        mapping[rel.strip()] = digest.lower()
    return mapping


def _yaml_paper_protocol() -> dict:
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    proto = cfg.get("paper_protocol")
    if not isinstance(proto, dict):
        raise KeyError("configs/cikm_v0.1.yaml is missing paper_protocol")
    return proto


def _scan_abs_paths() -> list[str]:
    hits: list[str] = []
    roots = [RELEASE, ROOT / "outputs" / "pilot_v2_camera_ready", ROOT / "outputs" / "post_acceptance_experiments"]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if "/Users/" in text or "/home/" in text:
                hits.append(str(path.relative_to(ROOT)))
    return hits


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).is_file():
            errors.append(f"missing file: {rel}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    proto = _yaml_paper_protocol()
    if proto.get("linkage", {}).get("fit") != "train_only":
        errors.append(f"paper_protocol.linkage.fit: {proto.get('linkage', {}).get('fit')!r} != 'train_only'")
    if proto.get("linkage", {}).get("risk_surface") != "purpose_specific":
        errors.append(
            "paper_protocol.linkage.risk_surface: "
            f"{proto.get('linkage', {}).get('risk_surface')!r} != 'purpose_specific'"
        )
    if proto.get("ta5_cohort", {}).get("primary") != "track_c_assessor_symmetric":
        errors.append(
            "paper_protocol.ta5_cohort.primary: "
            f"{proto.get('ta5_cohort', {}).get('primary')!r} != 'track_c_assessor_symmetric'"
        )

    cite = json.loads(PROTOCOL_JSON.read_text(encoding="utf-8"))
    ver = cite.get("verification", {})
    if ver.get("tfidf_fit_scope") != "train_only":
        errors.append("cite experimental_protocol.json: tfidf_fit_scope != train_only")
    if ver.get("risk_surface") != "purpose_specific":
        errors.append("cite experimental_protocol.json: risk_surface != purpose_specific")
    if ver.get("ta5_cohort") != "track_c_assessor_symmetric":
        errors.append("cite experimental_protocol.json: ta5_cohort != track_c_assessor_symmetric")

    table3_cite = ver.get("table3_at_0_45") or {}
    for key, expected in TABLE3_AT_045.items():
        got = table3_cite.get(key)
        if got != expected:
            errors.append(f"cite Table 3 @ 0.45 {key}: got {got!r}, expected {expected!r}")

    grid = json.loads(TABLE3.read_text(encoding="utf-8"))
    row = next((r for r in grid.get("track_c", []) if abs(float(r["r_max"]) - 0.45) < 1e-9), None)
    if row is None:
        errors.append("table3_operative_grid.json missing track_c row at r_max=0.45")
    else:
        for key, expected in TABLE3_AT_045.items():
            if row.get(key) != expected:
                errors.append(f"snapshot Table 3 @ 0.45 {key}: got {row.get(key)!r}, expected {expected!r}")

    camera = json.loads(CAMERA_READY.read_text(encoding="utf-8"))
    if camera.get("tfidf_fit_scope") != "train_only":
        errors.append("outputs CAMERA_READY_PROTOCOL.json: tfidf_fit_scope != train_only")
    token = camera.get("verification", {}).get("red_tokenize", {})
    cite_token = ver.get("red_tokenize", {})
    expected_token = 0.007883565797453002
    expected_persona = 0.8365079365079365
    for label, blob in (("outputs", token), ("cite", cite_token)):
        tr = float(blob.get("token_recovery_rate", -1))
        pr = float(blob.get("persona_top1", -1))
        if abs(tr - expected_token) > TOKEN_TOL:
            errors.append(f"{label} red_tokenize token_recovery_rate: got {tr}, expected {expected_token}")
        if abs(pr - expected_persona) > PERSONA_TOL:
            errors.append(f"{label} red_tokenize persona_top1: got {pr}, expected {expected_persona}")
        if blob.get("near_zero_token_high_persona") is not True:
            errors.append(f"{label} red_tokenize near_zero_token_high_persona is not true")

    checksums = _load_checksums(CHECKSUMS)
    expected_figs = [
        "releases/cikm-2026/figures/linkage_decomposition.pdf",
        "releases/cikm-2026/figures/utility_matrix_heatmap.pdf",
        "releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf",
    ]
    for rel in expected_figs:
        if rel not in checksums:
            errors.append(f"checksums.sha256 missing {rel}")
            continue
        digest = _sha256(ROOT / rel)
        if digest != checksums[rel]:
            errors.append(f"checksum mismatch {rel}: got {digest}, expected {checksums[rel]}")

    abs_hits = _scan_abs_paths()
    if abs_hits:
        errors.append("laptop absolute paths in: " + ", ".join(abs_hits))

    if errors:
        print("repro-cikm-2026: FAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("repro-cikm-2026: OK")
    print("  protocol: train-only TF-IDF, purpose-specific R, Track C Ta-5")
    print("  Table 3 @ 0.45: To-1 bracket, Ta-1 surrogate, Ta-2/3 coarse, Ta-5 surrogate")
    print("  red_tokenize: token=0.0079, persona=0.837")
    print("  figure checksums: 3/3 match releases/cikm-2026/checksums.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
