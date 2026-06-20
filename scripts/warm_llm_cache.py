#!/usr/bin/env python3
"""Pre-warm LLM transform cache using batch journal then assistant sanitization."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sbb.config import load_config, repo_root
from transform.io import load_jsonl
from transform.llm_cache_io import get_llm_cache_z, has_llm_cache_entry, llm_condition_cache_dir
from transform.llm_sanitize import (
    TextField,
    _llm_cfg,
    chunk_events,
    group_events_by_persona,
    llm_sanitize_batch,
)

CONDITIONS = {
    "redact_llm_substitute": "substitute",
    "redact_llm_rephrase": "rephrase",
}


def _event_batches(
    events: list[dict],
    cfg: dict,
    *,
    prefix: str = "",
) -> list[tuple[str, list[dict]]]:
    """Group by persona when configured; chunk to batch_size."""
    lcfg = cfg.get("transform", {}).get("llm", {})
    batch_size = int(lcfg.get("batch_size", 30))
    by_persona = bool(lcfg.get("batch_by_persona", True))

    batches: list[tuple[str, list[dict]]] = []
    if by_persona:
        for persona_id, group in sorted(group_events_by_persona(events).items()):
            for chunk in chunk_events(group, batch_size):
                key = f"{prefix}{persona_id}_{chunk[0]['event_id']}_{chunk[-1]['event_id']}"
                batches.append((key, chunk))
    else:
        for i, chunk in enumerate(chunk_events(events, batch_size)):
            key = f"{prefix}batch_{i:04d}_{chunk[0]['event_id']}_{chunk[-1]['event_id']}"
            batches.append((key, chunk))
    return batches


def _condition_dir(root: Path, cfg: dict, condition_id: str) -> Path:
    return llm_condition_cache_dir(root, cfg, condition_id)


def _needs_journal(
    event: dict,
    root: Path,
    cfg: dict,
    condition_id: str,
) -> bool:
    return not has_llm_cache_entry(_condition_dir(root, cfg, condition_id), event["event_id"])


def _needs_assistant(
    event: dict,
    root: Path,
    cfg: dict,
    condition_id: str,
) -> bool:
    cached = get_llm_cache_z(_condition_dir(root, cfg, condition_id), event["event_id"])
    if cached is None:
        return False
    return cached["assistant_text"] == event["assistant_text"]


def _run_phase(
    *,
    phase: str,
    text_field: TextField,
    events: list[dict],
    missing: list[dict],
    mode: str,
    cfg: dict,
    root: Path,
    condition_id: str,
    batch_size: int,
    total: int,
    done: int,
) -> int:
    print(
        f"  {phase}: {done}/{total} cached, {len(missing)} to fetch "
        f"(batch_size={batch_size})",
        flush=True,
    )
    if not missing:
        return done

    prefix = "assistant_" if text_field == "assistant_text" else ""
    batches = _event_batches(missing, cfg, prefix=prefix)
    processed = done
    for batch_key, chunk in batches:
        llm_sanitize_batch(
            chunk,
            mode,
            cfg,
            root,
            condition_id=condition_id,
            batch_key=batch_key,
            text_field=text_field,
        )
        processed += len(chunk)
        print(f"    {condition_id} {phase}: {processed}/{total}", flush=True)
    return processed


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-warm LLM transform cache.")
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=None,
        help="Condition IDs to warm (default: all LLM conditions).",
    )
    parser.add_argument(
        "--phase",
        choices=["journal", "assistant", "all"],
        default="all",
        help="Which text field phase to run (default: all).",
    )
    args = parser.parse_args()

    cfg = load_config(Path("configs/pilot_v0.1.1.yaml"))
    root = repo_root()
    events = load_jsonl(root / cfg["paths"]["raw"] / "events.jsonl")
    batch_size = _llm_cfg(cfg)["batch_size"]
    total = len(events)

    selected = CONDITIONS
    if args.conditions:
        unknown = [c for c in args.conditions if c not in CONDITIONS]
        if unknown:
            print(f"Unknown conditions: {unknown}", file=sys.stderr)
            return 1
        selected = {k: v for k, v in CONDITIONS.items() if k in args.conditions}

    phases: list[tuple[str, TextField]] = []
    if args.phase in ("journal", "all"):
        phases.append(("journal_text", "journal_text"))
    if args.phase in ("assistant", "all"):
        phases.append(("assistant_text", "assistant_text"))

    for condition_id, mode in selected.items():
        print(f"{condition_id} (batch_size={batch_size}):", flush=True)
        for phase_name, text_field in phases:
            if text_field == "journal_text":
                missing = [
                    e
                    for e in events
                    if _needs_journal(e, root, cfg, condition_id)
                ]
                done = total - len(missing)
            else:
                missing = [
                    e
                    for e in events
                    if _needs_assistant(e, root, cfg, condition_id)
                ]
                done = total - len(missing)
            _run_phase(
                phase=phase_name,
                text_field=text_field,
                events=events,
                missing=missing,
                mode=mode,
                cfg=cfg,
                root=root,
                condition_id=condition_id,
                batch_size=batch_size,
                total=total,
                done=done,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
