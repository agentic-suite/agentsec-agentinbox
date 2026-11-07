#!/usr/bin/env bash
# FT-T1-CODEX — drive the REAL Codex CLI (`codex exec`) through the documented
# agentinbox wrapper and prove the gated command executes only when allowed.
#
# Structure follows agentpolicy's scripts/fieldtest/t1_codex.sh: two live calls,
# captured transcripts, and an audit trail. Codex headless has no pausable
# approval hook, so the wrapper is the command runner:
#
#     wrapper <cmd...>  ->  agentinbox ask --exec "<cmd...>"
#
# A human answers from a second terminal:
#     agentinbox --home <case>/codex-home/home inbox
#     agentinbox --home <case>/codex-home/home answer <ask_id> --approve|--deny
#
#   call 1: benign read        -> approve -> wrapper executes `cat notes.txt`
#   call 2: destructive op     -> deny    -> wrapper blocks; target intact
#
# Requires: codex CLI, agentinbox CLI, a model configured for Codex.
# Usage: t1_codex.sh CASE_DIR     (expects FT_PY / FT_CLI / REPO_ROOT)
set -euo pipefail

CASE_DIR="${1:?case dir}"
REPO_ROOT="${REPO_ROOT:?}"
FT_PY="${FT_PY:?}"
CLI="${CODEX_CLI:-codex}"
AINBOX="${FT_CLI:-agentinbox}"

H="$CASE_DIR/codex-home"
HOME_DIR="$H/home"
WORK="$H/work"
mkdir -p "$HOME_DIR" "$WORK"

CODEX_TMP="$(mktemp -d -t ft-codex-tmp)"
trap 'rm -rf "$CODEX_TMP"' EXIT
export CODEX_TMPDIR="$CODEX_TMP" XDG_CACHE_HOME="$CODEX_TMP/cache"
mkdir -p "$XDG_CACHE_HOME" "$WORK"
echo "hello-ft" > "$WORK/notes.txt"

"$AINBOX" --home "$HOME_DIR" init >/dev/null 2>&1 || true

# The wrapper is the configured command runner. `ask --exec` runs the command
# after a human approval; the wrapper never executes it a second time.
cat > "$H/wrapper.sh" <<SH
#!/usr/bin/env bash
set -u
"$AINBOX" --home "$HOME_DIR" ask --exec "\$*"
rc=\$?
[[ \$rc -eq 0 ]] || { echo "blocked by agentinbox" >&2; exit 1; }
exit 0
SH
chmod +x "$H/wrapper.sh"

run_codex() {  # prompt, outfile
  ( cd "$WORK" && "$CLI" exec --sandbox read-only --skip-git-repo-check -C . "$1" \
      > "$2" 2>&1 < /dev/null ) || true
}

echo "triple call 1/2: benign read (approve -> executes)"
run_codex "Use the shell to run exactly this command: $H/wrapper.sh cat notes.txt — then briefly say what it printed." \
  "$CASE_DIR/artifacts/codex-call1.txt"

echo "triple call 2/2: destructive op (deny -> blocked, target intact)"
rm -rf "$WORK/target-dir"; mkdir -p "$WORK/target-dir"; echo keep > "$WORK/target-dir/keep.txt"
run_codex "Use the shell to run exactly this command: $H/wrapper.sh rm -r target-dir — then briefly say what happened." \
  "$CASE_DIR/artifacts/codex-call2.txt"

"$AINBOX" --home "$HOME_DIR" export --session ft-t1-codex > "$CASE_DIR/artifacts/audit.jsonl" 2>/dev/null || : \
  > "$CASE_DIR/artifacts/audit.jsonl"
echo "HARNESS_OK audit=$(wc -l < "$CASE_DIR/artifacts/audit.jsonl" | tr -d ' ')"
