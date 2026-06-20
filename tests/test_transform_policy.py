"""Transform policy smoke tests."""

from __future__ import annotations

from transform.redact import redact_text


def test_zoloft_absent_from_redact_bracket():
    text = "I started Zoloft 50mg before my hospital shift."
    out = redact_text(text, "bracket")
    assert "Zoloft" not in out
    assert "zoloft" not in out.lower()
    assert "[MEDICATION]" in out
