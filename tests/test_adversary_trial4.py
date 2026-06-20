"""Tests for Trial4-style adversary evaluation."""

from __future__ import annotations

from eval.adversary_trial4 import (
    combined_linkage_score,
    evaluate_trial4_adversary,
)
from eval.embeddings import MockEmbedder


def _label(
    event_id: str,
    persona_id: str,
    *,
    med: str = "SSRI",
    sector: str = "technology",
    symptoms: list[str] | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "persona_id": persona_id,
        "failure_mode": "assistant_ok",
        "error_stage": "none",
        "medication_class": med,
        "occupation_sector": sector,
        "symptom_categories": symptoms or ["anxiety"],
        "time_bucket": "morning",
    }


def _text_export(event_id: str, persona_id: str, condition_id: str, journal: str) -> dict:
    return {
        "event_id": event_id,
        "persona_id": persona_id,
        "condition_id": condition_id,
        "z": {
            "journal_text": journal,
            "assistant_text": "Acknowledged.",
        },
    }


def _persona_table() -> dict[str, dict]:
    return {
        "persona_a": {"persona_id": "persona_a", "quasi_id_rarity": "common"},
        "persona_b": {"persona_id": "persona_b", "quasi_id_rarity": "rare"},
        "persona_c": {"persona_id": "persona_c", "quasi_id_rarity": "common"},
    }


def _synthetic_corpus(condition_id: str) -> tuple[list[dict], list[dict]]:
    """Three personas with distinct prose signatures."""
    journals = {
        "persona_a": "Alpha persona logs morning SSRI dose with fatigue and anxiety.",
        "persona_b": "Beta persona evening SNRI routine includes retail work stress.",
        "persona_c": "Gamma persona hospital shift NDRI adherence barrier noted.",
    }
    train_rows = []
    test_rows = []
    for i, pid in enumerate(journals):
        for j in range(4):
            eid = f"evt_{pid}_train_{j}"
            train_rows.append(
                {
                    "event_id": eid,
                    "persona_id": pid,
                    "split": "train",
                    "label": _label(
                        eid,
                        pid,
                        med=["SSRI", "SNRI", "NDRI"][i],
                        sector=["technology", "retail", "healthcare"][i],
                    ),
                    "export": _text_export(eid, pid, condition_id, journals[pid]),
                }
            )
        eid = f"evt_{pid}_test"
        test_rows.append(
            {
                "event_id": eid,
                "persona_id": pid,
                "split": "test",
                "label": _label(
                    eid,
                    pid,
                    med=["SSRI", "SNRI", "NDRI"][i],
                    sector=["technology", "retail", "healthcare"][i],
                ),
                "export": _text_export(eid, pid, condition_id, journals[pid]),
            }
        )
    return train_rows, test_rows


def test_combined_linkage_score_formula():
    score = combined_linkage_score(
        {
            "persona_top1": 0.6,
            "attribute_combined_macro_f1": 0.3,
            "longitudinal_linkage_auc": 0.9,
        }
    )
    assert score == 0.6


def test_mock_embedder_persona_raw_beats_tokenize():
    embedder = MockEmbedder(dim=32)
    persona_table = _persona_table()
    raw_train, raw_test = _synthetic_corpus("raw")

    token_train, token_test = _synthetic_corpus("redact_tokenize")
    for rows in (token_train, token_test):
        for row in rows:
            row["export"]["z"]["journal_text"] = "tok tok tok generic tokenized text"

    raw_by_id = {
        r["event_id"]: {
            "event_id": r["event_id"],
            "journal_text": r["export"]["z"]["journal_text"],
            "assistant_text": r["export"]["z"]["assistant_text"],
        }
        for r in raw_train + raw_test
    }

    raw_metrics = evaluate_trial4_adversary(
        raw_train,
        raw_test,
        raw_by_id,
        persona_table,
        embedder=embedder,
        seed=42,
    )
    token_metrics = evaluate_trial4_adversary(
        token_train,
        token_test,
        raw_by_id,
        persona_table,
        embedder=embedder,
        seed=42,
    )

    assert raw_metrics["persona_top1"] > token_metrics["persona_top1"]
    assert raw_metrics["persona_top1"] > 0.0
    assert "combined_linkage_score" in raw_metrics
    assert raw_metrics["n_test"] == 3


def test_trial4_returns_attribute_and_linkage_keys():
    embedder = MockEmbedder(dim=16)
    train, test = _synthetic_corpus("raw")
    raw_by_id = {
        r["event_id"]: {
            "journal_text": r["export"]["z"]["journal_text"],
            "assistant_text": r["export"]["z"]["assistant_text"],
        }
        for r in train + test
    }
    metrics = evaluate_trial4_adversary(
        train, test, raw_by_id, _persona_table(), embedder=embedder, seed=7
    )
    for key in (
        "persona_top5",
        "medication_class_macro_f1",
        "occupation_sector_macro_f1",
        "longitudinal_linkage_auc",
        "longitudinal_loo_top1",
        "attribute_combined_macro_f1",
        "embedder",
    ):
        assert key in metrics
