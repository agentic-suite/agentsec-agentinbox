#!/usr/bin/env python3
"""Wave-0 release demo: agentpolicy decision -> agentinbox ask -> human deny.

This is the release smoke test (M33 33.5 / #116). It uses the local agentpolicy
engine (never a cloud service) and the real agentinbox ingest API, terminal
channel, desktop channel, audit chain, event tracer, and export/verify path.

The demo records every artifact under ``docs/release/v0.1.0/demo/`` so the
release notes can cite it. It is intentionally a *smoke* test, not a new field
test: the M32 report remains the field-test evidence.

Run with the agentpolicy virtualenv (it has the policy dependencies):

    PYTHONPATH=agentinbox agentpolicy/.venv/bin/python \
      agentinbox/scripts/release/wave0_demo.py

Or set ``AGENTPOLICY_SRC`` to the agentpolicy source tree and use any Python
that can import agentpolicy.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import hashlib
import io
import json
import os
import platform
import secrets
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

# agentinbox is imported from this checkout; agentpolicy is an optional local
# dependency and is reported as BLOCKED when unavailable, never claimed.
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from agentinbox import __version__ as agentinbox_version  # noqa: E402
from agentinbox.adapters import AgentPolicyClient  # noqa: E402
from agentinbox.answers import AnswerVerifier  # noqa: E402
from agentinbox.audit import export_jsonl, export_records  # noqa: E402
from agentinbox.card import build_card  # noqa: E402
from agentinbox.channels.desktop import DesktopChannel  # noqa: E402
from agentinbox.channels.terminal import TerminalChannel  # noqa: E402
from agentinbox.cli import main as cli_main  # noqa: E402
from agentinbox.config import (  # noqa: E402
    ChannelConfig,
    ClassConfig,
    Config,
    ProducerConfig,
)
from agentinbox.contract import compute_action_identity  # noqa: E402
from agentinbox.events import EventTracer, JsonlEventSink  # noqa: E402
from agentinbox.store import DeliveryRecord, to_iso, utcnow  # noqa: E402
from agentinbox.store.sqlite import SqliteStore  # noqa: E402


def _agentpolicy():
    candidates = []
    if os.environ.get("AGENTPOLICY_SRC"):
        candidates.append(Path(os.environ["AGENTPOLICY_SRC"]))
    candidates.append(REPO.parent / "agentpolicy" / "src")
    for candidate in candidates:
        if (candidate / "agentpolicy").is_dir():
            sys.path.insert(0, str(candidate))
            break
    try:
        from agentpolicy import __version__ as policy_version  # type: ignore[import-not-found]
        from agentpolicy.engine.engine import Engine  # type: ignore[import-not-found]
        from agentpolicy.policy.models import default_policy  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"BLOCKED: agentpolicy is not importable: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return policy_version, Engine, default_policy


def _ask_payload(decision: object, *, now: object) -> dict[str, object]:
    """Build a contract-valid ask from an agentpolicy escalate decision."""
    # The policy decided a production write needs a human; the ask records the
    # exact action identity the human is approving/denying.
    arguments = {"command": "deploy_service checkout-api", "timeout_s": 30}
    moment = now  # datetime passed in; kept untyped at the boundary
    body: dict[str, object] = {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": "agent://release-bot",
        "session_id": "sess_wave0_demo",
        "environment": "production",
        "data_class": "restricted",
        "class": "irreversible",
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": getattr(decision, "matched_rule", None) or "production-write",
            "policy_version": getattr(decision, "policy_version", "0.0.0"),
            "clause": getattr(decision, "clause", "human gate"),
        },
        "criticality": getattr(decision, "criticality", "critical"),
        "requested_by": "release-bot",
        "expires_at": to_iso(moment + timedelta(minutes=5)),
        "context": {
            "blast_radius": {
                "resource": "service:checkout-api",
                "reversibility": "irreversible",
                "affected_estimate": "unknown",
            },
            "flags": ["code_freeze_window"],
            "agentpolicy": {
                "decision": getattr(decision, "decision", "escalate"),
                "reason_code": getattr(decision, "reason_code", "escalate_prod_write"),
                "explanation": getattr(decision, "explanation", ""),
            },
            "alternatives": ["staging deploy", "read-only status check"],
        },
    }
    return body


def _config(user: str, key: str) -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300,
                warn_seconds=60,
                require_reason_on_deny=True,
            )
        },
        roster={"tier-1": {"terminal": (user,)}},
        channels={
            "terminal": ChannelConfig(enabled=True),
            "desktop": ChannelConfig(enabled=True),
        },
        producers={"agentpolicy": ProducerConfig(key_ref="env:AGENTINBOX_DEMO_KEY")},
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out: Path) -> int:
    policy_version, Engine, default_policy = _agentpolicy()
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "transcript.txt",
        "events.jsonl",
        "export.jsonl",
        "environment.json",
        "checksums.txt",
    ):
        (out / name).unlink(missing_ok=True)

    user = getpass.getuser()
    key = secrets.token_hex(24)
    os.environ["AGENTINBOX_DEMO_KEY"] = key
    config = _config(user, key)
    transcript = io.StringIO()

    def say(line: str = "") -> None:
        print(line)
        transcript.write(line + "\n")

    with tempfile.TemporaryDirectory(prefix="agentinbox-wave0-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir(parents=True, exist_ok=True)
        store = SqliteStore(home / "inbox.db")
        api = None
        try:
            engine = Engine(default_policy("balanced"))
            replit = engine.evaluate(
                tool_name="drop_database",
                action="delete",
                environment="production",
                data_class="restricted",
                agent_id="release-bot",
            )
            gate = engine.evaluate(
                tool_name="deploy_service",
                action="deploy",
                environment="production",
                data_class="restricted",
                agent_id="release-bot",
            )
            say("Wave-0 demo — agentpolicy -> agentinbox -> human deny")
            say(f"agentinbox {agentinbox_version}; agentpolicy {policy_version}")
            say(
                f"1) Replit destructive rule: drop_database -> {replit.decision} "
                f"({replit.reason_code})"
            )
            say(f"   {replit.explanation}")
            say(
                f"2) Production-write human gate: deploy_service -> {gate.decision} "
                f"({gate.reason_code})"
            )
            say(f"   {gate.explanation}")
            if gate.decision != "escalate":
                say("DEMO FAILED: the production write did not escalate to a human")
                return 3

            from agentinbox.api import start_api

            api = start_api(
                store=store,
                config=config,
                token=secrets.token_hex(16),
                now=utcnow,
                environ={"AGENTINBOX_DEMO_KEY": key},
            )
            client = AgentPolicyClient(
                url=api.url,
                token=api.token,
                adapter_key=key,
                principal="release-bot",
                adapter="agentpolicy",
            )
            body = _ask_payload(gate, now=utcnow())
            created = client.create(body)
            ask_id = str(created["ask_id"])
            ask = store.get(ask_id)
            if ask is None:  # pragma: no cover - API contract guard
                say("DEMO FAILED: ask was not stored")
                return 3
            say(f"3) ask-raised: {ask_id} (session {ask.session_id})")

            card = build_card(ask, now=utcnow(), transitions=store.transitions_for(ask_id))
            deny_reason = "production write denied by release owner"
            terminal = TerminalChannel(
                config=config,
                output=transcript,
                input_fn=lambda prompt: "d" if "approve" in prompt else deny_reason,
                interactive=True,
            )
            desktop = DesktopChannel(config=config)
            terminal.deliver(ask, card)
            desktop.deliver(ask, card)
            moment = utcnow()
            store.record_delivery(
                DeliveryRecord(
                    delivery_id="del_wave0_terminal",
                    ask_id=ask_id,
                    channel="terminal",
                    attempt=1,
                    status="delivered",
                    at=moment,
                    target=user,
                )
            )
            store.record_delivery(
                DeliveryRecord(
                    delivery_id="del_wave0_desktop",
                    ask_id=ask_id,
                    channel="desktop",
                    attempt=1,
                    status="delivered",
                    at=moment,
                    target="notification-center",
                )
            )
            say("4) delivered: terminal card + desktop notification")

            code = terminal.answer(
                store,
                AnswerVerifier(store, config, now=utcnow),
                ask,
                decision="deny",
                reason="production write denied by release owner",
                now=utcnow(),
            )
            say(f"5) terminal decision: deny (exit {int(code)})")
            resolved = client.resolve(ask_id, wait=0)
            say(
                f"6) resolve: {resolved.get('contract')} "
                f"{resolved.get('status')} ({resolved.get('reason_code')})"
            )
            if resolved.get("status") != "deny":
                say("DEMO FAILED: resolve did not deny")
                return 3

            EventTracer(
                store,
                sink=JsonlEventSink(out / "events.jsonl"),
                now=utcnow,
            ).drain()
            events = [
                json.loads(line)
                for line in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            say(f"7) agentwatch events: {[event['event_type'] for event in events]}")
            for event in events:
                for key_name in ("ask_id", "session_id", "agent_id", "action_identity"):
                    if not event.get(key_name):
                        say(f"DEMO FAILED: event missing join key {key_name}")
                        return 3

            records = export_records(store, session_id=ask.session_id, now=utcnow)
            (out / "export.jsonl").write_text(export_jsonl(records), encoding="utf-8")
            say(f"8) export: {len(records)} records")
        finally:
            if api is not None:
                api.stop()
            store.close()

        verify = io.StringIO()
        with contextlib.redirect_stdout(verify):
            verify_code = cli_main(["--home", str(home), "verify-log"])
        say(f"9) verify-log: {verify.getvalue().strip()} (exit {verify_code})")
        if verify_code != 0:
            say("DEMO FAILED: audit chain did not verify")
            return 3

        environment = {
            "agentinbox_version": agentinbox_version,
            "agentpolicy_version": policy_version,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "user": user,
            "session_id": "sess_wave0_demo",
        }
        (out / "environment.json").write_text(
            json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (out / "transcript.txt").write_text(transcript.getvalue(), encoding="utf-8")
        checksums = []
        for file in sorted(out.iterdir()):
            if file.name == "checksums.txt" or file.is_dir():
                continue
            checksums.append(f"{_hash(file)}  {file.name}")
        (out / "checksums.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
        print(f"evidence: {out}")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave-0 release demo (M33 33.5)")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "docs" / "release" / "v0.1.0" / "demo",
        help="evidence directory",
    )
    args = parser.parse_args(argv)
    return run(args.out)


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
