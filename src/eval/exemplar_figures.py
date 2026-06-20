"""E1–E3 qualitative export panels for the paper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG_DPI = 300

EXEMPLAR_PANELS: dict[str, dict[str, Any]] = {
    "E1": {
        "event_id": "evt_000010",
        "title": "E1 — Missed safety escalation",
        "conditions": ["raw", "redact_bracket", "sem_medium"],
    },
    "E2": {
        "event_id": "evt_000040",
        "title": "E2 — Rare quasi-ID under sem_fine",
        "conditions": ["raw", "sem_fine"],
    },
    "E3": {
        "event_id": "evt_000041",
        "title": "E3 — Redaction vs error_stage",
        "conditions": ["raw", "redact_bracket"],
    },
}


def _load_export_z(transformed_root: Path, condition_id: str, event_id: str) -> dict[str, Any] | None:
    path = transformed_root / condition_id / "events.jsonl"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event_id") == event_id:
            return row.get("z", {})
    return None


def _format_z(z: dict[str, Any], *, max_len: int = 420) -> str:
    text = json.dumps(z, indent=2, ensure_ascii=False)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def plot_exemplar_panel(
    exemplar_id: str,
    *,
    obs_root: Path,
    meta: dict[str, Any],
    out_dir: Path,
) -> dict[str, Path]:
    event_id = meta["event_id"]
    conditions = meta["conditions"]
    n = len(conditions)
    fig, axes = plt.subplots(1, n, figsize=(3.8 * n, 4.2))
    if n == 1:
        axes = [axes]

    for ax, condition_id in zip(axes, conditions, strict=True):
        z = _load_export_z(obs_root, condition_id, event_id)
        ax.axis("off")
        ax.set_title(condition_id.replace("_", "\n"), fontsize=9, loc="left")
        body = _format_z(z) if z else "(export not found)"
        ax.text(
            0.02,
            0.98,
            body,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=7,
            family="monospace",
            wrap=True,
        )

    fig.suptitle(f"{meta['title']}\n{event_id}", fontsize=10, y=1.02)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"exemplar_{exemplar_id.lower()}"
    png = out_dir / f"{stem}.png"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(png, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return {"png": png, "pdf": pdf}


def generate_exemplar_figures(obs_root: Path, out_dir: Path) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    for eid, meta in EXEMPLAR_PANELS.items():
        paths = plot_exemplar_panel(eid, obs_root=obs_root, meta=meta, out_dir=out_dir)
        for k, p in paths.items():
            outputs[f"exemplar_{eid.lower()}_{k}"] = p
    return outputs
