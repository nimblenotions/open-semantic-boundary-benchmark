"""Purpose registry: (consumer, T, π, schema)."""

from __future__ import annotations

import json
from pathlib import Path

from sbb.types import PurposeRegistration


class Registry:
    def __init__(self) -> None:
        self._entries: dict[str, PurposeRegistration] = {}

    def register(
        self,
        consumer_id: str,
        purpose_id: str,
        policy_path: str | Path,
        schema_id: str,
    ) -> None:
        key = f"{consumer_id}:{purpose_id}"
        self._entries[key] = PurposeRegistration(
            consumer_id=consumer_id,
            purpose_id=purpose_id,
            policy_path=str(policy_path),
            schema_id=schema_id,
        )

    def get(self, consumer_id: str, purpose_id: str) -> PurposeRegistration:
        key = f"{consumer_id}:{purpose_id}"
        if key not in self._entries:
            raise KeyError(f"Not registered: {key}")
        return self._entries[key]

    def load_policy(self, consumer_id: str, purpose_id: str) -> dict:
        entry = self.get(consumer_id, purpose_id)
        with open(entry.policy_path, encoding="utf-8") as f:
            return json.load(f)
