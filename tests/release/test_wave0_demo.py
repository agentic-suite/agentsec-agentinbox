"""M33 33.5 — the committed Wave-0 demo evidence is complete and internally consistent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "docs" / "release" / "v0.1.0" / "demo"


def test_demo_evidence_files_exist() -> None:
    for name in (
        "transcript.txt",
        "events.jsonl",
        "export.jsonl",
        "environment.json",
        "checksums.txt",
    ):
        assert (DEMO / name).is_file(), f"missing demo evidence: {name}"


def test_transcript_shows_policy_gate_delivery_and_verify() -> None:
    text = (DEMO / "transcript.txt").read_text(encoding="utf-8")
    for token in (
        "Replit destructive rule",
        "Production-write human gate",
        "ask-raised",
        "delivered: terminal card + desktop notification",
        "terminal decision: deny",
        "verify-log: ok",
    ):
        assert token in text, f"transcript missing {token}"


def test_events_carry_join_keys_and_the_expected_lifecycle() -> None:
    events = [
        json.loads(line)
        for line in (DEMO / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    types = [event["event_type"] for event in events]
    assert types == ["ask-raised", "ask-delivered", "ask-delivered", "ask-answered"]
    for event in events:
        for key in ("ask_id", "session_id", "agent_id", "action_identity"):
            assert event[key], f"event missing {key}"


def test_checksums_match_the_committed_evidence() -> None:
    expected = {}
    for line in (DEMO / "checksums.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    for name, digest in expected.items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == digest


def test_environment_records_both_versions() -> None:
    environment = json.loads((DEMO / "environment.json").read_text(encoding="utf-8"))
    assert environment["agentinbox_version"]
    assert environment["agentpolicy_version"] == "0.1.0"
