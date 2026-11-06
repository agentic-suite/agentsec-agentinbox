"""Trusted vs untrusted fields (T13).

Trusted-class fields are trusted **only** from an authenticated producer adapter (agentpolicy in
v0.1.0). Agent-supplied strings are always untrusted. A producer cannot self-assert trust by
putting bookkeeping fields in the request body.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRUSTED_FIELDS = (
    "class",
    "criticality",
    "data_class",
    "environment",
    "policy_ref",
    "reason_code",
)
UNTRUSTED_FIELDS = ("arguments", "context")
AGENTPOLICY_ADAPTER = "agentpolicy"


@dataclass(frozen=True, slots=True)
class ProducerIdentity:
    """Who is submitting, and did the adapter authenticate them?"""

    adapter: str | None = None
    authenticated: bool = False
    principal: str | None = None
    remote_addr: str | None = None

    @classmethod
    def unauthenticated(cls, *, remote_addr: str | None = None) -> ProducerIdentity:
        return cls(adapter=None, authenticated=False, remote_addr=remote_addr)


@dataclass(frozen=True, slots=True)
class TrustMap:
    trusted: tuple[str, ...]
    unverified: tuple[str, ...]
    untrusted: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trusted": list(self.trusted),
            "unverified": list(self.unverified),
            "untrusted": list(self.untrusted),
        }


def classify_trust(producer: ProducerIdentity) -> TrustMap:
    if producer.authenticated and producer.adapter:
        return TrustMap(
            trusted=TRUSTED_FIELDS,
            unverified=(),
            untrusted=UNTRUSTED_FIELDS,
        )
    return TrustMap(
        trusted=(),
        unverified=TRUSTED_FIELDS,
        untrusted=UNTRUSTED_FIELDS,
    )


__all__ = [
    "AGENTPOLICY_ADAPTER",
    "TRUSTED_FIELDS",
    "UNTRUSTED_FIELDS",
    "ProducerIdentity",
    "TrustMap",
    "classify_trust",
]
