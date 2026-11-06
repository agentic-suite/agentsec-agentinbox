"""Module entry point: ``python -m agentinbox`` behaves exactly like the console script."""

from __future__ import annotations

import sys

from agentinbox.cli import main

if __name__ == "__main__":
    sys.exit(main())
