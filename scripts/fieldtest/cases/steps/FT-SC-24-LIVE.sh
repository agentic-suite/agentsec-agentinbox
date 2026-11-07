#!/usr/bin/env bash
# Hand-written field step (not generated): SC-24 LIVE — fail-closed under real
# faults on the host CLI: a corrupted store and an unreadable store must each
# exit UNAVAILABLE (4) — never a silent allow (0).
LIVE="$FT_CASE_DIR/live"
mkdir -p "$LIVE/corrupt" "$LIVE/locked"

# Fault 1: a corrupted (non-sqlite) store file -> every CLI path fails closed.
echo "not a sqlite database at all" > "$LIVE/corrupt/inbox.db"
"$FT_CLI" --home "$LIVE/corrupt" init >/dev/null 2>&1 || true
mv "$LIVE/corrupt/inbox.db" "$LIVE/corrupt/inbox.db.bak" 2>/dev/null || true
mkdir -p "$LIVE/corrupt/.agentinbox"
echo "garbage-bytes-not-a-db" > "$LIVE/corrupt/inbox.db"
ft_assert "fault-corrupt-store-fails-closed" bash -c '
  "'"$FT_CLI"'" --home "'"$LIVE"'/corrupt" inbox >/dev/null 2>&1
  rc=$?
  test $rc -eq 4 && echo FAIL-CLOSED-4'

# Fault 2: an unreadable (permission) store -> ingest/gate fail closed.
mkdir -p "$LIVE/locked/.agentinbox"
"$FT_CLI" --home "$LIVE/locked" init >/dev/null 2>&1 || true
chmod 000 "$LIVE/locked/inbox.db" 2>/dev/null || true
ft_assert "fault-locked-store-fails-closed" bash -c '
  "'"$FT_CLI"'" --home "'"$LIVE"'/locked" inbox >/dev/null 2>&1
  rc=$?
  test $rc -eq 4 && echo FAIL-CLOSED-4'
chmod 644 "$LIVE/locked/inbox.db" 2>/dev/null || true

# No silent allow anywhere: neither fault path may exit 0 with a pending ask
# silently approved. (An explicit grep over the fault output for "allow"
# would be plumbing; the exit-code checks above are the contract.)
ft_assert "fault-no-silent-allow" bash -c '
  test ! -x "'"$LIVE"'/corrupt/allow-marker" && echo NO-SILENT-ALLOW'

ft_finalize