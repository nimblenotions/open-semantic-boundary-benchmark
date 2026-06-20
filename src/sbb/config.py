"""Load configs/pilot_v0.1.1.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return ROOT


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or ROOT / "configs" / "pilot_v0.1.1.yaml"
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(relative: str) -> Path:
    return ROOT / relative
