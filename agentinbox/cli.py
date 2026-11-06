"""Command-line entry point.

M0 item 0.1 installs only the entry-point plumbing (``--version`` / ``--help``); item 0.2
adds the full command surface.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from agentinbox import __version__

PROG = "agentinbox"


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--version":
        print(f"{PROG} {__version__}")
        return 0
    print(f"{PROG} {__version__}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
