"""Redaction before persistence (E6).

Pattern + shape redaction over agent-supplied text. Runs at ingest, before any storage, and
emits receipts (field, class, count) instead of values. The raw value is never persisted,
rendered, or logged.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SECRET = "SECRET"
PRIVATE_KEY = "PRIVATE_KEY"
CONNECTION_STRING = "CONNECTION_STRING"
EMAIL = "EMAIL"
PHONE = "PHONE"

REPLACEMENT = "[REDACTED:{kind}]"

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        PRIVATE_KEY,
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    (
        SECRET,
        re.compile(
            r"(?ix)"
            r"\b(?:"
            r"sk-[a-z0-9_-]{20,}"
            r"|gh[pousr]_[a-z0-9]{20,}"
            r"|xox[baprs]-[a-z0-9-]{10,}"
            r"|akia[0-9a-z]{16}"
            r")\b"
            r"|\bbearer\s+[a-z0-9\-._~+/]{16,}"
        ),
    ),
    (
        CONNECTION_STRING,
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@[^\s]+", re.IGNORECASE),
    ),
    (EMAIL, re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    (
        PHONE,
        re.compile(r"(?<!\d)\+?1?[-. ]?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)"),
    ),
)


@dataclass(frozen=True, slots=True)
class RedactionReceipt:
    field: str
    redaction_class: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "class": self.redaction_class, "count": self.count}


def redact_value(value: Any, field: str) -> tuple[Any, tuple[RedactionReceipt, ...]]:
    """Return ``(redacted, receipts)`` for any JSON-shaped value."""
    counts: dict[tuple[str, str], int] = {}
    redacted = _walk(value, field, counts)
    receipts = tuple(
        RedactionReceipt(field=path, redaction_class=kind, count=count)
        for (path, kind), count in sorted(counts.items())
    )
    return redacted, receipts


def _walk(value: Any, path: str, counts: dict[tuple[str, str], int]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, path, counts)
    if isinstance(value, Mapping):
        return {
            key: _walk(item, f"{path}.{key}" if path else str(key), counts)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _walk(item, f"{path}[{index}]", counts) for index, item in enumerate(value)
        ]
    return value


def _redact_text(text: str, path: str, counts: dict[tuple[str, str], int]) -> str:
    redacted = text
    for kind, pattern in _PATTERNS:
        redacted, replacements = pattern.subn(REPLACEMENT.format(kind=kind), redacted)
        if replacements:
            key = (path, kind)
            counts[key] = counts.get(key, 0) + replacements
    return redacted


__all__ = [
    "CONNECTION_STRING",
    "EMAIL",
    "PHONE",
    "PRIVATE_KEY",
    "REPLACEMENT",
    "SECRET",
    "RedactionReceipt",
    "redact_value",
]
