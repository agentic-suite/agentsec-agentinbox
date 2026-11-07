"""Secret references — never literal secrets (M0/M13).

Config carries ``env:NAME`` or ``file:/absolute/path`` references only. Resolution happens at
delivery time, and the resolved value is never logged or persisted.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class SecretError(Exception):
    """A configured reference cannot be resolved (fail closed)."""


def resolve_ref(ref: str | None, *, environ: Mapping[str, str] | None = None) -> str:
    if not ref:
        raise SecretError("missing secret reference")
    env = os.environ if environ is None else environ
    scheme, _, rest = ref.partition(":")
    if scheme == "env":
        value = env.get(rest)
        if not value:
            raise SecretError(f"env reference {rest} is not set")
        return value
    if scheme == "file":
        try:
            value = Path(rest).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise SecretError(f"file reference is unreadable: {exc.strerror}") from None
        if not value:
            raise SecretError("file reference is empty")
        return value
    raise SecretError(f"unknown reference scheme {scheme!r}")


__all__ = ["SecretError", "resolve_ref"]
