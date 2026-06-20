"""LLM text sanitization baselines (Ollama OpenAI-compatible API)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import httpx

from transform.llm_cache_io import (
    get_llm_cache_z,
    has_llm_cache_entry,
    llm_condition_cache_dir,
    upsert_llm_cache_entry,
    upsert_llm_cache_entries,
)

LlmSanitizeMode = Literal["substitute", "rephrase"]
TextField = Literal["journal_text", "assistant_text"]

PROMPT_VERSION = "v1"
BATCH_PROMPT_VERSION = "batch_v1"

_SYSTEM = {
    "substitute": (
        "You sanitize health-adjacent journaling text for an observability export. "
        "Replace personally identifying or sensitive phrases with plausible alternative "
        "phrases of similar grammatical role (medications, employers, times, symptom wording). "
        "Inspired by zero-shot redaction/substitution (Albanese et al.) and truthful replacement "
        "methods. Keep failure-relevant meaning (side effects, escalation cues, adherence friction). "
        "Return ONLY valid JSON with keys journal_text and assistant_text."
    ),
    "rephrase": (
        "You paraphrase health-adjacent journaling text for a privacy-preserving observability export. "
        "Rewrite in fluent prose without copying sensitive spans verbatim; preserve triage-relevant "
        "semantics (symptoms, medication changes, safety cues). Inspired by dynamic semantic "
        "sanitization (DYNTEXT) and neural text sanitization lines. "
        "Return ONLY valid JSON with keys journal_text and assistant_text."
    ),
}

_BATCH_SYSTEM: dict[str, dict[str, str]] = {
    "journal_text": {
        "substitute": (
            "You sanitize an array of health-adjacent journal strings for observability export. "
            "For each string, replace sensitive phrases with plausible alternates of similar grammatical "
            "role. Preserve order, count, and triage-relevant meaning. "
            "Return ONLY a JSON array of strings (same length as input). No markdown, no extra keys."
        ),
        "rephrase": (
            "You paraphrase an array of health-adjacent journal strings for privacy-preserving export. "
            "Rewrite each string in fluent prose without copying sensitive spans verbatim. "
            "Preserve order, count, and triage-relevant semantics. "
            "Return ONLY a JSON array of strings (same length as input). No markdown, no extra keys."
        ),
    },
    "assistant_text": {
        "substitute": (
            "You sanitize an array of health-adjacent assistant response strings for observability export. "
            "For each string, replace sensitive phrases with plausible alternates of similar grammatical "
            "role. Preserve order, count, and triage-relevant meaning. "
            "Return ONLY a JSON array of strings (same length as input). No markdown, no extra keys."
        ),
        "rephrase": (
            "You paraphrase an array of health-adjacent assistant response strings for privacy-preserving "
            "export. Rewrite each string in fluent prose without copying sensitive spans verbatim. "
            "Preserve order, count, and triage-relevant semantics. "
            "Return ONLY a JSON array of strings (same length as input). No markdown, no extra keys."
        ),
    },
}


def _user_message(journal_text: str, assistant_text: str) -> str:
    return json.dumps(
        {"journal_text": journal_text, "assistant_text": assistant_text},
        ensure_ascii=False,
    )


def _batch_user_message(journal_texts: list[str]) -> str:
    return json.dumps(journal_texts, ensure_ascii=False)


def _extract_json_payload(content: str) -> Any:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", content)
        if not match:
            raise ValueError(f"No JSON in model response: {content[:200]}") from None
        return json.loads(match.group(1))


def _parse_json_content(content: str) -> dict[str, str]:
    data = _extract_json_payload(content)
    if not isinstance(data, dict):
        raise ValueError("Model response JSON must be an object")
    journal = data.get("journal_text")
    assistant = data.get("assistant_text")
    if not isinstance(journal, str) or not isinstance(assistant, str):
        raise ValueError("Model JSON must include string journal_text and assistant_text")
    return {"journal_text": journal.strip(), "assistant_text": assistant.strip()}


def _parse_text_array(content: str, expected_len: int, *, label: str = "text") -> list[str]:
    data = _extract_json_payload(content)
    if isinstance(data, dict):
        for key in (
            "journal_texts",
            "assistant_texts",
            "texts",
            "journals",
            "assistants",
            "results",
        ):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("Batch model response must be a JSON array of strings")
    if len(data) != expected_len:
        raise ValueError(f"Expected {expected_len} {label} strings, got {len(data)}")
    out: list[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, str):
            raise ValueError(f"Batch item {i} is not a string")
        out.append(item.strip())
    return out


def _parse_journal_array(content: str, expected_len: int) -> list[str]:
    return _parse_text_array(content, expected_len, label="journal")


def cache_path(
    root: Path,
    cfg: dict[str, Any],
    condition_id: str,
    event_id: str,
) -> Path:
    """Legacy helper: per-event path (unused when cache is cache.jsonl-only)."""
    return llm_condition_cache_dir(root, cfg, condition_id) / f"{event_id}.json"


def batch_cache_path(
    root: Path,
    cfg: dict[str, Any],
    condition_id: str,
    batch_key: str,
) -> Path:
    tcfg = cfg.get("transform", {}).get("llm", {})
    cache_dir = root / tcfg.get("cache_dir", "data/llm_transform_cache")
    return cache_dir / condition_id / "batches" / f"{batch_key}.json"


def load_cached(
    root: Path,
    cfg: dict[str, Any],
    condition_id: str,
    event_id: str,
) -> dict[str, str] | None:
    condition_dir = llm_condition_cache_dir(root, cfg, condition_id)
    return get_llm_cache_z(condition_dir, event_id)


def write_cache(
    root: Path,
    cfg: dict[str, Any],
    *,
    condition_id: str,
    event_id: str,
    model: str,
    z: dict[str, str],
    prompt_version: str = PROMPT_VERSION,
    flush: bool = True,
) -> None:
    condition_dir = llm_condition_cache_dir(root, cfg, condition_id)
    upsert_llm_cache_entry(
        condition_dir,
        {
            "condition_id": condition_id,
            "event_id": event_id,
            "model": model,
            "prompt_version": prompt_version,
            "z": z,
        },
        flush=flush,
    )


def build_text_export(
    event: dict[str, Any],
    journal_text: str,
    *,
    condition_id: str,
    llm_sanitize_mode: str,
    model: str,
    prompt_version: str,
    transform_assistant: bool = False,
    assistant_text: str | None = None,
) -> dict[str, Any]:
    """Fill lattice export JSON after LLM returns journal text only."""
    assistant = assistant_text if assistant_text is not None else event["assistant_text"]
    if not transform_assistant:
        pass  # passthrough raw assistant (default for batch journal-only)
    return {
        "event_id": event["event_id"],
        "persona_id": event["persona_id"],
        "condition_id": condition_id,
        "schema_id": "redacted_text",
        "z": {
            "journal_text": journal_text,
            "assistant_text": assistant,
        },
        "r": {
            "policy_id": "obs_policy_v1",
            "policy_version": "1.0.0",
            "schema_id": "redacted_text",
            "transform_id": condition_id,
            "llm_sanitize_mode": llm_sanitize_mode,
            "llm_model": model,
            "prompt_version": prompt_version,
            "event_id": event["event_id"],
            "verify_outcome": "pass",
        },
        "verify_outcome": "pass",
    }


def _llm_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    tcfg = cfg.get("transform", {}).get("llm", {})
    eval_cfg = cfg.get("eval", {}).get("tier1", {})
    return {
        "base_url": str(
            tcfg.get("base_url", eval_cfg.get("ollama_base_url", "http://127.0.0.1:11434/v1"))
        ),
        "model": str(tcfg.get("model", eval_cfg.get("primary_model", "qwen3:8b"))),
        "temperature": float(tcfg.get("temperature", eval_cfg.get("temperature", 0))),
        "timeout": float(tcfg.get("timeout_s", 180)),
        "batch_size": int(tcfg.get("batch_size", 30)),
    }


def _model_tag(cfg: dict[str, Any]) -> str:
    return _llm_cfg(cfg)["model"]


def _chat_completion(messages: list[dict[str, str]], cfg: dict[str, Any]) -> str:
    lcfg = _llm_cfg(cfg)
    url = lcfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": lcfg["model"],
        "temperature": lcfg["temperature"],
        "messages": messages,
    }
    with httpx.Client(timeout=lcfg["timeout"]) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
    return body["choices"][0]["message"]["content"]


def call_ollama(
    journal_text: str,
    assistant_text: str,
    mode: LlmSanitizeMode,
    cfg: dict[str, Any],
) -> dict[str, str]:
    content = _chat_completion(
        [
            {"role": "system", "content": _SYSTEM[mode]},
            {"role": "user", "content": _user_message(journal_text, assistant_text)},
        ],
        cfg,
    )
    return _parse_json_content(content)


def call_ollama_batch(
    texts: list[str],
    mode: LlmSanitizeMode,
    cfg: dict[str, Any],
    *,
    text_field: TextField = "journal_text",
    max_retries: int = 2,
) -> list[str]:
    if not texts:
        return []
    label = "journal" if text_field == "journal_text" else "assistant"
    messages = [
        {"role": "system", "content": _BATCH_SYSTEM[text_field][mode]},
        {"role": "user", "content": _batch_user_message(texts)},
    ]
    last_err: ValueError | None = None
    for _ in range(max_retries + 1):
        content = _chat_completion(messages, cfg)
        try:
            return _parse_text_array(content, len(texts), label=label)
        except ValueError as exc:
            last_err = exc
    assert last_err is not None
    raise last_err


def llm_sanitize_event(
    journal_text: str,
    assistant_text: str,
    mode: LlmSanitizeMode,
    cfg: dict[str, Any],
    root: Path,
    *,
    condition_id: str,
    event_id: str,
    use_cache: bool = True,
) -> dict[str, str]:
    if use_cache:
        cached = load_cached(root, cfg, condition_id, event_id)
        if cached is not None:
            return cached
    z = call_ollama(journal_text, assistant_text, mode, cfg)
    write_cache(
        root,
        cfg,
        condition_id=condition_id,
        event_id=event_id,
        model=_model_tag(cfg),
        z=z,
    )
    return z


def llm_sanitize_batch(
    events: list[dict[str, Any]],
    mode: LlmSanitizeMode,
    cfg: dict[str, Any],
    root: Path,
    *,
    condition_id: str,
    batch_key: str | None = None,
    use_cache: bool = True,
    text_field: TextField = "journal_text",
) -> list[dict[str, str]]:
    """Sanitize journal_text or assistant_text for a batch; other field passthrough."""
    if not events:
        return []

    results: list[dict[str, str] | None] = [None] * len(events)
    pending: list[tuple[int, dict[str, Any], dict[str, str] | None]] = []

    for i, event in enumerate(events):
        cached = load_cached(root, cfg, condition_id, event["event_id"])
        if text_field == "journal_text":
            if use_cache and cached is not None:
                results[i] = cached
                continue
        else:
            if cached is None:
                continue
            if use_cache and cached["assistant_text"] != event["assistant_text"]:
                results[i] = cached
                continue
        pending.append((i, event, cached))

    if not pending:
        return [r for r in results if r is not None]  # type: ignore[list-item]

    pending_events = [e for _, e, _ in pending]
    source_texts = [e[text_field] for e in pending_events]

    def _split_fallback() -> list[str]:
        if len(pending_events) == 1:
            event = pending_events[0]
            z = call_ollama(
                event["journal_text"],
                event["assistant_text"],
                mode,
                cfg,
            )
            return [z[text_field]]
        mid = len(pending_events) // 2
        left = llm_sanitize_batch(
            pending_events[:mid],
            mode,
            cfg,
            root,
            condition_id=condition_id,
            use_cache=False,
            text_field=text_field,
        )
        right = llm_sanitize_batch(
            pending_events[mid:],
            mode,
            cfg,
            root,
            condition_id=condition_id,
            use_cache=False,
            text_field=text_field,
        )
        return [z[text_field] for z in left + right]

    try:
        transformed = call_ollama_batch(source_texts, mode, cfg, text_field=text_field)
    except ValueError:
        transformed = _split_fallback()

    if len(transformed) != len(pending):
        transformed = _split_fallback()

    model = _model_tag(cfg)
    condition_dir = llm_condition_cache_dir(root, cfg, condition_id)
    batch_records: list[dict[str, Any]] = []
    for (idx, event, cached), new_text in zip(pending, transformed, strict=True):
        if text_field == "journal_text":
            z = {
                "journal_text": new_text,
                "assistant_text": event["assistant_text"],
            }
        else:
            assert cached is not None
            z = {
                "journal_text": cached["journal_text"],
                "assistant_text": new_text,
            }
        batch_records.append(
            {
                "condition_id": condition_id,
                "event_id": event["event_id"],
                "model": model,
                "prompt_version": BATCH_PROMPT_VERSION,
                "z": z,
            }
        )
        results[idx] = z

    upsert_llm_cache_entries(condition_dir, batch_records, flush=True)

    if batch_key and use_cache:
        bpath = batch_cache_path(root, cfg, condition_id, batch_key)
        bpath.parent.mkdir(parents=True, exist_ok=True)
        bpath.write_text(
            json.dumps(
                {
                    "batch_key": batch_key,
                    "condition_id": condition_id,
                    "event_ids": [e["event_id"] for e in events],
                    "model": model,
                    "prompt_version": BATCH_PROMPT_VERSION,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return [r if r is not None else {"journal_text": "", "assistant_text": ""} for r in results]


def group_events_by_persona(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        pid = event["persona_id"]
        groups.setdefault(pid, []).append(event)
    return groups


def chunk_events(events: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0:
        return [events]
    return [events[i : i + size] for i in range(0, len(events), size)]
