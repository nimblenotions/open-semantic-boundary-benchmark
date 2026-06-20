"""Persona-stable tokenization baseline (vault-style pseudonyms)."""

from __future__ import annotations

from transform.spans import TokenVault, transform_text


def tokenize_text(text: str, persona_id: str, vault: TokenVault | None = None) -> str:
    v = vault or TokenVault(persona_id)
    return transform_text(text, "tokenize", vault=v)


def tokenize_event(
    journal_text: str,
    assistant_text: str,
    persona_id: str,
    vault: TokenVault | None = None,
) -> dict[str, str]:
    v = vault or TokenVault(persona_id)
    return {
        "journal_text": tokenize_text(journal_text, persona_id, v),
        "assistant_text": tokenize_text(assistant_text, persona_id, v),
    }
