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
#   REASON  the deny reason (passed on the command line; no prompt needed)
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
  # Keys are ONLY the lines the channel will actually read. --approve/--deny
  # are passed on the command line, so the choice prompt never runs: an
  # approve sends only the typed-confirmation line, a deny (with --reason)
  # sends nothing, and 'q' sends the quit line.
  approve) KEYS="${CONFIRM:-}" ;;
  deny)    KEYS="" ;;
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

# All planned keystrokes up-front: on a tty the channel consumes them in
# prompt order (choice, then typed confirmation if the class requires it).
# No prompt matching: the child reads line-by-line; extra/early input is
# buffered by the tty and consumed by the next prompt (or ignored).
KEYS="$KEYS"
[[ -n "$CONFIRM" ]] && KEYS="$KEYS
$CONFIRM"
export FT_ANSWER_KEYS="$KEYS"

# macOS ships no coreutils `timeout`; run the pty driver in the background of
# a subshell and kill it on deadline. The driver is the only hang guard.
(
  "$FT_PY" - "$FT_CLI" --home "$HOME_DIR" "$@" <<'PY'
"""Drive one interactive `agentinbox answer` under a pty.

Writes the pre-registered keystrokes (FT_ANSWER_KEYS) up-front — a tty
line-discipline buffers them for the prompts in order — then relays output
until the CLI exits. Exits with the CLI's exit code; the outer `timeout`
is the only hang guard.
"""
import os
import pty
import select
import sys
import time

cmd = [sys.argv[1]] + sys.argv[2:]
keys = os.environ.get("FT_ANSWER_KEYS", "").encode() + b"\n"

pid, fd = pty.fork()
if pid == 0:  # child: run the CLI on a tty
    os.execvp(cmd[0], cmd)  # noqa: S606 - fixed argv, pty child

# Feed the plan once the process has started; the tty buffers it for the
# prompts. Short delay so the CLI is up and reading before the bytes land.
time.sleep(0.5)
try:
    os.write(fd, keys)
except OSError:
    pass

buf = b""
deadline = time.time() + 180
while time.time() < deadline:
    ready, _, _ = select.select([fd], [], [], 0.5)
    if fd in ready:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            chunk = b""
        if not chunk:
            break  # EOF: the CLI exited — reap it below
        buf += chunk
        continue
    done, waited = os.waitpid(pid, os.WNOHANG)
    if done == pid:
        # drain whatever is left, then report the exit code
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
        sys.stdout.write(buf.decode("utf-8", "replace"))
        sys.exit(waited >> 8 if waited & 0xFF00 else 1)

# EOF path: the child exited while data was still readable — reap it and use
# its real exit code instead of misreporting a timeout.
try:
    _, waited = os.waitpid(pid, 0)
    sys.stdout.write(buf.decode("utf-8", "replace"))
    sys.exit(waited >> 8 if waited & 0xFF00 else 1)
except ChildProcessError:
    pass

sys.stdout.write(buf.decode("utf-8", "replace"))
print("t1_answer: timed out", file=sys.stderr)
try:
    os.kill(pid, 9)
    os.waitpid(pid, 0)
except ProcessLookupError:
    pass
sys.exit(1)
PY
) &
driver=$!
(
  sleep "${FT_ANSWER_TIMEOUT:-60}"
  kill "$driver" 2>/dev/null || true
  kill "$driver" 2>/dev/null || true
) &
watchdog=$!
wait "$driver"
rc=$?
kill "$watchdog" 2>/dev/null || true
exit "$rc"