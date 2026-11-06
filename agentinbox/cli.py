"""Command-line entry point and the frozen v0.1.0 command surface.

Design of record: ``docs/design/v0.1.0/foundation.md`` §2–§3. Two rules are load-bearing:

* an unimplemented command **refuses** with exit ``4`` (unavailable/fail-closed) and a one-line
  message — it never exits ``0``, because ``0`` means "approved";
* usage mistakes exit ``1``, not argparse's default ``2`` — ``2`` is the *denied* decision and
  must never be produced by the CLI's own parse errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from typing import NoReturn

from agentinbox import __version__
from agentinbox.exit_codes import ExitCode

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
    parser.add_argument("--config", metavar="PATH", help="config file (default: <home>/config.toml)")
    parser.add_argument("--home", metavar="PATH", help="home directory override")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-color", action="store_true", help="disable color output")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    for command, help_text in COMMAND_HELP.items():
        sub = subparsers.add_parser(command, help=help_text, description=help_text)
        sub.set_defaults(
            handler=_version if command == "version" else _stub(command),
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
    if extra and args.command == "version":
        parser.print_usage(sys.stderr)
        print(f"{PROG}: error: unrecognized arguments: {' '.join(extra)}", file=sys.stderr)
        return int(ExitCode.USAGE)

    handler: Handler = args.handler
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
