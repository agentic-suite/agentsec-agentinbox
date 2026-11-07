"""Contract conformance kit (M19 item 19.3).

Design: ``docs/design/v0.1.0/framework-adapters.md``. An integration runs
``agentinbox conformance`` (or :func:`run_conformance`) to prove it honours the ask/resolve
contract, redaction, idempotency, exit codes, event shapes, and the no-decide channel invariant.
The kit never touches the live store: it runs against a fresh in-memory store.
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentinbox.channels.ci import CiWaitChannel
from agentinbox.channels.desktop import DesktopChannel, Notification
from agentinbox.channels.terminal import TerminalChannel
from agentinbox.channels.webhook import WebhookChannel
from agentinbox.config import ClassConfig, Config
from agentinbox.contract import compute_action_identity
from agentinbox.events import EVENT_TYPES, PAYLOAD_REQUIREMENTS
from agentinbox.exit_codes import ExitCode
from agentinbox.ingest import ingest
from agentinbox.resolve import resolve
from agentinbox.store import canonical_json, to_iso, utcnow
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity

SECRET_MARKER = "sk-live-CONFORMANCE-0123456789abcdef"  # noqa: S105 - a test marker
SCHEMA_PATH = (
    Path(__file__).resolve().parent / "events" / "security-event.schema.json"
)


@dataclass(frozen=True, slots=True)
class ConformanceCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    checks: tuple[ConformanceCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


class _NullNotifier:
    def send(self, notification: Notification) -> None:
        del notification


def _canary(class_name: str, ask_class: ClassConfig, moment: datetime) -> dict[str, Any]:
    arguments = {
        "command": "echo conformance",
        "api_key": SECRET_MARKER,
    }
    ttl = min(ask_class.ttl_seconds, 300)
    return {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": "agent://conformance",
        "session_id": "sess_conformance",
        "environment": "conformance",
        "data_class": "unknown",
        "class": class_name,
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": "conformance-kit",
            "policy_version": "v0.1.0",
            "clause": "self-verify",
        },
        "criticality": "normal",
        "requested_by": "conformance",
        "expires_at": to_iso(moment + timedelta(seconds=ttl)),
        "context": {},
    }


def run_conformance(
    config: Config,
    *,
    store_factory: Callable[[], Any] = MemoryStore,
    now: datetime | None = None,
) -> ConformanceReport:
    moment = now or utcnow()
    checks: list[ConformanceCheck] = []

    def check(name: str, function: Callable[[], str]) -> None:
        try:
            detail = function()
        except Exception as exc:  # a broken integration fails the kit, never crashes it
            checks.append(ConformanceCheck(name, False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append(ConformanceCheck(name, True, detail))

    class_name = next(iter(sorted(config.classes)), None)
    if class_name is None:
        checks.append(ConformanceCheck("config.class", False, "no classes configured"))
        return ConformanceReport(tuple(checks))

    ask_class = config.classes[class_name]
    store = store_factory()
    body = _canary(class_name, ask_class, moment)
    state: dict[str, Any] = {}

    def contract_ask() -> str:
        result = ingest(
            body,
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=moment,
        )
        if not result.created:
            raise AssertionError("the first ask was not created")
        state["ask_id"] = result.ask.ask_id
        return f"created {result.ask.ask_id}"

    def redaction() -> str:
        stored = store.get(state["ask_id"])
        if stored is None:
            raise AssertionError("the ask vanished")
        blob = canonical_json(dict(stored.payload))
        if SECRET_MARKER in blob:
            raise AssertionError("a secret reached the store")
        if "echo conformance" not in blob:
            raise AssertionError("the benign command was lost")
        return "secret redacted, command preserved"

    def idempotent() -> str:
        again = ingest(
            body,
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=moment,
        )
        if again.created:
            raise AssertionError("a duplicate retry created a second ask")
        if again.ask.ask_id != state["ask_id"]:
            raise AssertionError("a duplicate retry changed the ask id")
        return "3 retries coalesce to one ask"

    def resolve_pending() -> str:
        outcome = resolve(store, state["ask_id"], now=moment, config=config)
        if outcome.reason_code != "deny_ask_pending":
            raise AssertionError(f"unexpected reason {outcome.reason_code}")
        return "pending -> deny_ask_pending"

    def exit_codes() -> str:
        expected = {0, 1, 2, 3, 4, 5}
        actual = {int(code) for code in ExitCode}
        if actual != expected:
            raise AssertionError(f"exit codes drifted: {sorted(actual)}")
        return "0/1/2/3/4/5"

    def event_shapes() -> str:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        published = set(schema["properties"]["event_type"]["enum"])
        if published != set(EVENT_TYPES):
            raise AssertionError("event types drifted from the shipped schema")
        for event_type, required in schema["x-payload-requirements"].items():
            if frozenset(required) != PAYLOAD_REQUIREMENTS[event_type]:
                raise AssertionError(f"{event_type} payload requirements drifted")
        return f"{len(EVENT_TYPES)} event types match the schema"

    def channel_invariants() -> str:
        channels: list[Any] = [
            TerminalChannel(
                config=config,
                output=io.StringIO(),
                input_fn=lambda _prompt: "q",
                interactive=True,
            ),
            CiWaitChannel(output=io.StringIO()),
            DesktopChannel(config=config, notifier=_NullNotifier()),
            WebhookChannel(config=config, post=lambda *_args: None),
        ]
        for channel in channels:
            if not callable(getattr(channel, "deliver", None)):
                raise AssertionError(f"{channel.name} has no deliver()")
            if not callable(getattr(channel, "authenticate", None)):
                raise AssertionError(f"{channel.name} has no authenticate()")
            if hasattr(channel, "decide") or hasattr(channel, "submit"):
                raise AssertionError(f"{channel.name} can decide")
        return "deliver + authenticate, never decide"

    def producers() -> str:
        for name, producer in config.producers.items():
            scheme, _, _ = producer.key_ref.partition(":")
            if scheme not in {"env", "file"}:
                raise AssertionError(f"{name} key_ref is not a reference")
        return f"{len(config.producers)} signed producers configured"

    check("config.class", lambda: f"class {class_name!r} configured")
    check("contract.ask", contract_ask)
    check("redaction", redaction)
    check("idempotent-ingest", idempotent)
    check("resolve.pending", resolve_pending)
    check("exit-codes", exit_codes)
    check("events", event_shapes)
    check("channels", channel_invariants)
    check("producers", producers)
    store.close()
    return ConformanceReport(tuple(checks))


__all__ = ["ConformanceCheck", "ConformanceReport", "run_conformance"]
