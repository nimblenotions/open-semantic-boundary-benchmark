"""Shared PHI-span detection for rule-based and tokenizing redaction."""

from __future__ import annotations

import hashlib
import re
from typing import Callable, Literal

from generate.persona import MEDICATIONS

RedactStyle = Literal["bracket", "mask", "remove", "tokenize"]

_MEDICATION_TOKENS: list[str] = []
for m in MEDICATIONS:
    _MEDICATION_TOKENS.extend([m["brand"], m["generic"], m["class"]])
_MEDICATION_TOKENS.extend(
    [
        "Zoloft",
        "sertraline",
        "SSRI",
        "SNRI",
        "NDRI",
        "medication",
        "meds",
        "pill",
        "pills",
        "dose",
    ]
)
_MEDICATION_TOKENS = sorted(set(_MEDICATION_TOKENS), key=len, reverse=True)

_TIME_PATTERNS = [
    re.compile(r"\byesterday evening\b", re.I),
    re.compile(r"\byesterday\b", re.I),
    re.compile(r"\bthis morning\b", re.I),
    re.compile(r"\btonight\b", re.I),
    re.compile(r"\bevening\b", re.I),
    re.compile(r"\bmorning\b", re.I),
    re.compile(r"\b\d{1,2}:\d{2}\b"),
    re.compile(r"\b\d+\s*mg\b", re.I),
]

_OCCUPATION_PATTERNS = [
    re.compile(r"\bhospital nurse\b", re.I),
    re.compile(r"\bhospital\b", re.I),
    re.compile(r"\bhealthcare\b", re.I),
    re.compile(r"\bshift at [^.;]+", re.I),
    re.compile(r"\bmy job at the \w+ place\b", re.I),
    re.compile(r"\bwork\b", re.I),
]

_SYMPTOM_PATTERNS = [
    re.compile(r"\bextremely dizzy and nauseous\b", re.I),
    re.compile(r"\bbrain fog\b", re.I),
    re.compile(r"\bdizzy\b", re.I),
    re.compile(r"\bnauseous\b", re.I),
    re.compile(r"\bnausea\b", re.I),
]

_TAG_PREFIX = {
    "MEDICATION": "MED",
    "TIME": "TIME",
    "OCCUPATION": "OCC",
    "SYMPTOM": "SYM",
}

# (name, rules, bracket tag)
RULES: list[tuple[str, list[str] | list[re.Pattern[str]], str]] = [
    ("medication", _MEDICATION_TOKENS, "MEDICATION"),
    ("time", _TIME_PATTERNS, "TIME"),
    ("occupation", _OCCUPATION_PATTERNS, "OCCUPATION"),
    ("symptom", _SYMPTOM_PATTERNS, "SYMPTOM"),
]


class TokenVault:
    """Stable pseudonyms per (persona, span type, normalized surface)."""

    def __init__(self, persona_id: str) -> None:
        self.persona_id = persona_id
        self._tokens: dict[tuple[str, str], str] = {}

    def pseudonym(self, tag: str, surface: str) -> str:
        norm = surface.lower().strip()
        key = (tag, norm)
        if key not in self._tokens:
            digest = hashlib.sha256(
                f"{self.persona_id}:{tag}:{norm}".encode()
            ).hexdigest()[:8]
            prefix = _TAG_PREFIX.get(tag, "TKN")
            self._tokens[key] = f"{prefix}_{digest}"
        return self._tokens[key]


def _mask_span(match: re.Match[str]) -> str:
    width = max(1, len(match.group(0)))
    return "[" + ("*" * width) + "]"


def _replacer(
    style: RedactStyle,
    tag: str,
    vault: TokenVault | None = None,
) -> Callable[[re.Match[str]], str]:
    if style == "bracket":
        label = f"[{tag}]"
        return lambda m: label
    if style == "mask":
        return _mask_span
    if style == "tokenize":
        if vault is None:
            raise ValueError("tokenize style requires TokenVault")
        return lambda m: vault.pseudonym(tag, m.group(0))
    return lambda m: " "


def _apply_token_rules(
    text: str,
    tokens: list[str],
    style: RedactStyle,
    tag: str,
    vault: TokenVault | None,
) -> str:
    out = text
    repl = _replacer(style, tag, vault)
    for token in tokens:
        out = re.sub(rf"\b{re.escape(token)}\b", repl, out, flags=re.I)
    return out


def _apply_pattern_rules(
    text: str,
    patterns: list[re.Pattern[str]],
    style: RedactStyle,
    tag: str,
    vault: TokenVault | None,
) -> str:
    out = text
    repl = _replacer(style, tag, vault)
    for pat in patterns:
        out = pat.sub(repl, out)
    return out


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def transform_text(
    text: str,
    style: RedactStyle,
    *,
    vault: TokenVault | None = None,
) -> str:
    out = text
    for name, rules, tag in RULES:
        if name == "medication":
            out = _apply_token_rules(out, rules, style, tag, vault)  # type: ignore[arg-type]
        else:
            out = _apply_pattern_rules(out, rules, style, tag, vault)  # type: ignore[arg-type]
    if style == "remove":
        out = _normalize_whitespace(out)
    return out
