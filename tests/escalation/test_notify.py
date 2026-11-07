"""Escalation notifications: one job per tier, one notification per tier (M11 item 11.4)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.bus import InProcBus, JobKind
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.channels.desktop import DesktopChannel, Notification
from agentinbox.escalation import Escalator
from tests.ask.conftest import NOW
from tests.escalation.conftest import Clock, make_ask, make_config


class Recorder:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> None:
        self.sent.append(notification)


class FakeDesktopConfig:
    """Minimal Config stand-in carrying just the desktop channel flag."""

    def __init__(self, config) -> None:  # type: ignore[no-untyped-def]
        self.classes = config.classes
        self.roster = config.roster
        self.channels = {"desktop": _enabled()}


def _enabled():  # type: ignore[no-untyped-def]
    from agentinbox.config import ChannelConfig

    return ChannelConfig(enabled=True)


def test_one_renotify_job_per_tier(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config(
        tiers=("tier-1", "on-call", "incident-commander"),
        delays=(0, 300, 900),
        roster={
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
            "incident-commander": {"terminal": ("carol",)},
        },
    )
    make_ask(store, config=config)
    bus = InProcBus(now=lambda: NOW)
    clock = Clock(NOW + timedelta(seconds=300))
    escalator = Escalator(store, config, now=clock, bus=bus)

    assert escalator.tick().notified == 1
    assert escalator.tick().notified == 0

    jobs = []
    bus.consume(jobs.append)
    assert [job.kind for job in jobs] == [JobKind.RENOTIFY]
    assert jobs[0].payload["tier"] == "on-call"

    clock.moment = NOW + timedelta(seconds=900)
    assert escalator.tick().notified == 1
    followed = []
    bus.consume(followed.append)
    assert followed[0].payload["tier"] == "incident-commander"
    assert len({job.job_id for job in jobs + followed}) == 2


def test_the_desktop_notifies_once_per_tier(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    make_ask(store, config=config)
    bus = InProcBus(now=lambda: NOW)
    clock = Clock(NOW + timedelta(seconds=300))
    Escalator(store, config, now=clock, bus=bus).tick()

    recorder = Recorder()
    desktop = DesktopChannel(config=FakeDesktopConfig(config), notifier=recorder, now=clock)  # type: ignore[arg-type]
    wiring = DeliveryWiring(store, [desktop], now=clock)
    bus.consume(wiring.handle)

    assert len(recorder.sent) == 1
    assert "on-call" in recorder.sent[0].body

    # A redelivered tier job does not re-ping.
    Escalator(store, config, now=clock, bus=bus).tick()
    bus.consume(wiring.handle)
    assert len(recorder.sent) == 1


def test_escalated_card_carries_history(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.card import build_card

    config = make_config()
    ask = make_ask(store, config=config)
    clock = Clock(NOW + timedelta(seconds=300))
    Escalator(store, config, now=clock).tick()
    stored = store.get(ask.ask_id)
    card = build_card(stored, now=clock(), transitions=store.transitions_for(ask.ask_id))  # type: ignore[arg-type]

    tier_fields = [
        field
        for block in card.blocks
        for field in block.fields
        if field.label == "tier"
    ]
    assert [field.value for field in tier_fields] == ["on-call"]
    assert "tier-1 → on-call" in card.render("text")
