"""Log-safe text (M22 item 22.5): control characters and ANSI cannot forge a log line.

The product never logs raw untrusted text, but error messages can carry a caller-supplied value
(a command name, a path). This helper keeps one message on one line and strips terminal control
sequences before it reaches stderr or a log file.
"""

from __future__ import annotations

import re

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
DEFAULT_LIMIT = 500


def sanitize_log_line(value: object, *, limit: int = DEFAULT_LIMIT) -> str:
    """Return a single-line, control-free, length-capped rendering of ``value``."""
    text = _ANSI.sub("", str(value))
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = _CONTROL.sub("", text)
    return text[:limit]


__all__ = ["DEFAULT_LIMIT", "sanitize_log_line"]
