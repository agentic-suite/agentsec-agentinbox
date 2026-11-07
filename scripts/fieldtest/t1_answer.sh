#!/usr/bin/env bash
# Answer ONE pending ask through a real terminal session (pty).
#
# The product contract is unchanged: non-interactive scripts can never approve
# (TerminalChannel returns PENDING without a tty). The field-test answerer
# therefore drives a genuine interactive session under a pty and feeds the
# pre-registered keystrokes. This is recorded in the journal as automation with
# a pre-registered answer plan — never as a human decision.
#
# Usage: t1_answer.sh HOME ASK_ID ACTION [CONFIRM] [REASON]
#   ACTION  approve | deny | q
#   CONFIRM the typed confirmation for an irreversible approve (the action name)
#   REASON  the deny reason (avoids the reason prompt)
set -euo pipefail

HOME_DIR="${1:?home}"
ASK_ID="${2:?ask id}"
ACTION="${3:?approve|deny|q}"
CONFIRM="${4:-}"
REASON="${5:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

case "$ACTION" in
  approve) KEYS="a" ;;
  deny)    KEYS="d" ;;
  q)       KEYS="q" ;;
  *) echo "t1_answer: unknown action $ACTION" >&2; exit 2 ;;
esac

if [[ "$ACTION" == "approve" ]]; then
  set -- answer "$ASK_ID" --approve --as alice
elif [[ "$ACTION" == "deny" ]]; then
  set -- answer "$ASK_ID" --deny --reason "${REASON:-field-test plan}" --as alice
else
  set -- answer "$ASK_ID" --as alice
fi

export FT_ANSWER_KEYS="$KEYS" FT_ANSWER_CONFIRM="$CONFIRM"
"$FT_PY" - "$FT_CLI" --home "$HOME_DIR" "$@" <<'PY'
"""Drive one interactive `agentinbox answer` under a pty.

Reads the answer plan from FT_ANSWER_KEYS ("a" | "d" | "q"), waits for each
prompt, and feeds the pre-registered line. The typed confirmation
(FT_ANSWER_CONFIRM) is sent only when the channel's confirmation prompt
appears; the deny reason is passed on the command line. Exits with the CLI's
exit code.
"""
import os
import pty
import re
import select
import sys
import time

cmd = [sys.argv[1]] + sys.argv[2:]
keys = os.environ.get("FT_ANSWER_KEYS", "").encode()
confirm = os.environ.get("FT_ANSWER_CONFIRM", "").encode()

pid, fd = pty.fork()
if pid == 0:  # child: run the CLI on a tty
    os.execvp(cmd[0], cmd)  # noqa: S606 - fixed argv, pty child

buf = b""
sent_choice = sent_confirm = False
deadline = time.time() + 120
status = 1

PROMPT_CHOICE = re.compile(rb"\[a\]pprove / \[d\]eny", re.I)
PROMPT_CONFIRM = re.compile(rb"type the action name to confirm", re.I)

while time.time() < deadline:
    ready, _, _ = select.select([fd], [], [], 0.5)
    if fd in ready:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            chunk = b""
        if not chunk:
            break
        buf += chunk
    # Feed each pre-registered keystroke only when its prompt has rendered.
    if not sent_choice and keys and PROMPT_CHOICE.search(buf):
        time.sleep(0.3)
        os.write(fd, keys + b"\n")
        sent_choice = True
        buf = b""
        continue
    if sent_choice and not sent_confirm and confirm and PROMPT_CONFIRM.search(buf):
        time.sleep(0.3)
        os.write(fd, confirm + b"\n")
        sent_confirm = True
        buf = b""
        continue
    done, waited = os.waitpid(pid, os.WNOHANG)
    if done == pid:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if fd not in ready:
                break
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
        status = waited >> 8  # POSIX exit code; signals are recorded as 128+n+256
        break

sys.stdout.write(buf.decode("utf-8", "replace"))
sys.exit(status)
PY