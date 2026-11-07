"""Shared HMAC signing for outbound adapters and webhooks (M13/M18)."""

from __future__ import annotations

import hashlib
import hmac


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


__all__ = ["sign"]
