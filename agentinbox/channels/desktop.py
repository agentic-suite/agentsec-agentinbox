"""Desktop notification channel: a wake-up, never a decision surface (M8).

Design: ``docs/design/v0.1.0/desktop.md``. The notification carries the fingerprint, class, and
remaining TTL only. It cannot authenticate a principal, so it can never answer an ask: the human
answers in the terminal under the OS session.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agentinbox.card import Card
from agentinbox.channels.base import ChannelError
from agentinbox.config import Config
from agentinbox.store import AskRecord, utcnow

DEFAULT_TIMEOUT_SECONDS = 5.0
ANSWER_FOOTER = "Answer in the terminal: agentinbox answer {ask_id}"


@dataclass(frozen=True, slots=True)
class Notification:
    """A renderer-safe desktop message. It never carries the ask arguments."""

    title: str
    body: str
    thread_id: str
    ask_id: str
    kind: str = "ask"
    tier: str | None = None


class Notifier(Protocol):
    def send(self, notification: Notification) -> None: ...


Runner = Callable[..., "subprocess.CompletedProcess[str]"]


# --------------------------------------------------------------------------- rendering


def render_notification(
    ask: AskRecord,
    *,
    now: datetime,
    tier: str | None = None,
    warning: bool = False,
) -> Notification:
    """Build the notification from the record — never from the card's payload body."""
    trust = ask.payload.get("_trust") or {}
    unverified = set(trust.get("unverified") or [])
    action_class = str(ask.payload.get("class", "unknown"))
    if "class" in unverified:
        action_class = f"[unverified] {action_class}"
    remaining = max(0, int((ask.expires_at - now).total_seconds()))
    parts = [
        action_class,
        _fingerprint(ask.action_identity),
        f"expires in {remaining // 60}m{remaining % 60:02d}s",
    ]
    if tier:
        parts.append(f"tier {tier}")
    body = " · ".join(parts) + "\n" + ANSWER_FOOTER.format(ask_id=ask.ask_id)
    return Notification(
        title=(
            f"Agent ask expiring soon · {action_class}"
            if warning
            else f"Agent ask · {action_class}"
        ),
        body=("expires soon · " if warning else "") + body,
        thread_id=ask.ask_id,
        ask_id=ask.ask_id,
        kind="warn" if warning else "ask",
        tier=tier,
    )


def render_digest(*, window_start: datetime, first_ask_id: str, count: int) -> Notification:
    window = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    return Notification(
        title="Agent flood neutralized",
        body=(
            f"{count} asks denied by flood protection since {window} "
            f"(first: {first_ask_id}).\n"
            "Answer pre-flood pending asks in the terminal: agentinbox inbox"
        ),
        thread_id="digest",
        ask_id=first_ask_id,
        kind="digest",
    )


def _fingerprint(identity: str) -> str:
    value = identity.removeprefix("sha256:")
    return f"sha256:{value[:12]}…" if value else "sha256:unknown"


# --------------------------------------------------------------------------- backends


class MacOSNotifier:
    """macOS Notification Center via ``osascript`` (argv list, never a shell)."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess.run,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._runner = runner
        self._timeout = timeout

    def send(self, notification: Notification) -> None:
        script = (
            f"display notification {_apple_string(notification.body)} "
            f"with title {_apple_string(notification.title)}"
        )
        _invoke(
            ["osascript", "-e", script],
            runner=self._runner,
            timeout=self._timeout,
        )


class LinuxNotifier:
    """Freedesktop notifications via ``notify-send`` (actions intentionally unused)."""

    def __init__(
        self,
        *,
        runner: Runner = subprocess.run,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._runner = runner
        self._timeout = timeout

    def send(self, notification: Notification) -> None:
        _invoke(
            [
                "notify-send",
                "--app-name",
                "agentinbox",
                "--urgency",
                "critical",
                "--hint",
                f"string:x-canonical-private-synchronous:{notification.thread_id}",
                notification.title,
                notification.body,
            ],
            runner=self._runner,
            timeout=self._timeout,
        )


class UnavailableNotifier:
    """No desktop backend on this platform; every delivery fails loudly."""

    def __init__(self, reason: str = "no desktop notification backend on this platform") -> None:
        self._reason = reason

    def send(self, notification: Notification) -> None:
        del notification
        raise ChannelError(self._reason)


def _apple_string(value: str) -> str:
    # A JSON string is a valid AppleScript string literal (double quotes, backslash escapes).
    return json.dumps(value, ensure_ascii=False)


def _invoke(argv: Sequence[str], *, runner: Runner, timeout: float) -> None:
    try:
        runner(
            list(argv),
            shell=False,
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ChannelError(f"desktop notification failed: {exc}") from None


# --------------------------------------------------------------------------- availability


def desktop_availability(
    *,
    platform: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    environ: Mapping[str, str] | None = None,
) -> tuple[bool, str]:
    """Report whether this session can actually show a notification."""
    system = sys.platform if platform is None else platform
    env = os.environ if environ is None else environ

    if system == "darwin":
        if which("osascript") is None:
            return False, "osascript not found on PATH"
        if env.get("SSH_CONNECTION") and not env.get("__CFBundleIdentifier"):
            return False, "headless SSH session (no GUI session to display a notification)"
        return True, "osascript (Notification Center)"

    if system.startswith("linux"):
        if which("notify-send") is None:
            return False, "notify-send not found on PATH"
        if not (env.get("DISPLAY") or env.get("DBUS_SESSION_BUS_ADDRESS")):
            return False, "no DISPLAY or DBUS_SESSION_BUS_ADDRESS (headless session)"
        return True, "notify-send (Freedesktop)"

    return False, f"unsupported platform for desktop notifications: {system}"


def default_notifier() -> Notifier:
    system: str = sys.platform
    if system == "darwin":
        return MacOSNotifier()
    if system.startswith("linux"):
        return LinuxNotifier()
    return UnavailableNotifier()


# --------------------------------------------------------------------------- channel


class DesktopChannel:
    """Deliver-only channel. ``authenticate`` always returns ``None`` (E4)."""

    name = "desktop"

    def __init__(
        self,
        *,
        config: Config,
        notifier: Notifier | None = None,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.config = config
        self.notifier = default_notifier() if notifier is None else notifier
        self._now = now
        self._sent: set[tuple[str, str | None, bool]] = set()
        self._digest_windows: set[datetime] = set()

    def deliver(self, ask: AskRecord, card: Card | None = None) -> None:
        """Deliver at most one notification per (ask, tier, warning state)."""
        # The card body is not a notification source (content rule); only its warning flag is.
        if not self._enabled():
            return
        warning = bool(card.warning) if card is not None else False
        key = (ask.ask_id, ask.tier, warning)
        if key in self._sent:
            return
        self.notifier.send(
            render_notification(
                ask, now=self._now(), tier=ask.tier, warning=warning
            )
        )
        self._sent.add(key)

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        del as_name
        return None

    def notify_digest(self, *, window_start: datetime, first_ask_id: str, count: int) -> None:
        if not self._enabled() or window_start in self._digest_windows:
            return
        self.notifier.send(
            render_digest(window_start=window_start, first_ask_id=first_ask_id, count=count)
        )
        self._digest_windows.add(window_start)

    def _enabled(self) -> bool:
        channel = self.config.channels.get("desktop")
        return channel is not None and channel.enabled


__all__ = [
    "ANSWER_FOOTER",
    "DesktopChannel",
    "LinuxNotifier",
    "MacOSNotifier",
    "Notification",
    "Notifier",
    "UnavailableNotifier",
    "default_notifier",
    "desktop_availability",
    "render_digest",
    "render_notification",
]
