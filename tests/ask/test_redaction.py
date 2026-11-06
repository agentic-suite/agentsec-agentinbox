"""Redaction before persistence + receipts (M2 item 2.4, E6/SC-21 groundwork)."""

from __future__ import annotations

from agentinbox.ingest import ingest
from agentinbox.redaction import (
    CONNECTION_STRING,
    EMAIL,
    PRIVATE_KEY,
    SECRET,
    redact_value,
)
from agentinbox.store import canonical_json
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload

OPENAI_KEY = "sk-" + "a1B2c3D4" * 4
GITHUB_TOKEN = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3h2"
EMAIL_ADDRESS = "maya.ops@example-corp.com"
PRIVATE_KEY_BLOCK = (
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1234\n-----END RSA PRIVATE KEY-----"
)
CONNECTION_URL = "postgres://admin:hunter2@db.internal:5432/prod"


def test_secret_patterns_are_replaced() -> None:
    redacted, receipts = redact_value(
        {"command": f"curl -H 'Authorization: Bearer {OPENAI_KEY}'", "token": GITHUB_TOKEN},
        "arguments",
    )

    assert OPENAI_KEY not in canonical_json(redacted)
    assert GITHUB_TOKEN not in canonical_json(redacted)
    assert any(receipt.redaction_class == SECRET for receipt in receipts)


def test_private_key_block_is_removed() -> None:
    redacted, receipts = redact_value({"note": PRIVATE_KEY_BLOCK}, "context")

    assert "MIIEowIBAAKCAQEA1234" not in canonical_json(redacted)
    assert any(receipt.redaction_class == PRIVATE_KEY for receipt in receipts)


def test_connection_string_password_is_removed() -> None:
    redacted, receipts = redact_value({"dsn": CONNECTION_URL}, "arguments")

    assert "hunter2" not in canonical_json(redacted)
    assert any(receipt.redaction_class == CONNECTION_STRING for receipt in receipts)


def test_email_is_a_pii_class() -> None:
    redacted, receipts = redact_value({"requested_for": EMAIL_ADDRESS}, "context")

    assert EMAIL_ADDRESS not in canonical_json(redacted)
    assert any(receipt.redaction_class == EMAIL for receipt in receipts)


def test_nested_paths_and_lists_are_receipted() -> None:
    _redacted, receipts = redact_value(
        {"session_tail": [{"tool": "read", "output": OPENAI_KEY}], "flags": [EMAIL_ADDRESS]},
        "context",
    )

    fields = {receipt.field for receipt in receipts}
    assert "context.session_tail[0].output" in fields
    assert "context.flags[0]" in fields


def test_redaction_is_idempotent() -> None:
    once, _ = redact_value({"k": OPENAI_KEY}, "arguments")
    twice, receipts = redact_value(once, "arguments")

    assert once == twice
    assert receipts == ()


def test_ingest_persists_zero_raw_secrets(store) -> None:  # type: ignore[no-untyped-def]
    body = payload(
        arguments={"command": f"deploy --token {GITHUB_TOKEN}", "dsn": CONNECTION_URL},
        context={"note": PRIVATE_KEY_BLOCK, "owner": EMAIL_ADDRESS},
    )

    result = ingest(
        body,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    stored = canonical_json(dict(result.ask.payload))
    for raw in (GITHUB_TOKEN, CONNECTION_URL, PRIVATE_KEY_BLOCK, EMAIL_ADDRESS, "hunter2"):
        assert raw not in stored

    receipts = result.ask.payload["_redactions"]
    assert receipts, "receipts must ride the stored payload"
    assert all({"field", "class", "count"} <= set(receipt) for receipt in receipts)
    assert any(receipt["field"] == "arguments.command" for receipt in receipts)


def test_audit_entries_carry_no_raw_secret(store) -> None:  # type: ignore[no-untyped-def]
    body = payload(arguments={"command": f"use {OPENAI_KEY}"})

    ingest(
        body,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    audit_text = canonical_json(
        [
            {
                "kind": entry.kind,
                "ref": entry.ref_id,
                "digest": entry.payload_digest,
                "prev": entry.prev_hash,
                "hash": entry.entry_hash,
            }
            for entry in store.audit_entries()
        ]
    )
    assert OPENAI_KEY not in audit_text
