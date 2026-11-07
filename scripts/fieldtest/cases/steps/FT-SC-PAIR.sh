#!/usr/bin/env bash
# Hand-written field step (not generated): SC-13 + SC-14 must pass TOGETHER.
# PRD 17: "P iff SC-13 and SC-14 pass together — the discriminator is
# behavior, not volume." The pair case enforces the paired verdict on top of
# the per-case suites: both siblings must be `pass` in THIS run directory.
ft_sut_pytest "FT-SC-PAIR flood suites" \
  tests/flood/test_buckets.py tests/flood/test_headroom.py tests/flood/test_deny_digest.py
ft_assert "flood-pair-together" "$FT_PY" - <<'PY'
import json, os
base = os.environ["FT_RUN_DIR"]
statuses = []
for cid in ("FT-SC-13", "FT-SC-14"):
    path = f"{base}/cases/{cid}/verdict.json"
    with open(path, encoding="utf-8") as handle:
        statuses.append(json.load(handle)["status"])
assert statuses == ["pass", "pass"], f"pair broken: {statuses}"
print("PAIR-OK")
PY
ft_finalize