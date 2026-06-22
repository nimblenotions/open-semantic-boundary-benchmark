"""Frozen release artifact checks (split manifest v0, boundary bundle schema)."""

from __future__ import annotations

import json

import jsonschema
import pytest

from sbb.config import repo_root
from sbb.frozen_tier import (
    BOUNDARY_BUNDLE_SCHEMA,
    SPLIT_MANIFEST_V0,
    build_split_manifest_v0,
    canonical_json_sha256,
)

EXPECTED_SPLIT_MANIFEST_SHA256 = (
    "b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0"
)


def test_split_manifest_v0_matches_splits_json():
    root = repo_root()
    manifest_path = root / SPLIT_MANIFEST_V0
    assert manifest_path.is_file(), "run scripts/build_split_manifest_v0.py"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    splits = json.loads((root / "data" / "ground_truth" / "splits.json").read_text(encoding="utf-8"))

    assert manifest["persona_split"] == splits["persona_split"]
    assert manifest["seed"] == splits["seed"]
    assert manifest["persona_counts"] == {"train": 70, "val": 10, "test": 20}
    assert manifest["test_event_count"] == 630


def test_split_manifest_v0_canonical_sha256():
    root = repo_root()
    manifest_path = root / SPLIT_MANIFEST_V0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert canonical_json_sha256(manifest) == EXPECTED_SPLIT_MANIFEST_SHA256


def test_split_manifest_v0_regeneration_is_stable():
    root = repo_root()
    rebuilt = build_split_manifest_v0(root)
    committed = json.loads((root / SPLIT_MANIFEST_V0).read_text(encoding="utf-8"))
    assert rebuilt == committed


def test_readme_lists_split_manifest_sha256():
    readme = (repo_root() / "README.md").read_text(encoding="utf-8")
    assert EXPECTED_SPLIT_MANIFEST_SHA256 in readme
    assert "split_manifest_v0.json" in readme


def test_boundary_bundle_v0_validates_against_schema():
    root = repo_root()
    schema_path = root / BOUNDARY_BUNDLE_SCHEMA
    bundle_path = root / "outputs" / "pilot_v2" / "boundary_bundle_v0.json"
    if not bundle_path.is_file():
        pytest.skip("pilot_v2 boundary_bundle_v0.json not present")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    jsonschema.validate(bundle, schema)
    assert bundle["split_manifest"] == SPLIT_MANIFEST_V0
