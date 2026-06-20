"""Policy π: allowed fields and prohibited combinations."""

from __future__ import annotations

from typing import Any


def policy_check(z: dict[str, Any], policy: dict[str, Any], schema_id: str) -> tuple[bool, list[str]]:
    """Return (ok, violations)."""
    violations: list[str] = []
    for field in policy.get("prohibited_in_export", []):
        if field in z:
            violations.append(f"prohibited_field:{field}")

    caps = policy.get("granularity_caps", {})
    expected_schema = caps.get(schema_id.replace("obs_schema_", "sem_").replace("sem_", "sem_"))
    # schema_id passed as obs_schema_medium or sem_medium
    for gran_key, allowed_schema in caps.items():
        if schema_id.endswith(gran_key.split("_")[-1]) or schema_id == allowed_schema:
            break
    else:
        if schema_id.startswith("obs_schema_"):
            pass  # ok

    for combo in policy.get("prohibited_combinations", []):
        fields = combo.get("fields", [])
        if all(f in z and z[f] is not None for f in fields):
            violations.append(f"prohibited_combo:{','.join(fields)}")

    return len(violations) == 0, violations
