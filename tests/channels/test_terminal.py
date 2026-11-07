"""Terminal channel: blocking loop, OS principal, non-interactive never approves (M7)."""

from __future__ import annotations

import getpass
import io

import pytest

from agentinbox.answers import AnswerVerifier
from agentinbox.channels.base import ChannelError
from agentinbox.channels.terminal import TerminalChannel
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.exit_codes import ExitCode
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


@pytest.fixture(autouse=True)
def os_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agentinbox.channels.terminal.getpass.getuser", lambda: "alice")


class Inputs:
    def __init__(self, values: list[str]) -> None:
        self.values = iter(values)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return next(self.values)


def config(*, allow_as: bool = False, roster=("alice", "bob")) -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300,
                warn_seconds=60,
                self_review="deny",
                require_reason_on_deny=True,
                ladder=("tier-1",),
            )
        },
        roster={"tier-1": {"terminal": list(roster)}},
        channels={"terminal": ChannelConfig(enabled=True, allow_as=allow_as)},
    )


def make(store, *, cfg=None):  # type: ignore[no-untyped-def]
    cfg = cfg or config()
    ask = ingest(
        payload(),
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask
    return cfg, ask


def test_non_interactive_never_approves(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    out = io.StringIO()
    channel = TerminalChannel(config=cfg, output=out, input_fn=Inputs([]), interactive=False)

    code = channel.answer(
        store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, decision="approve", now=NOW
    )

    assert code == ExitCode.PENDING
    assert '"status": "pending"' in out.getvalue()
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]
    assert store.export_session(ask.session_id).claims == ()


def test_interactive_approve_with_typed_confirmation(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    out = io.StringIO()
    inputs = Inputs(["a", "run_command"])
    channel = TerminalChannel(config=cfg, output=out, input_fn=inputs, interactive=True)

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.APPROVED
    assert store.get(ask.ask_id).status is AskStatus.APPROVED  # type: ignore[union-attr]
    assert any("action name" in prompt for prompt in inputs.prompts)


def test_interactive_deny_requires_and_records_reason(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    inputs = Inputs(["d", "rollback plan missing"])
    channel = TerminalChannel(config=cfg, output=io.StringIO(), input_fn=inputs, interactive=True)

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.DENIED
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.DENIED
    assert store.transitions_for(ask.ask_id)[-1].reason == "rollback plan missing"


def test_q_leaves_pending(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs(["q"]), interactive=True
    )

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.PENDING
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_wrong_typed_confirmation_is_refused(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs(["a", "nope"]), interactive=True
    )

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.UNAVAILABLE
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_as_is_refused_without_config(store) -> None:  # type: ignore[no-untyped-def]
    cfg, _ask = make(store)
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs([]), interactive=True
    )

    with pytest.raises(ChannelError, match="allow_as"):
        channel.authenticate(as_name="bob")


def test_assumed_principal_is_recorded(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store, cfg=config(allow_as=True))
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs(["a", "run_command"]), interactive=True
    )

    code = channel.answer(
        store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, as_name="bob", now=NOW
    )

    assert code == ExitCode.APPROVED
    transition = store.transitions_for(ask.ask_id)[-1]
    assert transition.principal == "bob"
    assert transition.detail["assumed_principal"] is True


def test_deliver_renders_inert_plain_text(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    out = io.StringIO()
    channel = TerminalChannel(config=cfg, output=out, input_fn=Inputs([]), interactive=True)
    from agentinbox.card import build_card

    channel.deliver(ask, build_card(ask, now=NOW))

    rendered = out.getvalue()
    for block in ("ACTION", "POLICY", "BLAST RADIUS", "SESSION SO FAR"):
        assert block in rendered
    assert "\x1b" not in rendered


def test_channel_contract_has_no_decision_power(store) -> None:  # type: ignore[no-untyped-def]
    cfg, _ask = make(store)
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs([]), interactive=True
    )

    assert channel.name == "terminal"
    assert hasattr(channel, "deliver")
    assert not hasattr(channel, "decide")
    assert channel.authenticate() == getpass.getuser()


def test_unconfigured_terminal_still_authenticates_os_user() -> None:
    channel = TerminalChannel(
        config=Config(classes={}, roster={}),
        output=io.StringIO(),
        input_fn=Inputs([]),
        interactive=True,
    )

    assert channel.authenticate() == getpass.getuser()


class _NoPrincipalChannel(TerminalChannel):
    def authenticate(self, *, as_name: str | None = None) -> str | None:
        return None


def test_missing_principal_is_unavailable(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    channel = _NoPrincipalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs([]), interactive=True
    )

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.UNAVAILABLE
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_unexpected_decision_is_unavailable(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    channel = TerminalChannel(
        config=cfg, output=io.StringIO(), input_fn=Inputs([]), interactive=True
    )

    code = channel.answer(
        store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, decision="bogus", now=NOW
    )

    assert code == ExitCode.UNAVAILABLE
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_choose_help_and_unrecognized_then_quit(store) -> None:  # type: ignore[no-untyped-def]
    cfg, ask = make(store)
    out = io.StringIO()
    channel = TerminalChannel(
        config=cfg, output=out, input_fn=Inputs(["?", "nonsense", "q"]), interactive=True
    )

    code = channel.answer(store, AnswerVerifier(store, cfg, now=lambda: NOW), ask, now=NOW)

    assert code == ExitCode.PENDING
    rendered = out.getvalue()
    assert "a=approve" in rendered
    assert "unrecognized choice" in rendered
