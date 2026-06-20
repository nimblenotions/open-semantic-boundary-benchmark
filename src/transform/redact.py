"""Rule-based redaction baselines aligned with common de-ID operators.

- redact_bracket: category-labeled placeholders ([MEDICATION]) — Philter-style
- redact_tokenize: stable persona-scoped pseudonyms — vault/tokenization products
"""

from __future__ import annotations

from transform.spans import RedactStyle, transform_text
from transform.tokenize import tokenize_event as _tokenize_event


def redact_text(text: str, style: RedactStyle = "bracket") -> str:
    if style == "tokenize":
        raise ValueError("use tokenize.tokenize_text with persona_id for tokenize style")
    return transform_text(text, style)


def redact_event(
    journal_text: str,
    assistant_text: str,
    style: RedactStyle = "bracket",
    *,
    persona_id: str | None = None,
) -> dict[str, str]:
    if style == "tokenize":
        if not persona_id:
            raise ValueError("persona_id required for tokenize")
        return _tokenize_event(journal_text, assistant_text, persona_id)
    return {
        "journal_text": transform_text(journal_text, style),
        "assistant_text": transform_text(assistant_text, style),
    }
