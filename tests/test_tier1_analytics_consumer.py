"""Primary LLM analytics consumer tests (mocked HTTP — no live Ollama)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from eval.tier1_analytics_consumer import (
    PROMPT_VERSION,
    _parse_batch_predictions,
    _validate_labels,
    build_analytics_system_prompt,
    build_batch_user_message,
    evaluate_tier1_analytics,
    load_analytics_vocab,
    load_cached_prediction,
    predict_rows,
    write_eval_cache,
)
from sbb.config import load_config, repo_root


@pytest.fixture
def cfg():
    return load_config(repo_root() / "configs" / "pilot_v0.1.1.yaml")


@pytest.fixture
def vocab(cfg):
    return load_analytics_vocab(repo_root(), cfg)


@pytest.fixture
def sample_rows():
    return [
        {
            "event_id": "evt_a",
            "persona_id": "persona_001",
            "label": {
                "medication_class": "SSRI",
                "side_effect": False,
                "adherence_barrier": False,
            },
            "export": {
                "condition_id": "raw",
                "z": {
                    "journal_text": "Routine check-in.",
                    "assistant_text": "Logged.",
                },
            },
        },
        {
            "event_id": "evt_b",
            "persona_id": "persona_001",
            "label": {
                "medication_class": "SNRI",
                "side_effect": True,
                "adherence_barrier": True,
            },
            "export": {
                "condition_id": "raw",
                "z": {
                    "journal_text": "Nausea after dose, missed pills.",
                    "assistant_text": "Try resting.",
                },
            },
        },
    ]


def test_build_analytics_system_prompt_lists_vocab(vocab):
    prompt = build_analytics_system_prompt(vocab)
    assert "SSRI" in prompt
    assert "present" in prompt
    assert "barrier" in prompt
    assert "failure_mode" not in prompt
    assert "error_stage" not in prompt
    assert "BI/analytics agent" in prompt


def test_build_batch_user_message_preserves_event_ids(sample_rows):
    payload = json.loads(build_batch_user_message(sample_rows))
    assert [e["event_id"] for e in payload["events"]] == ["evt_a", "evt_b"]


def test_validate_labels_passes_through_oov_medication_class(vocab):
    pred = {
        "medication_class": "none",
        "side_effect_signal": "absent",
        "adherence_signal": "none",
    }
    assert _validate_labels(pred, vocab) == pred


def test_parse_batch_predictions_accepts_oov_medication_class(sample_rows, vocab):
    content = json.dumps(
        [
            {
                "event_id": "evt_a",
                "medication_class": "none",
                "side_effect_signal": "absent",
                "adherence_signal": "none",
            },
            {
                "event_id": "evt_b",
                "medication_class": "SNRI",
                "side_effect_signal": "present",
                "adherence_signal": "barrier",
            },
        ]
    )
    parsed = _parse_batch_predictions(content, sample_rows, vocab)
    assert parsed["evt_a"]["medication_class"] == "none"
    assert parsed["evt_b"]["medication_class"] == "SNRI"


def test_eval_cache_roundtrip(tmp_path, cfg):
    write_eval_cache(
        tmp_path,
        model="qwen3:8b",
        condition_id="raw",
        event_id="evt_a",
        seed=42,
        prediction={
            "medication_class": "SSRI",
            "side_effect_signal": "absent",
            "adherence_signal": "none",
        },
        raw_completion="{}",
    )
    cached = load_cached_prediction(tmp_path, "qwen3:8b", "raw", "evt_a")
    assert cached == {
        "medication_class": "SSRI",
        "side_effect_signal": "absent",
        "adherence_signal": "none",
    }


def _ollama_chat_response(content: str) -> dict:
    """Native Ollama /api/chat JSON body (qwen path in tier1_consumer)."""
    return {"message": {"content": content}}


def _openai_chat_response(content: str) -> dict:
    """OpenAI-compatible /v1/chat/completions body (llama/gemma path)."""
    return {"choices": [{"message": {"content": content}}]}


def _mock_transport_for_content(content: str) -> httpx.MockTransport:
    """Return Ollama or OpenAI mock body based on request URL/model."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        model = str(payload.get("model", "")).lower()
        if "qwen" in model or "/api/chat" in str(request.url):
            body = _ollama_chat_response(content)
        else:
            body = _openai_chat_response(content)
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def _mock_transport(responses: list[dict]) -> httpx.MockTransport:
    calls = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = calls["i"]
        calls["i"] += 1
        body = responses[min(idx, len(responses) - 1)]
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def test_predict_rows_batch_mock(sample_rows, cfg, vocab, tmp_path):
    system_prompt = build_analytics_system_prompt(vocab)
    content = json.dumps(
        [
            {
                "event_id": "evt_a",
                "medication_class": "SSRI",
                "side_effect_signal": "absent",
                "adherence_signal": "none",
            },
            {
                "event_id": "evt_b",
                "medication_class": "SNRI",
                "side_effect_signal": "present",
                "adherence_signal": "barrier",
            },
        ]
    )
    transport = _mock_transport_for_content(content)
    client = httpx.Client(transport=transport)

    preds = predict_rows(
        sample_rows,
        cfg=cfg,
        root=tmp_path,
        model="qwen3:8b",
        seed=42,
        condition_id="raw",
        vocab=vocab,
        system_prompt=system_prompt,
        client=client,
    )
    assert preds["evt_a"]["medication_class"] == "SSRI"
    assert preds["evt_b"]["side_effect_signal"] == "present"
    assert preds["evt_b"]["adherence_signal"] == "barrier"
    assert load_cached_prediction(tmp_path, "qwen3:8b", "raw", "evt_a") is not None


def test_evaluate_tier1_analytics_mock_metrics(sample_rows, cfg, tmp_path):
    content = json.dumps(
        [
            {
                "event_id": "evt_a",
                "medication_class": "SSRI",
                "side_effect_signal": "absent",
                "adherence_signal": "none",
            },
            {
                "event_id": "evt_b",
                "medication_class": "SNRI",
                "side_effect_signal": "present",
                "adherence_signal": "barrier",
            },
        ]
    )
    transport = _mock_transport_for_content(content)
    client = httpx.Client(transport=transport)

    cfg_local = json.loads(json.dumps(cfg))
    cfg_local["eval"]["tier1"]["eval_seeds"] = [42]

    result = evaluate_tier1_analytics(
        [],
        sample_rows,
        cfg_local,
        root=tmp_path,
        client=client,
    )
    assert result["status"] == "ok"
    assert result["medication_class_macro_f1"] == 1.0
    assert result["side_effect_signal_macro_f1"] == 1.0
    assert result["adherence_signal_macro_f1"] == 1.0
    assert "sensitivity" in result
    assert "llama3.1:8b" in result["sensitivity"]


def test_evaluate_tier1_analytics_connection_error(sample_rows, cfg, tmp_path):
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    cfg_local = json.loads(json.dumps(cfg))
    cfg_local["eval"]["tier1"]["eval_seeds"] = [42]
    cfg_local["eval"]["tier1"]["sensitivity_models"] = []

    result = evaluate_tier1_analytics(
        [], sample_rows, cfg_local, root=tmp_path, client=client
    )
    assert result["status"] == "error"
    assert result["medication_class_macro_f1"] is None
