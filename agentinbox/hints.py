"""Rescope-hint authoring (M17 item 17.2).

Hints are advisory text the **agent** reads, never policy and never executable. They are capped,
control-stripped, and labelled as human/derived input.
"""

from __future__ import annotations

import re

HINT_CAP = 400
LABEL = "human-authored hint, not policy"
_CONTROL = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]"
)
_WHITESPACE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    text = _CONTROL.sub("", value)
    return _WHITESPACE.sub(" ", text).strip()


def author_hint(
    raw: str | None,
    *,
    action_class: str,
    environment: str,
    reason: str | None = None,
) -> str:
    """Build the hint from config or a class-aware fallback, echoing the deny reason."""
    label = f"({LABEL})"
    reason_part = f"deny reason: {clean_text(reason)[:120]}" if reason else ""
    reserve = len(label) + 2 + (len(reason_part) + 2 if reason_part else 0)

    if raw:
        body = clean_text(raw)[: max(0, HINT_CAP - reserve)]
    else:
        target = (
            "a narrower target (for example staging)"
            if environment == "production"
            else "a narrower action or resource"
        )
        body = (
            f"narrow the target to {target}, or request a standing approval "
            f"for class {action_class}"
        )
    parts = [body]
    if reason_part:
        parts.append(reason_part)
    parts.append(label)
    return "; ".join(parts)[:HINT_CAP]


__all__ = ["HINT_CAP", "LABEL", "author_hint", "clean_text"]
