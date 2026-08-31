#!/usr/bin/env python3
"""Artifact-generation utility: emit data/ground_truth/split_manifest_v0.json.

Writes the frozen split manifest. Regeneration stability is tested; this is
not the CIKM 2026 reproduction path (`make repro-cikm-2026`).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sbb.frozen_tier import write_split_manifest_v0  # noqa: E402


def main() -> None:
    path, digest = write_split_manifest_v0(ROOT)
    print(f"wrote {path.relative_to(ROOT)}")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
