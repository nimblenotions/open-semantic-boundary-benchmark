"""Serialize frozen exports as text for embedding-based evaluation."""

from __future__ import annotations

import json
from typing import Any

from eval.observability_task import (
    condition_kind,
    flatten_semantic_z,
    serialize_text_export,
)


def export_text_for_embedding(export: dict[str, Any]) -> str:
    """Canonical string representation of an export for embedders."""
    condition_id = export["condition_id"]
    z = export["z"]
    if condition_kind(condition_id) == "text":
        return serialize_text_export(z)
    return json.dumps(flatten_semantic_z(z), sort_keys=True)
