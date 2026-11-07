"""agentpolicy reference producer adapter (M18).

Design: ``docs/design/v0.1.0/adapters.md``. The broker POSTs a contract-valid ask with the trusted
fields HMAC-signed, then long-polls ``resolve/1.0``. The shared key is a caller-supplied secret (the
caller resolves it from a reference); it is never stored here.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from agentinbox.signing import sign
from agentinbox.store import canonical_json

DEFAULT_TIMEOUT_SECONDS = 10.0


class AdapterError(Exception):
    """The inbox refused the adapter call (bad signature, HTTP error, unreachable)."""


@dataclass(frozen=True, slots=True)
class AgentPolicyClient:
    """The reference producer: ``create`` then ``resolve`` (or ``ask`` for both)."""

    url: str
    token: str
    adapter_key: str
    principal: str | None = None
    adapter: str = "agentpolicy"
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    opener: Callable[..., Any] = urllib.request.urlopen

    # ------------------------------------------------------------------ contract

    def create(self, ask: Mapping[str, Any]) -> dict[str, Any]:
        body = canonical_json(dict(ask)).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "X-AgentInbox-Adapter": self.adapter,
            "X-AgentInbox-Signature": sign(self.adapter_key, body),
        }
        if self.principal:
            headers["X-AgentInbox-Principal"] = self.principal
        request = urllib.request.Request(  # noqa: S310 - caller-supplied loopback URL
            f"{self.url.rstrip('/')}/v1/asks",
            data=body,
            headers=headers,
            method="POST",
        )
        return self._json(request)

    def resolve(
        self,
        ask_id: str,
        *,
        wait: float = 30,
        action_identity: str | None = None,
    ) -> dict[str, Any]:
        query: dict[str, str] = {"wait": f"{wait}s"}
        if action_identity is not None:
            query["action_identity"] = action_identity
        request = urllib.request.Request(  # noqa: S310 - caller-supplied loopback URL
            f"{self.url.rstrip('/')}/v1/asks/{ask_id}?{urllib.parse.urlencode(query)}",
            headers={"Authorization": f"Bearer {self.token}"},
            method="GET",
        )
        return self._json(request)

    def ask(self, ask: Mapping[str, Any], *, wait: float = 30) -> dict[str, Any]:
        created = self.create(ask)
        return self.resolve(created["ask_id"], wait=wait)

    # ------------------------------------------------------------------ internals

    def _json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise AdapterError(f"HTTP {exc.code}: {body}") from None
        except (OSError, ValueError) as exc:
            raise AdapterError(f"inbox unreachable: {exc}") from None
        if not isinstance(payload, dict):
            raise AdapterError("inbox returned a non-object response")
        return payload


__all__ = ["AdapterError", "AgentPolicyClient"]
