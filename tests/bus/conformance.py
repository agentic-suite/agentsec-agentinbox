"""AskBus conformance (M9 item 9.4): every driver has the same movement semantics."""

from __future__ import annotations

from datetime import datetime, timedelta

from agentinbox.bus.base import AskBus, JobKind, new_job


def check_bus_contract(bus: AskBus, *, now: datetime) -> None:
    """Dedupe, not-before scheduling, and at-least-once on handler failure."""
    seen = []

    job = new_job(JobKind.DELIVER, ask_id="ask-1", now=now)
    assert bus.publish(job) is True
    assert bus.publish(job) is False, "republishing the same job must dedupe"
    assert bus.consume(seen.append) == 1
    assert seen == [job]
    assert bus.consume(seen.append) == 0, "a consumed job must not be delivered twice"

    later = new_job(
        JobKind.DELIVER, ask_id="ask-2", now=now, not_before=now + timedelta(seconds=10)
    )
    assert bus.publish(later) is True
    assert bus.consume(seen.append) == 0, "not_before must delay the job"
    assert seen == [job]

    crash = new_job(JobKind.DELIVER, ask_id="ask-3", now=now)
    assert bus.publish(crash) is True

    def boom(_job) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("handler crashed mid-job")

    try:
        bus.consume(boom)
    except RuntimeError:
        pass
    else:  # pragma: no cover - only a broken driver gets here
        raise AssertionError("a handler failure must propagate (at-least-once)")

    assert bus.consume(seen.append) == 1, "a crashed job must be redelivered"
    assert seen[-1] == crash
