"""Claim tokens: mint, hash, bind, revoke (M6, E3).

A claim is a single-use answer token. The 128-bit secret is returned **once** to the channel
adapter; the store keeps only ``sha256(secret)``. Binding is by ``ask_id`` + ``channel`` + tier at
issue time, plus the ask's immutable ``action_identity`` at verification time.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime

from agentinbox.store import AskRecord, AskStore, ClaimRecord


@dataclass(frozen=True, slots=True)
class MintedClaim:
    claim: ClaimRecord
    secret: str


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def mint_claim(
    store: AskStore,
    ask: AskRecord,
    *,
    channel: str,
    tier: str | None,
    now: datetime,
    secret: str | None = None,
) -> MintedClaim:
    """Mint and persist a claim; the returned secret must never be stored by the caller."""
    raw = secret or secrets.token_hex(16)  # 128 bits
    claim = ClaimRecord(
        claim_id="cl_" + secrets.token_hex(8),
        ask_id=ask.ask_id,
        channel=channel,
        tier=tier,
        secret_hash=hash_secret(raw),
        issued_at=now,
        expires_at=ask.expires_at,
    )
    store.issue_claim(claim)
    return MintedClaim(claim=claim, secret=raw)


def secret_matches(claim: ClaimRecord, secret: str) -> bool:
    return hmac.compare_digest(claim.secret_hash, hash_secret(secret))


__all__ = ["MintedClaim", "hash_secret", "mint_claim", "secret_matches"]
