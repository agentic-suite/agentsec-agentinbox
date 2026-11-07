"""Command-line entry point and the frozen v0.1.0 command surface.

Design of record: ``docs/design/v0.1.0/foundation.md`` §2-§3. Two rules are load-bearing:

* an unimplemented command **refuses** with exit ``4`` (unavailable/fail-closed) and a one-line
  message — it never exits ``0``, because ``0`` means "approved";
* usage mistakes exit ``1``, not argparse's default ``2`` — ``2`` is the *denied* decision and
  must never be produced by the CLI's own parse errors.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import secrets as _secrets
import shlex
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn

from agentinbox import __version__
from agentinbox.alternatives import prior_objections
from agentinbox.answers import AnswerVerifier
from agentinbox.api import start_api
from agentinbox.audit import (
    apply_retention,
    export_csv,
    export_jsonl,
    export_records,
    read_audit_entries,
)
from agentinbox.bus import (
    BusError,
    DeliveryWiring,
    Job,
    JobPublisher,
    load_bus,
    load_publisher,
)
from agentinbox.card import build_card
from agentinbox.channels.base import ChannelError
from agentinbox.channels.desktop import DesktopChannel, desktop_availability
from agentinbox.channels.terminal import TerminalChannel
from agentinbox.config import (
    Config,
    ConfigError,
    init_home,
    load_config,
    resolve_config_path,
    resolve_home,
)
from agentinbox.config_audit import record_config_change, record_config_failure
from agentinbox.conformance import run_conformance
from agentinbox.contract import ContractError, compute_action_identity
from agentinbox.doctor import render_explain, render_human, run_checks
from agentinbox.escalation import Escalator
from agentinbox.events import BufferedEventSink, EventTracer, JsonlEventSink
from agentinbox.exit_codes import ExitCode
from agentinbox.flood import FloodGuard
from agentinbox.gate import gate
from agentinbox.grants import grant_for_card
from agentinbox.ingest import ingest
from agentinbox.logsafe import sanitize_log_line
from agentinbox.operations import handoff_for
from agentinbox.ops import (
    OpsError,
    backup_home,
    clear_daemon_lock,
    daemon_alive,
    install_service,
    read_daemon_lock,
    restore_home,
    write_daemon_lock,
)
from agentinbox.outcomes import decision_packet, packet_json
from agentinbox.parity import prior_asks
from agentinbox.readiness import similar_cases
from agentinbox.reload import ConfigHolder
from agentinbox.report import build_report
from agentinbox.resolve import resolve
from agentinbox.scheduler import Scheduler
from agentinbox.secrets import SecretError, resolve_ref
from agentinbox.store import (
    AskStore,
    ChainHashMismatch,
    StoreError,
    parse_iso,
    to_iso,
    utcnow,
    verify_audit_chain,
)
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity

PROG = "agentinbox"

#: Commands that exist in v0.1.0 and the milestone that makes each real.
COMMAND_MILESTONES: dict[str, str] = {
    "init": "M0",
    "doctor": "M0",
    "version": "M0",
    "channels": "M13",
    "ask": "M18",
    "inbox": "M7",
    "answer": "M7",
    "serve": "M9",
    "gate": "M10",
    "export": "M15",
    "verify-log": "M15",
    "report": "M21",
    "conformance": "M19",
}

COMMAND_HELP: dict[str, str] = {
    "init": "scaffold the config file and home layout",
    "doctor": "check the install (home, config, store, schema, clock)",
    "version": "print the version",
    "channels": "list configured channels and their health",
    "ask": "propose an ask and wait for a decision",
    "inbox": "review pending asks interactively",
    "answer": "answer a pending ask",
    "serve": "run the local daemon",
    "gate": "CI checkpoint: block until an ask is decided",
    "export": "export asks and the audit log",
    "verify-log": "verify the audit hash chain",
    "report": "print the success-metric report",
    "conformance": "run the contract conformance kit",
}

Handler = Callable[[argparse.Namespace], int]


class CliParser(argparse.ArgumentParser):
    """Usage errors exit ``1`` — never ``2``, which the decision contract reserves for deny."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        print(f"{PROG}: error: {sanitize_log_line(message)}", file=sys.stderr)
        raise SystemExit(1)


def _init(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
        config_path = resolve_config_path(home, args.config)
        init_home(home, config_path, force=bool(args.force))
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)
    print(f"{PROG}: wrote {config_path}")
    return int(ExitCode.APPROVED)


def _doctor(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
        config_path = resolve_config_path(home, args.config)
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    if getattr(args, "backup", None):
        try:
            backup = backup_home(home, Path(args.backup), config_path=config_path)
        except (ConfigError, OpsError) as exc:
            print(f"{PROG}: backup failed: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        print(
            f"{PROG}: backup {backup.path} "
            f"({backup.asks} asks, {backup.audit_entries} audit entries)"
        )
        return int(ExitCode.APPROVED)

    if getattr(args, "restore", None):
        try:
            restored = restore_home(
                Path(args.restore), home, force=bool(getattr(args, "force", False))
            )
        except OpsError as exc:
            print(f"{PROG}: restore failed: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        print(
            f"{PROG}: restored {restored.home} "
            f"({restored.asks} asks, {restored.expired} overdue expired)"
        )

    report = run_checks(home, config_path)
    if args.json:
        print(
            json.dumps(
                [{"id": c.id, "status": c.status, "detail": c.detail} for c in report.checks]
            )
        )
    else:
        print(render_human(report))
        if args.explain:
            explanation = render_explain(report, home, config_path)
            if explanation is None:
                print("explain unavailable: config is invalid")
            else:
                print(explanation)
    return int(ExitCode.APPROVED if report.ok else ExitCode.UNAVAILABLE)


def _runtime(args: argparse.Namespace) -> tuple[Config, AskStore]:
    home = resolve_home(args.home)
    config_path = resolve_config_path(home, args.config)
    config = load_config(config_path)
    store = load_store(config.store.driver, home=home)
    return config, store


def _close_store(store: AskStore) -> None:
    """Close deterministically at every exit path (pytest 9 GC must never reap it)."""
    with contextlib.suppress(Exception):
        store.close()


def _answer(args: argparse.Namespace) -> int:
    try:
        config, store = _runtime(args)
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    ask = store.get(args.ask_id)
    if ask is None:
        print(f"{PROG}: unknown ask: {args.ask_id}", file=sys.stderr)
        return int(ExitCode.DENIED)

    decision = "approve" if args.approve else "deny" if args.deny else None
    try:
        edits = _parse_edits(args.edit)
    except ValueError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE)
    channel = TerminalChannel(
        config=config,
        output=sys.stdout,
        input_fn=input,
        interactive=sys.stdin.isatty(),
    )
    try:
        return channel.answer(
            store,
            AnswerVerifier(store, config),
            ask,
            decision=decision,
            reason=args.reason,
            as_name=args.as_name,
            alternative_id=args.alternative,
            edits=edits,
        )
    except ChannelError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)


def _inbox(args: argparse.Namespace) -> int:
    try:
        _config, store = _runtime(args)
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    pending = store.list_pending(now=utcnow(), limit=200)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "ask_id": ask.ask_id,
                        "class": ask.payload.get("class", "unknown"),
                        "expires_at": ask.expires_at.isoformat(),
                        "action": ask.payload.get("action", "unknown"),
                    }
                    for ask in pending
                ],
                sort_keys=True,
            )
        )
    else:
        if not pending:
            print("no pending asks")
        for ask in pending:
            print(f"{ask.ask_id}  {ask.payload.get('class', 'unknown')}  "
                  f"{ask.payload.get('action', 'unknown')}  expires {ask.expires_at.isoformat()}")
    return int(ExitCode.APPROVED if not pending else ExitCode.PENDING)


def _exec_ask_body(args: argparse.Namespace, config: Config) -> dict[str, Any]:
    class_name = args.ask_class or "irreversible"
    ask_class = config.classes.get(class_name)
    if ask_class is None:
        raise ConfigError(f"unknown class: {class_name!r}")
    command = args.exec_command
    if not command or not command.strip():
        raise ValueError("--exec needs a non-empty command")
    now = utcnow()
    ttl = ask_class.ttl_seconds if args.ttl is None else args.ttl
    if ttl <= 0 or ttl > ask_class.ttl_seconds:
        raise ConfigError(
            f"--ttl must be between 1 and the class ceiling ({ask_class.ttl_seconds}s)"
        )
    arguments = {"command": command}
    return {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": args.agent_id or "agent://agentinbox-cli",
        "session_id": args.session_id or f"cli_{_secrets.token_hex(8)}",
        "environment": args.environment or "local",
        "data_class": "unknown",
        "class": class_name,
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": "cli-exec",
            "policy_version": "v0.1.0",
            "clause": "local CLI producer",
        },
        "criticality": "normal",
        # The requester is the agent, not the human who happens to run the CLI (self-review).
        "requested_by": (
            args.requested_by or args.agent_id or "agent://agentinbox-cli"
        ),
        "expires_at": to_iso(now + timedelta(seconds=ttl)),
        "context": {},
    }


def _ask(args: argparse.Namespace) -> int:
    try:
        config, store = _runtime(args)
        publisher = load_publisher(config, home=resolve_home(args.home))
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)
    try:
        return _ask_impl(args, config, store, publisher)
    finally:
        store.close()
        publisher.close()


def _ask_impl(
    args: argparse.Namespace,
    config: Config,
    store: AskStore,
    publisher: JobPublisher,
) -> int:
    if args.file:
        try:
            body = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{PROG}: cannot read --file: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        if not isinstance(body, dict):
            print(f"{PROG}: --file must contain a JSON object", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
    else:
        try:
            body = _exec_ask_body(args, config)
        except ConfigError as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        except ValueError as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return int(ExitCode.USAGE)

    try:
        result = ingest(
            body,
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            flood_guard=FloodGuard(store, config),
            bus=publisher,
        )
    except ContractError as exc:
        if exc.details:
            payload = {"field": exc.field, "message": exc.message, **exc.details}
            print(
                json.dumps({"error": payload}, sort_keys=True), file=sys.stderr
            )
        else:
            print(
                f"{PROG}: {sanitize_log_line(exc.field)}: {sanitize_log_line(exc.message)}",
                file=sys.stderr,
            )
        return int(ExitCode.UNAVAILABLE)
    except StoreError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    ask_id = result.ask.ask_id
    gate_result = gate(
        store,
        ask_id,
        wait=True,
        timeout=args.timeout,
        principal=os.environ.get("USER"),
    )
    code = gate_result.code
    outcome = resolve(store, ask_id, now=utcnow(), config=config)

    if args.exec_command:
        if code is not ExitCode.APPROVED:
            print(
                f"{PROG}: {outcome.reason_code}; command not executed",
                file=sys.stderr,
            )
            return int(code)
        argv = shlex.split(args.exec_command)
        if not argv:
            print(f"{PROG}: empty --exec command", file=sys.stderr)
            return int(ExitCode.USAGE)
        print(f"{PROG}: approved; executing: {args.exec_command}", file=sys.stderr)
        return subprocess.run(argv, check=False).returncode  # noqa: S603 - gated argv

    if getattr(args, "json", False):
        print(json.dumps(outcome.to_dict(), sort_keys=True))
    else:
        print(f"{PROG}: ask {ask_id}: {outcome.status} ({outcome.reason_code})")
    return int(code)


def _gate(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
        _config, store = _runtime(args)
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    cancel = threading.Event()

    def on_signal(_signum: int, _frame: object) -> None:
        cancel.set()

    previous: list[tuple[int, Any]] = []
    for signum in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(ValueError, OSError):
            # Not the main thread (tests embed main()) — cancellation is simply unavailable.
            previous.append((signum, signal.signal(signum, on_signal)))

    # A lock left by a dead daemon is fail-closed: no decision can arrive while it is gone.
    alive = (lambda: daemon_alive(home)) if read_daemon_lock(home) is not None else None
    try:
        result = gate(
            store,
            args.ask,
            wait=bool(args.wait),
            timeout=args.timeout,
            cancel=cancel,
            principal=os.environ.get("USER"),
            daemon_alive=alive,
        )
    except Exception as exc:  # any failure is fail-closed exit 4
        print(f"{PROG}: gate unavailable: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)
    finally:
        for previous_signum, handler in previous:
            with contextlib.suppress(ValueError, OSError, TypeError):
                signal.signal(previous_signum, handler)

    ask = store.get(args.ask)
    if ask is not None:
        card = build_card(
            ask,
            now=utcnow(),
            transitions=store.transitions_for(ask.ask_id),
            prior_asks=prior_asks(store, ask),
            similar_cases=similar_cases(store, ask),
            prior_objections=prior_objections(store, ask),
            handoff=handoff_for(store.transitions_for(ask.ask_id)),
            grant=grant_for_card(store, ask),
        )
        sys.stdout.write(card.render("ci"))
    if result.code is ExitCode.UNAVAILABLE:
        print(f"{PROG}: gate unavailable: {result.reason}", file=sys.stderr)
    print(f"{PROG}: ask {args.ask}: {result.status} ({result.reason})")
    _close_store(store)
    return int(result.code)


def _serve(args: argparse.Namespace) -> int:
    if getattr(args, "install", False):
        try:
            home = resolve_home(args.home)
            config_path = resolve_config_path(home, args.config)
            load_config(config_path)  # never install a unit for an invalid config
            unit = install_service(home, config_path)
        except (ConfigError, OpsError) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        print(f"{PROG}: wrote {unit.path}")
        return int(ExitCode.APPROVED)

    try:
        config, store = _runtime(args)
        home = resolve_home(args.home)
        config_path = resolve_config_path(home, args.config)
        holder = ConfigHolder(config_path)
        bus = load_bus(config, home=home)
    except (ConfigError, StoreError, BusError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    try:
        record_config_change(home, config)
    except OSError as exc:
        print(f"{PROG}: config-change evidence unavailable: {exc}", file=sys.stderr)

    write_daemon_lock(home)

    def make_digest(
        desktop: DesktopChannel | None,
    ) -> Callable[[Job], None]:
        def on_digest(job: Job) -> None:
            if desktop is None:
                return
            payload = job.payload
            try:
                window_start = parse_iso(str(payload["window_start"]))
                desktop.notify_digest(
                    window_start=window_start,
                    first_ask_id=job.ask_id,
                    count=int(payload.get("count", 0)),
                )
            except (KeyError, ValueError, ChannelError) as exc:
                print(f"{PROG}: digest delivery failed: {exc}", file=sys.stderr)

        return on_digest

    def build_channels(
        current: Config,
    ) -> tuple[list[object], Callable[[Job], None]]:
        desktop_config = current.channels.get("desktop")
        desktop = (
            DesktopChannel(config=current)
            if desktop_config is not None and desktop_config.enabled
            else None
        )
        return (
            [desktop] if desktop is not None else [],
            make_digest(desktop),
        )

    channels, on_digest = build_channels(config)
    try:
        apply_retention(store, config)
    except StoreError as exc:
        print(f"{PROG}: retention failed: {exc}", file=sys.stderr)

    api: Any = None
    state: dict[str, DeliveryWiring] = {
        "wiring": DeliveryWiring(store, channels, on_digest=on_digest)
    }

    def handle(job: Job) -> None:
        state["wiring"].handle(job)

    scheduler = Scheduler(
        store, escalator=Escalator(store, config, bus=bus), bus=bus
    )

    def on_hup(_signum: int, _frame: object) -> None:
        result = holder.reload()
        if not result.ok:
            record_config_failure(home, result.error or "invalid config")
            print(f"{PROG}: config reload refused: {result.error}", file=sys.stderr)
            return
        new_channels, new_digest = build_channels(result.config)
        state["wiring"] = DeliveryWiring(
            store, new_channels, on_digest=new_digest
        )
        scheduler.escalator = Escalator(store, result.config, bus=bus)
        if api is not None:
            api.update_config(
                result.config,
                flood_guard=FloodGuard(store, result.config, bus=bus),
            )
        try:
            apply_retention(store, result.config)
        except StoreError as exc:
            print(f"{PROG}: retention failed: {exc}", file=sys.stderr)
        record_config_change(home, result.config)
        print(f"{PROG}: config reloaded")

    with contextlib.suppress(ValueError, OSError):
        signal.signal(signal.SIGHUP, on_hup)

    tracer = EventTracer(
        store,
        sink=BufferedEventSink(
            JsonlEventSink(home / "logs" / "events.jsonl")
        ),
        state_path=home / "logs" / "events.seq",
    )
    try:
        if args.once:
            scheduler.tick()
            bus.consume(handle)
            tracer.drain()
            tracer.sink.flush()
            return int(ExitCode.APPROVED)

        if not args.no_api:
            token = os.environ.get("AGENTINBOX_API_TOKEN") or _secrets.token_hex(32)
            token_path = home / "api-token"
            token_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
                token_file.write(token + "\n")
            try:
                api = start_api(
                    store=store,
                    config=config,
                    token=token,
                    port=args.api_port,
                    bus=bus,
                    flood_guard=FloodGuard(store, config, bus=bus),
                )
            except OSError as exc:
                print(f"{PROG}: API bind failed: {exc}", file=sys.stderr)
                return int(ExitCode.UNAVAILABLE)
            print(f"{PROG}: api {api.url} (token: {token_path})")

        stop = threading.Event()
        thread, scheduler_stop = scheduler.start()
        trace_stop = threading.Event()

        def trace_loop() -> None:
            while not trace_stop.is_set():
                tracer.drain()
                tracer.sink.flush()
                trace_stop.wait(1.0)

        trace_thread = threading.Thread(target=trace_loop, daemon=True)
        trace_thread.start()

        def on_stop(_signum: int, _frame: object) -> None:
            # Stop accepting work; the finally block flushes and closes cleanly.
            stop.set()

        previous: list[tuple[int, Any]] = []
        for signum in (signal.SIGTERM, signal.SIGINT):
            with contextlib.suppress(ValueError, OSError):
                previous.append((signum, signal.signal(signum, on_stop)))

        try:
            bus.run(handle, stop)
        except KeyboardInterrupt:
            pass
        finally:
            for previous_signum, handler in previous:
                with contextlib.suppress(ValueError, OSError, TypeError):
                    signal.signal(previous_signum, handler)
            scheduler_stop.set()
            trace_stop.set()
            thread.join(timeout=2)
            trace_thread.join(timeout=2)
            tracer.drain()
            tracer.sink.flush()
            if api is not None:
                api.stop()
        return int(ExitCode.APPROVED)
    finally:
        clear_daemon_lock(home)
        bus.close()
        store.close()


def _verify_log(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    try:
        # Read-only: verify-log must not migrate or write the store it inspects.
        entries = read_audit_entries(home / "inbox.db")
        verify_audit_chain(entries)
    except ChainHashMismatch as exc:
        print(f"{PROG}: chain verification failed: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)
    except StoreError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    print(f"ok: {len(entries)} audit entries verify")
    return int(ExitCode.APPROVED)


def _export(args: argparse.Namespace) -> int:
    try:
        _config, store = _runtime(args)
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    try:
        if getattr(args, "packet", False):
            if not args.ask:
                print(f"{PROG}: --packet requires --ask", file=sys.stderr)
                return int(ExitCode.USAGE)
            try:
                packet = decision_packet(store, args.ask)
            except KeyError as exc:
                print(f"{PROG}: {exc.args[0]}", file=sys.stderr)
                return int(ExitCode.UNAVAILABLE)
            text = packet_json(packet)
            if args.out:
                path = Path(args.out)
                if not path.is_absolute():
                    print(f"{PROG}: --out must be an absolute path", file=sys.stderr)
                    return int(ExitCode.USAGE)
                path.write_text(text, encoding="utf-8")
                with contextlib.suppress(OSError):  # pragma: no cover
                    os.chmod(path, 0o600)
                print(f"{PROG}: wrote {path}")
            else:
                sys.stdout.write(text)
            return int(ExitCode.APPROVED)

        try:
            records = export_records(
                store,
                session_id=args.session,
                ask_id=args.ask,
                format=args.format,
                now=utcnow,
            )
        except KeyError as exc:
            print(f"{PROG}: {exc.args[0]}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)
        except (StoreError, ValueError) as exc:
            print(f"{PROG}: {exc}", file=sys.stderr)
            return int(ExitCode.UNAVAILABLE)

        text = export_jsonl(records) if args.format == "jsonl" else export_csv(records)
        if args.out:
            path = Path(args.out)
            if not path.is_absolute():
                print(f"{PROG}: --out must be an absolute path", file=sys.stderr)
                return int(ExitCode.USAGE)
            path.write_text(text, encoding="utf-8")
            with contextlib.suppress(OSError):  # pragma: no cover - exotic filesystems
                os.chmod(path, 0o600)
            print(f"{PROG}: wrote {path}")
        else:
            sys.stdout.write(text)
        return int(ExitCode.APPROVED)
    finally:
        _close_store(store)


def _parse_edits(raw: list[str]) -> dict[str, object] | None:
    if not raw:
        return None
    edits: dict[str, object] = {}
    for item in raw:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise ValueError(f"--edit must be KEY=VALUE (got {item!r})")
        edits[key] = value
    return edits


def _report(args: argparse.Namespace) -> int:
    try:
        _config, store = _runtime(args)
    except (ConfigError, StoreError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    try:
        data = build_report(store).to_dict()

        if getattr(args, "json", False):
            print(json.dumps(data, sort_keys=True))
            return int(ExitCode.APPROVED)

        response = data["response_time_s"]
        print(f"asks: {data['total_asks']} (pending {data['pending']})")
        print(
            f"response p50/p99: {response['p50']}s / {response['p99']}s "
            f"({response['samples']} samples)"
        )
        print(
            f"expiries: {data['expiries']} · escalations: {data['escalation_firings']} · "
            f"floods: {data['flood_events']}"
        )
        causes = data["answer_rejected_causes"]
        if causes:
            rendered = ", ".join(f"{cause}={count}" for cause, count in causes.items())
            print(f"answer rejected: {rendered}")
        for class_name, rate in data["deny_rate_by_class"].items():
            print(f"deny rate {class_name}: {rate:.0%}")
        return int(ExitCode.APPROVED)

    finally:
        _close_store(store)


def _conformance(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
        config = load_config(resolve_config_path(home, args.config))
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    report = run_conformance(config)
    if args.json:
        print(
            json.dumps(
                [
                    {"name": check.name, "ok": check.ok, "detail": check.detail}
                    for check in report.checks
                ]
            )
        )
    else:
        for check in report.checks:
            print(f"{'ok' if check.ok else 'FAIL':4} {check.name}: {check.detail}")
    return int(ExitCode.APPROVED if report.ok else ExitCode.UNAVAILABLE)


def _channels(args: argparse.Namespace) -> int:
    try:
        home = resolve_home(args.home)
        config = load_config(resolve_config_path(home, args.config))
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    healthy = True
    rows: list[str] = []
    for name in sorted(config.channels):
        channel = config.channels[name]
        if not channel.enabled:
            rows.append(f"{name}: disabled")
            continue
        if name == "terminal":
            rows.append(f"{name}: enabled (ok)")
            continue
        if name == "desktop":
            available, detail = desktop_availability()
            rows.append(
                f"{name}: enabled ({'ok' if available else 'unavailable: ' + detail})"
            )
            healthy = healthy and available
            continue
        if name == "webhook":
            try:
                resolve_ref(channel.url_ref)
                resolve_ref(channel.hmac_key_ref)
            except (SecretError, TypeError) as exc:
                rows.append(f"{name}: enabled (unavailable: {exc})")
                healthy = False
            else:
                rows.append(f"{name}: enabled (references resolve)")
            continue
        rows.append(f"{name}: enabled")

    print("\n".join(rows) if rows else "no channels configured")
    return int(ExitCode.APPROVED if healthy else ExitCode.UNAVAILABLE)


def _version(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "name": "agentinbox",
                    "version": __version__,
                    "python": sys.version.split()[0],
                    "platform": sys.platform,
                }
            )
        )
    else:
        print(f"{PROG} {__version__}")
    return int(ExitCode.APPROVED)


HANDLERS: dict[str, Handler] = {
    "version": _version,
    "init": _init,
    "doctor": _doctor,
    "answer": _answer,
    "inbox": _inbox,
    "ask": _ask,
    "serve": _serve,
    "gate": _gate,
    "channels": _channels,
    "verify-log": _verify_log,
    "export": _export,
    "conformance": _conformance,
    "report": _report,
}


def build_parser() -> argparse.ArgumentParser:
    parser = CliParser(
        prog=PROG,
        description=(
            "Local-first ask gate: route agent asks to humans, record the authenticated "
            "answer, and deny by default on timeout."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="print the version and exit",
    )
    parser.add_argument(
        "--config", metavar="PATH", help="config file (default: <home>/config.toml)"
    )
    parser.add_argument("--home", metavar="PATH", help="home directory override")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-color", action="store_true", help="disable color output")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    for command, help_text in COMMAND_HELP.items():
        sub = subparsers.add_parser(command, help=help_text, description=help_text)
        sub.set_defaults(handler=HANDLERS[command])
        if command == "init":
            sub.add_argument(
                "--force", action="store_true", help="overwrite an existing config file"
            )
        if command == "doctor":
            sub.add_argument(
                "--explain", action="store_true", help="print the effective configuration"
            )
            operation = sub.add_mutually_exclusive_group()
            operation.add_argument(
                "--backup", metavar="PATH", help="write a WAL-safe backup archive"
            )
            operation.add_argument(
                "--restore", metavar="PATH", help="restore a backup into this fresh home"
            )
            sub.add_argument(
                "--force", action="store_true", help="replace a non-empty home on --restore"
            )
        if command == "answer":
            sub.add_argument("ask_id")
            choice = sub.add_mutually_exclusive_group()
            choice.add_argument("--approve", action="store_true")
            choice.add_argument("--deny", action="store_true")
            sub.add_argument("--reason")
            sub.add_argument("--as", dest="as_name", metavar="NAME")
            sub.add_argument(
                "--alternative", metavar="ID", help="allow a producer-declared alternative"
            )
            sub.add_argument(
                "--edit",
                action="append",
                default=[],
                metavar="KEY=VALUE",
                help="edit an argument field allowed by the class (repeatable)",
            )
        if command == "ask":
            source = sub.add_mutually_exclusive_group(required=True)
            source.add_argument("--file", metavar="PATH", help="an ask/1.0 JSON file")
            source.add_argument(
                "--exec", dest="exec_command", metavar="COMMAND", help="gate this command"
            )
            sub.add_argument("--class", dest="ask_class", default="irreversible")
            sub.add_argument("--environment", default="local")
            sub.add_argument("--agent-id", default=None)
            sub.add_argument("--requested-by", default=None)
            sub.add_argument("--session-id", default=None)
            sub.add_argument("--ttl", type=int, default=None)
            sub.add_argument("--timeout", type=float, default=None)
        if command == "serve":
            sub.add_argument(
                "--once", action="store_true", help="drain the bus once and exit (tests/cron)"
            )
            sub.add_argument(
                "--install",
                action="store_true",
                help="write a user-scoped launchd/systemd unit and exit",
            )
            sub.add_argument(
                "--api-port",
                type=int,
                default=8377,
                help="loopback API port (default 8377)",
            )
            sub.add_argument(
                "--no-api", action="store_true", help="do not start the loopback API"
            )
        if command == "export":
            scope = sub.add_mutually_exclusive_group(required=True)
            scope.add_argument("--session", metavar="SESSION_ID")
            scope.add_argument("--ask", metavar="ASK_ID")
            sub.add_argument(
                "--format", choices=("jsonl", "csv"), default="jsonl"
            )
            sub.add_argument("--out", metavar="PATH", help="absolute output path")
            sub.add_argument(
                "--packet",
                action="store_true",
                help="emit a self-contained decision packet for --ask",
            )
        if command == "gate":
            sub.add_argument("--ask", required=True, metavar="ASK_ID")
            sub.add_argument("--wait", action="store_true", help="block until resolved")
            sub.add_argument(
                "--timeout",
                type=float,
                default=None,
                metavar="SECONDS",
                help="CI wait budget (independent of the ask TTL)",
            )
        if command == "report":
            sub.add_argument(
                "--json", action="store_true", help="machine-readable metrics (local only)"
            )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit as exc:  # --help / --version
        code = exc.code
        return code if isinstance(code, int) else 1

    if args.command is None:
        parser.print_usage(sys.stderr)
        if extra:
            print(f"{PROG}: error: unrecognized arguments: {' '.join(extra)}", file=sys.stderr)
        else:
            print(f"{PROG}: error: the following arguments are required: COMMAND", file=sys.stderr)
        return int(ExitCode.USAGE)

    # A stub accepts the flags of the command it will become (and refuses); a real command
    # rejects anything it does not define.
    if extra and args.command in {
        "version",
        "init",
        "doctor",
        "answer",
        "inbox",
        "serve",
        "ask",
        "gate",
        "channels",
        "export",
        "verify-log",
        "conformance",
        "report",
    }:
        parser.print_usage(sys.stderr)
        print(f"{PROG}: error: unrecognized arguments: {' '.join(extra)}", file=sys.stderr)
        return int(ExitCode.USAGE)

    handler: Handler = args.handler
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
