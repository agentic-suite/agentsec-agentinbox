"""Store-level security invariant checks (M22 item 22.3).

These are the checks the release packs and the negative fixtures share: an answer must carry a claim
and a principal, an expiry must resolve to ``expired`` (never allow), and no answer may exist
without a bound identity. They read evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentinbox.store import AskStatus, AskStore


@dataclass(frozen=True, slots=True)
class Violation:
    kind: str
    ask_id: str
    detail: str


def answers_without_claim(store: AskStore) -> list[Violation]:
    violations: list[Violation] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        body = entry.payload
        if body.get("kind") != "answer":
            continue
        if body.get("to_status") not in {AskStatus.APPROVED.value, AskStatus.DENIED.value}:
            continue
        if not body.get("claim_id"):
            violations.append(
                Violation("answer-without-claim", entry.ref_id, "answer has no claim_id")
            )
    return violations


def answers_without_principal(store: AskStore) -> list[Violation]:
    violations: list[Violation] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        body = entry.payload
        if body.get("kind") != "answer":
            continue
        if body.get("to_status") not in {AskStatus.APPROVED.value, AskStatus.DENIED.value}:
            continue
        if not body.get("principal"):
            violations.append(
                Violation(
                    "answer-without-principal", entry.ref_id, "answer has no principal"
                )
            )
    return violations


def expires_that_allowed(store: AskStore) -> list[Violation]:
    violations: list[Violation] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        body = entry.payload
        if body.get("kind") != "expired":
            continue
        if body.get("to_status") != AskStatus.EXPIRED.value:
            violations.append(
                Violation(
                    "expiry-allowed",
                    entry.ref_id,
                    f"expiry settled as {body.get('to_status')!r}",
                )
            )
    return violations


def check_store(store: AskStore) -> list[Violation]:
    return [
        *answers_without_claim(store),
        *answers_without_principal(store),
        *expires_that_allowed(store),
    ]


__all__ = [
    "Violation",
    "answers_without_claim",
    "answers_without_principal",
    "check_store",
    "expires_that_allowed",
]
