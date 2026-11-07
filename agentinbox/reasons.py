"""The frozen agentpolicy reason-code registry (M17, D-6).

Codes are imported from here — never re-spelled at a call site. The mapping table in
``docs/reference/resolve.md`` is the human copy of this registry.
"""

from __future__ import annotations

ALLOW_ASK_APPROVED = "allow_ask_approved"
DENY_ASK_DENIED = "deny_ask_denied"
HUMAN_GATE_TIMEOUT = "human_gate_timeout"
DENY_ASK_PENDING = "deny_ask_pending"
DENY_ASK_UNKNOWN = "deny_ask_unknown"
DENY_ACTION_IDENTITY_MISMATCH = "deny_action_identity_mismatch"
ASK_FLOOD_THROTTLED = "ask_flood_throttled"

REASON_CODES = frozenset(
    {
        ALLOW_ASK_APPROVED,
        DENY_ASK_DENIED,
        HUMAN_GATE_TIMEOUT,
        DENY_ASK_PENDING,
        DENY_ASK_UNKNOWN,
        DENY_ACTION_IDENTITY_MISMATCH,
        ASK_FLOOD_THROTTLED,
    }
)

__all__ = [
    "ALLOW_ASK_APPROVED",
    "ASK_FLOOD_THROTTLED",
    "DENY_ACTION_IDENTITY_MISMATCH",
    "DENY_ASK_DENIED",
    "DENY_ASK_PENDING",
    "DENY_ASK_UNKNOWN",
    "HUMAN_GATE_TIMEOUT",
    "REASON_CODES",
]
