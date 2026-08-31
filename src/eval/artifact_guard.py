"""Refuse accidental writes into committed CIKM artifact trees."""

from __future__ import annotations

from pathlib import Path

COMMITTED_ARTIFACT_DIRS = (
    "outputs/pilot_v2",
    "outputs/pilot_v2_camera_ready",
    "releases/cikm-2026",
)


def is_committed_artifact_path(root: Path, path: Path) -> bool:
    resolved = path if path.is_absolute() else Path.cwd() / path
    try:
        rel = resolved.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return False
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in COMMITTED_ARTIFACT_DIRS)


def refuse_committed_write(root: Path, path: Path, *, force: bool) -> str | None:
    if force or not is_committed_artifact_path(root, path):
        return None
    return (
        f"Refusing to write committed artifact {path}. "
        "Pass --force, or --output pointing outside outputs/pilot_v2, "
        "outputs/pilot_v2_camera_ready, and releases/cikm-2026."
    )
