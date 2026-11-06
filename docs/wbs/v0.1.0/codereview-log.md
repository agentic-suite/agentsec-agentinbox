# WBS v0.1.0 — Code review log

Findings per milestone, per the standard `.CR` gate. Every finding is resolved (or explicitly waived with a
reason) before a milestone closes.

| Date | Milestone | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-06 | M0 | 0.2 | argparse's default usage-error exit is `2`, which the decision contract reserves for **denied** — a mistyped flag would have looked like a human denial to CI | High | `CliParser.error()` overridden to exit `1`; test asserts usage errors never emit `2` |
| 2026-11-06 | M0 | 0.2 | `nargs=REMAINDER` on stubs made `agentinbox ask --file x` a usage error instead of an honest refusal (and misparsed flags after the first positional) | Medium | Stub detection now uses `parse_known_args`; stubs accept foreign flags and still exit `4`; real commands reject unknown flags |
| 2026-11-06 | M0 | 0.4 | Design §5.1 called a non-loopback bind a config error while PRD 13 N-18 promises a loud config **plus** a `doctor` warning — the two could not both be true | Medium | v0.1.0 rejects non-loopback binds (the web UI does not exist); the loud-config/warning path lands with the web UI in v0.1.x. Design doc reconciled with N-18 |
| 2026-11-06 | M0 | 0.4 | `_reject_unknown` reported "unknown key" for secret-looking keys before the secret-specific error, hiding the actual fix (`token = "…"` → "unknown key") | Low | Secret check evaluated first; message now says secrets must be `*_ref` references |
| 2026-11-06 | M0 | 0.4 | Dead `_CHANNELS` constant (superseded by `_CHANNEL_KEYS`) failed `mypy --strict` | Low | Removed |
| 2026-11-06 | M0 | 0.T/0.C | Coverage gate caught **89.63%** — config/doctor error branches and CLI usage paths were untested | Medium | Added `tests/config/test_load_edges.py` and `tests/cli/test_doctor_edges.py`; coverage now 100% |
| 2026-11-06 | M0 | 0.1 | Console-script test relied on `PATH`, so it failed under `python -m pytest` even though the script was installed | Low | Test resolves the script next to `sys.executable`; no environment assumption |
| 2026-11-06 | M0 | 0.5 | CI workflow was an org placeholder that ran no gates — the "CI green" acceptance was unfalsifiable | High | Replaced with ruff + mypy + pytest/coverage (3.11–3.13) + `pip check` + install-smoke; workflow contents pinned by tests |
| 2026-11-06 | M1 | 1.2 | ISO timestamps were emitted with variable-length fractional seconds, so lexicographic `expires_at` comparisons in SQL could order times incorrectly (`.5Z` sorts before `Z`) | High | `to_iso` now always emits microseconds (`...00.000000Z`); pending ordering and claim-expiry tests pin it |
| 2026-11-06 | M1 | 1.4 | The conformance chain check assumed appended seqs start at 1, but `created` legitimately occupies seq 1 — a correct driver failed | Medium | Check now asserts a contiguous range from the first returned seq and verifies linkage pairwise; a broken driver still fails |
| 2026-11-06 | M1 | 1.4 | Claim expiry boundary was ambiguous in tests (consume exactly at `expires_at`) | Medium | Semantics fixed and documented: a claim is unusable at `expires_at` (`expires_at > at`); SQLite and memory agree |
| 2026-11-06 | M1 | 1.6 | `export_session` builds `IN (...)` clauses by interpolation — an easy place to introduce real injection later | Low | Placeholders are generated `?` only and ids stay bound parameters; annotated at the site, review keeps it that way |
| 2026-11-06 | M1 | 1.1 | Status enum written as `(str, Enum)` when `StrEnum` is the 3.11 idiom (N-20 floor) | Low | Switched to `StrEnum` |
