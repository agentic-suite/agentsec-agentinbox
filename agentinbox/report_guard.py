"""Guard the hand-maintained field-test report against automated overwrite.

The canonical field-test report (``docs/field-test/<version>/FIELD_TEST_REPORT.md``)
is a hand-maintained journal. A lossy automated rewrite has destroyed its notes
before, so automation must never write it. Any tool that would write a report
must ask this module first and must stop when it refuses.

There is deliberately **no force flag** in agentinbox: the canonical report is
edited by hand, period.

Usage::

    from agentinbox.report_guard import refuse_overwrite

    if refuse_overwrite(path):
        ...  # do NOT write; tell the operator to edit by hand
"""

from __future__ import annotations

from pathlib import Path

#: Marker carried by a hand-maintained report (anywhere in the file).
HAND_MAINTAINED_MARKER = "HAND-MAINTAINED"


def is_hand_maintained(path: str | Path) -> bool:
    """Whether *path* exists and carries the hand-maintained marker."""
    try:
        file = Path(path).expanduser()
        return file.is_file() and HAND_MAINTAINED_MARKER in file.read_text(encoding="utf-8")
    except OSError:
        return False


def refuse_overwrite(path: str | Path) -> bool:
    """Whether a write to *path* must be REFUSED.

    Always true for a hand-maintained report. There is no force exception: the
    canonical report is hand-edited; automation writes a sibling draft instead.
    """
    return is_hand_maintained(path)


__all__ = ["HAND_MAINTAINED_MARKER", "is_hand_maintained", "refuse_overwrite"]
