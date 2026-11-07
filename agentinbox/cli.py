"""Command-line entry point and the frozen v0.1.0 command surface.

Design of record: ``docs/design/v0.1.0/foundation.md`` §2-§3. Two rules are load-bearing:

* an unimplemented command **refuses** with exit ``4`` (unavailable/fail-closed) and a one-line
  message — it never exits ``0``, because ``0`` means "approved";
* usage mistakes exit ``1``, not argparse's default ``2`` — ``2`` is the *denied* decision and
  must never be produced by the CLI's own parse errors.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections.abc import Callable, Sequence
from typing import NoReturn

from agentinbox import __version__
from agentinbox.answers import AnswerVerifier
from agentinbox.bus import BusError, DeliveryWiring, Job, load_bus
from agentinbox.channels.base import ChannelError
from agentinbox.channels.desktop import DesktopChannel
from agentinbox.channels.terminal import TerminalChannel
from agentinbox.config import (
    Config,
    ConfigError,
    init_home,
    load_config,
    resolve_config_path,
    resolve_home,
)
from agentinbox.doctor import render_explain, render_human, run_checks
from agentinbox.exit_codes import ExitCode
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStore, StoreError, parse_iso, utcnow
from agentinbox.store.loader import load_store

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
}

Handler = Callable[[argparse.Namespace], int]


class CliParser(argparse.ArgumentParser):
    """Usage errors exit ``1`` — never ``2``, which the decision contract reserves for deny."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        print(f"{PROG}: error: {message}", file=sys.stderr)
        raise SystemExit(1)


def _stub(command: str) -> Handler:
    milestone = COMMAND_MILESTONES[command]

    def handler(_args: argparse.Namespace) -> int:
        print(
            f"{PROG}: {command} is not implemented in v0.1.0 (scheduled: {milestone})",
            file=sys.stderr,
        )
        return int(ExitCode.UNAVAILABLE)

    return handler


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


def _serve(args: argparse.Namespace) -> int:
    try:
        config, store = _runtime(args)
        home = resolve_home(args.home)
        bus = load_bus(config, home=home)
    except (ConfigError, StoreError, BusError) as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return int(ExitCode.UNAVAILABLE)

    desktop_config = config.channels.get("desktop")
    desktop = (
        DesktopChannel(config=config)
        if desktop_config is not None and desktop_config.enabled
        else None
    )
    channels: list[object] = [desktop] if desktop is not None else []

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

    wiring = DeliveryWiring(store, channels, on_digest=on_digest)
    scheduler = Scheduler(store)
    try:
        if args.once:
            scheduler.tick()
            bus.consume(wiring.handle)
            return int(ExitCode.APPROVED)

        stop = threading.Event()
        thread, scheduler_stop = scheduler.start()
        try:
            bus.run(wiring.handle, stop)
        except KeyboardInterrupt:
            pass
        finally:
            scheduler_stop.set()
            thread.join(timeout=2)
        return int(ExitCode.APPROVED)
    finally:
        bus.close()
        store.close()


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
        handler: Handler
        if command == "version":
            handler = _version
        elif command == "init":
            handler = _init
        elif command == "doctor":
            handler = _doctor
        elif command == "answer":
            handler = _answer
        elif command == "inbox":
            handler = _inbox
        elif command == "serve":
            handler = _serve
        else:
            handler = _stub(command)
        sub.set_defaults(handler=handler)
        if command == "init":
            sub.add_argument(
                "--force", action="store_true", help="overwrite an existing config file"
            )
        if command == "doctor":
            sub.add_argument(
                "--explain", action="store_true", help="print the effective configuration"
            )
        if command == "answer":
            sub.add_argument("ask_id")
            choice = sub.add_mutually_exclusive_group()
            choice.add_argument("--approve", action="store_true")
            choice.add_argument("--deny", action="store_true")
            sub.add_argument("--reason")
            sub.add_argument("--as", dest="as_name", metavar="NAME")
        if command == "serve":
            sub.add_argument(
                "--once", action="store_true", help="drain the bus once and exit (tests/cron)"
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
    if extra and args.command in {"version", "init", "doctor", "answer", "inbox", "serve"}:
        parser.print_usage(sys.stderr)
        print(f"{PROG}: error: unrecognized arguments: {' '.join(extra)}", file=sys.stderr)
        return int(ExitCode.USAGE)

    handler: Handler = args.handler
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
