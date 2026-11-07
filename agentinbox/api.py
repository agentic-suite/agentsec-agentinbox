"""Loopback JSON API for ingest and long-poll reads (E1, N-1).

Design: ``docs/design/v0.1.0/ask-contract.md`` §6. The token is a per-process shared secret
compared in constant time; the bind is loopback-only. Long-poll waits on a per-ask event with a
bounded poll fallback, so a missed signal degrades to polling, never to a hang.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.bus.base import AskBus
from agentinbox.config import Config
from agentinbox.contract import ContractError
from agentinbox.flood import FloodGuard
from agentinbox.ingest import TOTAL_CAP_BYTES, ingest
from agentinbox.resolve import resolve
from agentinbox.store import AskStatus, AskStore, StoreError, utcnow
from agentinbox.trust import ProducerIdentity

MAX_WAIT_SECONDS = 30.0
_ASK_PATH = re.compile(r"^/v1/asks/([A-Za-z0-9_-]+)$")
_ANSWER_PATH = re.compile(r"^/v1/asks/([A-Za-z0-9_-]+)/answer$")
_WAIT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)s?$")


@dataclass(frozen=True, slots=True)
class IngestAPI:
    """A running loopback API. ``stop()`` always shuts it down."""

    url: str
    token: str
    _server: ThreadingHTTPServer
    _thread: threading.Thread
    _waiters: dict[str, threading.Event]
    _lock: threading.Lock

    def notify(self, ask_id: str) -> None:
        with self._lock:
            event = self._waiters.get(ask_id)
        if event is not None:
            event.set()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


class _ApiServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        store: AskStore,
        config: Config,
        token: str,
        now: Callable[[], Any],
        bus: AskBus | None = None,
        flood_guard: FloodGuard | None = None,
    ) -> None:
        super().__init__(address, _Handler)
        self.store = store
        self.config = config
        self.token = token
        self.now = now
        self.bus = bus
        self.flood_guard = flood_guard
        self.waiters: dict[str, threading.Event] = {}
        self.waiters_lock = threading.Lock()

    def event_for(self, ask_id: str) -> threading.Event:
        with self.waiters_lock:
            return self.waiters.setdefault(ask_id, threading.Event())


class _Handler(BaseHTTPRequestHandler):
    server: _ApiServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    # ------------------------------------------------------------------ routing

    def do_POST(self) -> None:
        if not self._authorized():
            return

        answer_match = _ANSWER_PATH.fullmatch(self.path)
        if answer_match is not None:
            self._handle_answer(answer_match.group(1))
            return
        if self.path != "/v1/asks":
            self._error(HTTPStatus.NOT_FOUND, "path", "unknown endpoint")
            return

        raw = self._read_body()
        if raw is None:
            return
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "body", "must be valid JSON")
            return
        if not isinstance(body, dict):
            self._error(HTTPStatus.BAD_REQUEST, "body", "must be a JSON object")
            return

        producer = ProducerIdentity.unauthenticated(remote_addr=self.client_address[0])
        try:
            result = ingest(
                body,
                store=self.server.store,
                config=self.server.config,
                producer=producer,
                now=self.server.now(),
                bus=self.server.bus,
                flood_guard=self.server.flood_guard,
            )
        except ContractError as exc:
            self._error(HTTPStatus(exc.status_code), exc.field, exc.message)
            return
        except StoreError:
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE, "store", "store is unavailable (fail-closed)"
            )
            return

        self.server.notify(result.ask.ask_id) if hasattr(self.server, "notify") else None
        self._send(
            HTTPStatus.CREATED if result.created else HTTPStatus.OK,
            {
                "ask_id": result.ask.ask_id,
                "status": result.ask.status.value,
                "created": result.created,
            },
        )

    def _handle_answer(self, ask_id: str) -> None:
        """Raw-API answers are refused: answers come only from an authenticated channel adapter."""
        raw = self._read_body()
        if raw is None:
            return
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "body", "must be valid JSON")
            return
        if not isinstance(body, dict):
            self._error(HTTPStatus.BAD_REQUEST, "body", "must be a JSON object")
            return
        if body.get("decision") not in {"approve", "deny"}:
            self._error(HTTPStatus.BAD_REQUEST, "decision", "must be approve or deny")
            return
        if self.server.store.get(ask_id) is None:
            self._error(HTTPStatus.NOT_FOUND, "ask_id", "unknown ask")
            return

        request = AnswerRequest(
            ask_id=ask_id,
            claim_id=str(body.get("claim_id", "")),
            secret=str(body.get("secret", "")),
            principal=str(body.get("principal", "")),
            channel=str(body.get("channel", "api")),
            decision=str(body["decision"]),
            reason=body.get("reason"),
            typed_confirmation=body.get("typed_confirmation"),
        )
        verifier = AnswerVerifier(self.server.store, self.server.config, now=self.server.now)
        try:
            verifier.submit(request, channel_authenticated=False)
        except AnswerRejected:
            self._error(
                HTTPStatus.FORBIDDEN, "authorization", "answers require an authenticated channel"
            )
            return
        self._send(HTTPStatus.OK, {"ask_id": ask_id, "status": "resolved"})

    def do_GET(self) -> None:
        if not self._authorized():
            return
        parsed = urlparse(self.path)
        match = _ASK_PATH.fullmatch(parsed.path)
        if match is None:
            self._error(HTTPStatus.NOT_FOUND, "path", "unknown endpoint")
            return

        ask_id = match.group(1)
        query = parse_qs(parsed.query)
        wait_seconds = _parse_wait(query.get("wait", [None])[0])
        presented = query.get("action_identity", [None])[0]
        ask = self.server.store.get(ask_id)
        if ask is None:
            outcome = resolve(
                self.server.store,
                ask_id,
                now=self.server.now(),
                config=self.server.config,
            )
            self._send(HTTPStatus.NOT_FOUND, outcome.to_dict())
            return

        if presented is not None and presented != ask.action_identity:
            outcome = resolve(
                self.server.store,
                ask_id,
                now=self.server.now(),
                config=self.server.config,
                action_identity=presented,
            )
            self._send(HTTPStatus.OK, outcome.to_dict())
            return

        if wait_seconds and ask.status is AskStatus.PENDING:
            event = self.server.event_for(ask_id)
            deadline = time.monotonic() + wait_seconds
            while ask is not None and ask.status is AskStatus.PENDING:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                event.wait(min(remaining, 0.05))
                event.clear()
                ask = self.server.store.get(ask_id)

        outcome = resolve(
            self.server.store,
            ask_id,
            now=self.server.now(),
            config=self.server.config,
            action_identity=presented,
        )
        self._send(HTTPStatus.OK, outcome.to_dict())

    # ------------------------------------------------------------------ helpers

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        candidate = header[7:] if header.startswith("Bearer ") else ""
        if not candidate:
            candidate = self.headers.get("X-AgentInbox-Token", "")
        if hmac.compare_digest(candidate, self.server.token):
            return True
        self._error(HTTPStatus.UNAUTHORIZED, "authorization", "missing or invalid token")
        return False

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "body", "invalid Content-Length")
            return None
        if length > TOTAL_CAP_BYTES + 4096:
            # Drain the declared body so the client sees the 413 instead of a reset.
            self.rfile.read(length)
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body", "payload too large")
            return None
        if length <= 0:
            self._error(HTTPStatus.BAD_REQUEST, "body", "empty body")
            return None
        return self.rfile.read(length)

    def _error(self, status: HTTPStatus, field: str, message: str) -> None:
        self._send(status, {"error": {"field": field, "message": message}})

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def _parse_wait(raw: str | None) -> float:
    if raw is None:
        return 0.0
    match = _WAIT_PATTERN.fullmatch(raw)
    if match is None:
        return 0.0
    return min(float(match.group(1)), MAX_WAIT_SECONDS)


def start_api(
    *,
    store: AskStore,
    config: Config,
    token: str,
    port: int = 0,
    now: Callable[[], Any] = utcnow,
    bus: AskBus | None = None,
    flood_guard: FloodGuard | None = None,
) -> IngestAPI:
    """Bind to loopback and start serving in a daemon thread."""
    guard = (
        flood_guard
        if flood_guard is not None
        else FloodGuard(store, config, now=now, bus=bus)
    )
    server = _ApiServer(
        ("127.0.0.1", port),
        store=store,
        config=config,
        token=token,
        now=now,
        bus=bus,
        flood_guard=guard,
    )
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.05), daemon=True
    )
    thread.start()
    host, bound_port = server.server_address[:2]
    host_text = host.decode() if isinstance(host, bytes) else host
    return IngestAPI(
        url=f"http://{host_text}:{bound_port}",
        token=token,
        _server=server,
        _thread=thread,
        _waiters=server.waiters,
        _lock=server.waiters_lock,
    )


__all__ = ["MAX_WAIT_SECONDS", "IngestAPI", "start_api"]
