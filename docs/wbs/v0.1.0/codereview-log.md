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
| 2026-11-06 | M2 | 2.2 | Caps were enforced after identity verification in the first draft — a hostile oversized payload could force hashing/redaction work before the 413 | High | Order is now validate → **cap** → identity → expiry → redact; a 300 KB body is rejected before any regex pass |
| 2026-11-06 | M2 | 2.4 | The connection-string pattern initially replaced only the password, leaving the DSN shape and host — inconsistent with "raw values never persisted" | Medium | The whole credential-bearing match is replaced; tests assert the password is absent from the stored payload |
| 2026-11-06 | M2 | 2.5 | A producer could have smuggled `_trust` in the body and had it preserved as an "unknown field" | High | Reserved metadata keys are dropped from `extra` and the server always writes its own `_trust`/`_redactions`/`_producer` |
| 2026-11-06 | M2 | 2.6 | Rejecting an oversized body by Content-Length without draining it reset the connection, hiding the 413 | Medium | The declared body is drained before the 413; the API test asserts the status |
| 2026-11-06 | M2 | 2.6 | Peer **uid** is not exposed on loopback TCP; recording a "uid" would have been a lie | Medium | The API records the remote address and documents the gap; Unix-socket credentials are the upgrade path (T13) |
| 2026-11-06 | M2 | 2.1 | Model/schema could drift silently (hand-maintained JSON) | Medium | A test asserts the required set and `additionalProperties` match the model; schema remains the shipped truth |
| 2026-11-06 | M3 | 3.1 | The interface grew (`transitions_for`, `record_delivery`, `list_deliveries`) but the conformance version stayed `1`, so a driver could have been admitted without the new methods | High | Conformance version bumped to `2`; both built-ins declare the constant, and third-party drivers must re-run the suite |
| 2026-11-06 | M3 | 3.5 | The first resolve draft wrote `expired` on read — a read path mutating the store would race the scheduler and make "derived on read" meaningless | High | Reads never write; a derived expiry is returned as deny and M4 records it via CAS exactly once. A test asserts the stored status is still `pending` after an overdue read |
| 2026-11-06 | M3 | 3.3 | Recording `illegal-transition-rejected` after raising would lose evidence for the most interesting attempts | Medium | The observation is appended first, then `IllegalTransition` is raised; tests assert the evidence row exists |
| 2026-11-06 | M3 | 3.5 | `cancelled` has no fixed reason code in PRD 02; inventing one would silently fork the vocabulary | Low | Mapped to `deny_ask_denied` with an explicit "cancelled by the producer" explanation; flagged for the PRD vocabulary rather than patched ad hoc |
| 2026-11-06 | M3 | 3.5 | `ResolveResult.to_dict` emitted both `answer_by` and `answered_by` | Low | Removed the typo field; the shape test pins the contract |
| 2026-11-06 | M4 | 4.1 | Expiry initially called `lifecycle.transition()`, which records `illegal-transition-rejected` when two schedulers race a benign double-expire — noise in the evidence log | Medium | Expiry now uses the store CAS directly (the edge is known-legal); a lost race writes nothing. Warnings still use `observe()` and swallow the benign race |
| 2026-11-06 | M4 | 4.3 | A recovery marker appended **after** expiry would be rejected (terminal states only allow `late-answer`) | Medium | The marker is appended before firing, carrying the planned outcomes; tests assert marker + exactly one expiry |
| 2026-11-06 | M4 | 4.4 | Scheduling against raw `now()` lets a backwards clock jump postpone a deadline indefinitely | High | `effective_now()` uses `max(now, last_seen)`; a jump back after the deadline still fires, and a jump back before it cannot undo a seen instant |
| 2026-11-06 | M4 | 4.4 | "doctor warns on skew" compared `time.time()` to `datetime.now()` — the same source, so it could never detect skew | Medium | The check compares the newest **persisted audit** timestamp to the wall clock; evidence ahead by >300 s warns |
| 2026-11-06 | M4 | 4.5 | A warning for an ask that expired during downtime would be meaningless noise | Low | Expired asks only fire expiry; the missed-warning path applies to asks that are still pending, and is tested |
| 2026-11-06 | M5 | 5.3 | The untrusted label was applied twice (in the text helper and again by the renderer) | Low | Labelled once at render; untrusted `unknown` values are not mislabelled as tool output |
| 2026-11-06 | M5 | 5.2 | A missing reversibility on an irreversible class initially rendered plain `unknown`, hiding the class context | Medium | Renders `unknown (irreversible class)` — the honest ambiguous label, tested |
| 2026-11-06 | M5 | 5.3 | The first markup-stripping regex was greedy across the card and could eat legitimate text | Medium | Bounded tag pattern (`<[^>]{0,200}>`), and the poisoned corpus pins the inertness rules |
| 2026-11-06 | M5 | 5.5 | Corpora could be edited silently, making SC-23 meaningless | High | sha256-checksummed corpus with a test; counts (12/12/10) are asserted |
| 2026-11-06 | M5 | 5.1 | Per-surface frontends could drift and render different blocks | Medium | One model + renderer; a test asserts all four surfaces share an identical core body |
| 2026-11-06 | M6 | 6.2 | The pipeline checked ask state **before** principal authorization, so an off-roster caller could learn the winner/time of a resolved ask by making a late attempt | Medium | Authorization now precedes the terminal-state check: off-roster callers get `off_roster`; only authorized late answers learn the winner. Test added |
| 2026-11-06 | M6 | 6.5 | Guessing counters live in process memory, so a restart resets the attempt budget | Low | Documented limitation; the deadline still bounds the window, and the M20 fault matrix re-checks it. Durable counters are deferred until server mode |
| 2026-11-06 | M6 | 6.6 | The first raw-API guard was inserted with a stale anchor and silently absent until the test caught the `AttributeError` | Low | Tests caught it before commit; the endpoint now exists solely to refuse and record |
| 2026-11-08 | M7 | 7.3 | CLI `_runtime` returned `tuple[object, object]`, so mypy could not see missing attributes on the config/store; strict mode caught real `.get`/`.list_pending` errors | Medium | Typed as `tuple[Config, AskStore]`; removed the stale `type: ignore` comments |
| 2026-11-08 | M7 | 7.T | Coverage was 94.77% at the gate — the CLI error branches and terminal edge paths were untested | Medium | Added tests for bad config, `ChannelError`, empty inbox, missing principal, unexpected decision, and the help/unrecognized loop; coverage now 95.61% |
| 2026-11-08 | M7 | 7.3 | Non-interactive `answer` returns before minting a claim or authenticating — verified that a piped/scripted invocation cannot approve | Low | Covered by `test_non_interactive_answer_returns_pending_and_never_approves`; documented as the D-5 contract |
| 2026-11-08 | M8 | 8.1/8.3 | The first desktop renderer used the full card body, which would have put ask arguments and tool output on the lock screen | High | The renderer takes only `AskRecord` and emits class, fingerprint, TTL, and tier; a secret-bearing payload test asserts arguments never appear |
| 2026-11-08 | M8 | 8.3 | A notification tap could only be made safe by omitting any answer affordance, but the adapter still had to satisfy the `InboxChannel` protocol | High | `authenticate()` returns `None` unconditionally and no `answer`/`submit` method exists; the shared conformance suite and a direct assertion pin it |
| 2026-11-08 | M8 | 8.5 | The desktop `doctor` check would have failed healthy installs where the channel is disabled (the default) | Medium | Disabled is `ok` (`disabled`); only an enabled-but-unreachable channel is `fail`, with the TTL-unaffected note in the message |
| 2026-11-08 | M8 | 8.1 | Invoking `osascript` through a shell would have made the notification body a command-injection surface | High | Backends use an argv list with `shell=False`, bounded timeout, and JSON-escaped AppleScript strings; tests assert the flags |
| 2026-11-08 | M9 | 9.3 | Publish was check-then-`replace`, so two publishers of the same job id could both enqueue and the second silently overwrote the first | High | Publish now uses `os.link(tmp, target)` as the atomic rename-CAS (fails with `FileExistsError`); `upsert` is the only deliberate overwrite and is reserved for the rolling digest |
| 2026-11-08 | M9 | 9.1 | A digest window that republished a fixed job id kept the **first** count (1) and dropped the aggregate, making the digest lie about the flood size | High | `publish_digest` uses `upsert`; the 200-publish fixture asserts one job whose payload reports 200 |
| 2026-11-08 | M9 | 9.6 | Logging a redelivered job for a resolved ask went through `observe()`, which refuses post-terminal observations — the idempotent no-op would have crashed the daemon | Medium | `delivery-skipped`/`delivery-failed` are evidence-only post-terminal observations; an unknown ask is skipped (nowhere to log) |
| 2026-11-08 | M9 | 9.5 | The daemon could report a stale digest count because the in-proc driver's dedupe dropped the updated payload | Medium | Both drivers implement `upsert`; the spool writes atomically and in-proc replaces the stored job |
| 2026-11-08 | M9 | 9.3 | A partially written job file could become visible if publish wrote in place | High | All writes stage under `tmp/` with `fsync`, then link/rename into `jobs/`; boot sweeps `*.tmp` |
| 2026-11-08 | M10 | 10.1 | The first gate draft expired the ask when the CI `--timeout` lapsed, letting a CI budget rewrite the ask's truth | High | The budget returns `3` without any write; only the ask's own TTL or an authenticated answer changes its state. A test asserts the ask is still pending |
| 2026-11-08 | M10 | 10.3 | Cancelling unconditionally would have rewritten an already-expired ask as `cancelled`, hiding the timeout | High | Cancellation is attempted only while `pending` and before `expires_at`; a lost race reports the real outcome |
| 2026-11-08 | M10 | 10.3 | `signal.signal()` raises in a non-main thread, so embedding `main()` in tests/daemons would have crashed before the gate ran | Medium | Handler installation/restoration is suppressed; cancellation simply degrades to unavailable, never to a wrong exit |
| 2026-11-08 | M10 | 10.2 | Any unexpected store/API exception could have escaped as an internal error (`1`) that CI might treat as a retry | High | The CLI boundary maps any gate failure to `4`; the irreversible step is guarded by non-zero, never `0` |
| 2026-11-08 | M10 | 10.4 | Re-running the gate could have minted a claim or re-notified | Medium | The gate is a pure reader (plus the cancellation edge); a retry idempotency test asserts no deliveries and no new transitions |
| 2026-11-08 | M11 | 11.2 | An escalation implemented as a generic ask update could have written `expires_at` and silently extended the deadline | High | `store.escalate()` updates only `tier`/`escalate_at`; the invariant test asserts `expires_at` is byte-identical after every tier and after exhaustion |
| 2026-11-08 | M11 | 11.3 | Tier change and claim revocation were separate writes in the first draft; a sleeper could answer inside that gap | High | The store performs both in one transaction (`escalate()`), returning `-1` on a lost CAS; a revocation fixture proves the sleeper is rejected |
| 2026-11-08 | M11 | 11.3 | `_allowed_principals` unioned every ladder tier, so a prior-tier principal could still answer the new tier once a channel minted a current-tier claim | High | Authorization is tier-aware: only the current tier's roster for that channel is eligible; the prior-tier-principal test pins `off_roster` |
| 2026-11-08 | M11 | 11.5 | An implicit zero delay would escalate instantly and make the ladder meaningless | High | Omitted delays spread over the TTL; explicit delays must start at 0, strictly increase, and end before the TTL (load-time refusal) |
| 2026-11-08 | M11 | 11.5 | A ladder tier with no roster entry would fail at 3 a.m. rather than at load | Medium | Every tier must resolve to a non-empty roster entry; `doctor --explain` prints the effective ladder and delays |
| 2026-11-08 | M11 | 11.1 | Two schedulers could both escalate the same tier and double-publish `ask-escalated` | Medium | The store CAS requires `pending` + the expected tier; the loser writes nothing and publishes no job |
| 2026-11-08 | M11 | 11.5 | A crash between writing the config event and its digest state could lose the event | Low | The event is appended **before** the state file; a crash re-emits (duplicate) rather than silently dropping a policy change |
| 2026-11-08 | M12 | 12.2 | A bucket keyed only by agent would let one agent launder a flood through new sessions or environments | High | The key is `agent \| session \| environment \| producer-uid`; isolation tests cover each dimension |
| 2026-11-08 | M12 | 12.4 | Appending the `ask-flood` event after the deny transition would have raised (terminal states reject observations) and lost the event | High | The event is appended while the first denied ask is still pending; `record_flood()` returns `created` so exactly one caller appends it |
| 2026-11-08 | M12 | 12.4 | The digest job kept the first denial's count, under-reporting the flood | High | Every denial upserts the rolling digest; the 200-pack fixture asserts one job with count 180 |
| 2026-11-08 | M12 | 12.3 | `resolve` reported flood denials as non-retryable, contradicting the "retry after the window" contract | Medium | Flood denials are `retryable=true` with an explanation naming the window; `retry_after_s` is on the transition |
| 2026-11-08 | M12 | 12.1 | Duplicate retries would consume bucket tokens and could trip the guard through retry storms | High | Coalescing runs first: `created=False` returns before the guard; a 3-retry fixture asserts one ask and one delivery |
| 2026-11-08 | M12 | 12.3 | A flood-denied ask could be answered by a race if denial were not terminal | High | `flood_denied` is terminal; an answer is a late-answer rejection and the `resurrections` counter stays 0 |
| 2026-11-08 | M13 | 13.1 | Sending the M5 card body over the webhook would have leaked tool arguments and blast-radius text to a third party | High | The payload is built from the record with an explicit allow-list; `arguments`/context never appear |
| 2026-11-08 | M13 | 13.1 | A receiver could be given a non-http(s) URL (for example `file:`) and be used to read local data | High | The default sender refuses anything but `http(s)`; the test covers the guard |
| 2026-11-08 | M13 | 13.1 | The HMAC secret could have been logged or persisted while building headers | High | The key is resolved at delivery time and only the hex signature leaves the process; a test asserts the secret is absent from headers |
| 2026-11-08 | M13 | 13.5 | Routability was only checked for ladders, so a class whose roster pointed at a disabled channel loaded and then quietly timed out | High | A roster-bearing config must resolve every class to at least one enabled channel; a class-named load error names the configured channels |
| 2026-11-08 | M13 | 13.4 | A receiver 500 could have blocked ingest if delivery ran inline | High | Ingest only publishes a bus job; retries/failover run in the consumer with bounded backoff and per-attempt records |
| 2026-11-08 | M13 | 13.2 | An interactive receiver button could be mistaken for an answer path | Medium | The adapter has `deliver()` only; `decision` is `null`; recipes explicitly omit actions, and a crafted response has no inbox endpoint |
| 2026-11-08 | M14 | 14.1 | Building the decision record per surface would let the shapes drift and make "same fact" unprovable | High | `agentinbox.parity` builds it once; `comparable_decision()` is the byte-level fixture and only channel/principal are excluded |
| 2026-11-08 | M14 | 14.3 | Late answers told the responder only "ask is already resolved", not who won or when | Medium | The rejection message names the winner and its instant (public information), while credential causes stay uniform |
| 2026-11-08 | M14 | 14.2 | Race losers recorded `late` but the evidence did not carry the winner identity/time | Medium | The `late-answer` observation already carries `winner`/`winner_at`; the race fixture asserts exactly one winner and seven late no-ops |
| 2026-11-08 | M14 | 14.5 | The M7 conformance suite only ran the terminal channel, so a deciding desktop/webhook adapter could have shipped | High | The suite now runs terminal, desktop, webhook, and the CI-wait surface; a deliberately deciding channel fails it |
| 2026-11-08 | M14 | 14.4 | A downed surface could have been re-asked or shown stale state | Medium | Surfaces are read-only views of the store; the failover fixture asserts the outcome appears without a new ask |
| 2026-11-08 | M15 | 15.1 | Deliveries and flood windows were recorded in their own tables but not in the audit chain, so an auditor could not see movement | High | `record_delivery`/`record_flood` now append chained audit entries; conformance asserts both kinds and verifies the chain |
| 2026-11-08 | M15 | 15.3 | An export could lift evidence out of the box without leaving a trace | High | Every export appends an `export` audit entry (scope, format, count) before the caller writes the file |
| 2026-11-08 | M15 | 15.4 | Pruning audit rows would leave `verify-log` unable to link the retained chain | High | Retention prunes **detail** rows and appends a `retention-pruned` marker; the chain stays intact and verifiable. The honest loss of pruned detail is documented |
| 2026-11-08 | M15 | 15.3 | A relative `--out` could write somewhere unexpected; a world-readable export would leak evidence | Medium | `--out` must be absolute and the file is `chmod 0600`; stdout remains the default |
| 2026-11-08 | M15 | 15.5 | A restore/import path would let old evidence become authority again | High | No import command or `import_*` API exists; the export meta records `authority: "none"` and a negative test pins both |
| 2026-11-08 | M16 | 16.1 | Emitting from both the mirrored delivery/flood transitions and their records would double every event | High | The tracer skips the mirror transitions and reads the delivery/flood audit records; a fixture asserts one `ask-delivered` and three `ask-delivery-failed` |
| 2026-11-08 | M16 | 16.1 | The audit chain stored only payload digests, so the event stream could not be projected from evidence | High | Audit schema v4 stores the canonical payload (and `AuditEntry.payload`); the chain still verifies over the digest |
| 2026-11-08 | M16 | 16.1 | Internal rejection causes (`bad_secret`, `identity_mismatch`, …) do not match the published schema vocabulary and could drift | High | A frozen cause map emits the schema vocabulary and preserves the internal cause in `cause_detail` |
| 2026-11-08 | M16 | 16.3 | A downed sink could raise into the daemon or lose events silently | High | `BufferedEventSink` buffers on failure and an overflow writes an `event-gap` marker; decisions never touch the sink |
| 2026-11-08 | M16 | 16.2 | The payload allow-lists are the no-drift guard; an unlisted field could leak untrusted text | High | The fixture's `x-payload-allowed` is enforced by the validator; a marker secret in `arguments` is absent from every event |
| 2026-11-08 | M16 | 16.4 | `traceparent` could be synthesized, breaking honest correlation | Medium | It is carried only when the producer supplied the contract field; otherwise `null` |
| 2026-11-08 | M17 | 17.1 | Reason codes were string literals in `resolve.py`, so the bridge could drift from agentpolicy's registry | High | `agentinbox.reasons` is the frozen registry; `resolve.py` imports it, and a drift test asserts the exact set and state mapping |
| 2026-11-08 | M17 | 17.4 | `GET /v1/asks/{id}` returned raw lifecycle words (`approved`/`denied`) instead of `resolve/1.0` | High | The endpoint now returns the full resolve payload (allow/deny/pending + reason/retry/hint) and 404s with `deny_ask_unknown` |
| 2026-11-08 | M17 | 17.2 | Expiry hints were class-agnostic and echoed nothing about the deny | Medium | `ClassConfig.rescope_hint` plus a class/environment fallback; human deny reasons are echoed |
| 2026-11-08 | M17 | 17.2 | A long configured hint or control characters could smuggle markup/newlines into agent-visible text | High | Hints are control-stripped, capped, reserved space keeps the "not policy" label, and config validation refuses control characters |
| 2026-11-08 | M17 | 17.5 | A resolve call could present any identity and still read a decision for another action | High | The optional `action_identity` is compared to the stored identity; a mismatch returns `deny_action_identity_mismatch` |
| 2026-11-08 | M17 | 17.3 | Flood denials were retryable but carried no retry window | Medium | `retry_after` comes from the `flood-denied` evidence (falling back to the configured window); expiry is never retryable |
| 2026-11-08 | M18 | 18.1 | A producer could claim trusted class/policy fields with only the bearer token | High | Adapter trusted fields require an HMAC over the exact body with `[producers.<name>].key_ref`; unknown/bad signatures are `401` and nothing is stored |
| 2026-11-08 | M18 | 18.2 | `--exec` could have run a denied or expired command | High | The command runs only after `ExitCode.APPROVED`; deny/expiry print the reason and never execute (fixtures assert the marker is absent) |
| 2026-11-08 | M18 | 18.2 | Wrapping the command through a shell would make the payload a second injection surface | High | The command is `shlex.split` and run with `shell=False`; shell features require an explicit `sh -c` |
| 2026-11-08 | M18 | 18.1 | Concurrent store openers raced migrations (`table schema_version already exists`) and WAL switches (`database is locked`) | High | Migrations run inside `BEGIN IMMEDIATE` after re-reading the version; WAL is only switched when needed and retried on lock |
| 2026-11-08 | M18 | 18.2 | `ask` left its SQLite connection open in embedded/threaded use | Medium | `_ask` closes the store in a `finally`, so a long-lived host does not leak connections |
| 2026-11-08 | M18 | 18.3 | The adapter client collapsed every failure into a string, hiding the status/body a producer needs | Medium | `AdapterError` carries `HTTP <code>: <body>` for 4xx/5xx and "inbox unreachable" for transport failures |
| 2026-11-08 | M19 | 19.2 | A resumed graph could re-run an irreversible tool after a crash | High | `ExecutionJournal` claims `executing` **before** the action and `done` after; a replay sees the marker and refuses, so execution is at-most-once |
| 2026-11-08 | M19 | 19.1 | Pending/deny/expiry could be read as approval by a naive `bool(resume)` | High | `decision()` returns `approve` only for `status=allow`; a pending read is explicitly `deny` in the fixture |
| 2026-11-08 | M19 | 19.3 | The conformance kit could write canary asks into the live inbox | High | The kit always uses a fresh `MemoryStore` (injectable factory); the live store is never touched |
| 2026-11-08 | M19 | 19.3 | A broken adapter could crash the kit instead of failing it | Medium | Each check is wrapped; a failure is recorded as a red check with the exception, and the CLI exits `4` |
| 2026-11-08 | M19 | 19.3 | The shipped fixture could drift from the contract | Medium | A test ingests `tests/fixtures/conformance/ask.json` through the real pipeline |
| 2026-11-08 | M19 | 19.1 | A framework adapter could grow answer/claim code | High | The adapter has `create`/`resolve` only; the conformance kit gates `deliver`/`authenticate` and no `decide`/`submit` |
| 2026-11-08 | M20 | 20.3 | A locked/unreadable SQLite file escaped as a raw `sqlite3` exception, so the CLI could crash instead of exiting `4` | High | `SqliteStore` wraps connection/migration failures in `StoreError`; every CLI runtime path maps that to exit `4`, and the API maps it to `503` |
| 2026-11-08 | M20 | 20.4 | The chain check would have failed an old store that predates the audit table, before the migration could run | Medium | A missing `audit` table is `ok` ("migrates on open"); real hash/seq faults still name the seq |
| 2026-11-08 | M20 | 20.4 | An enabled webhook/producer with an unresolvable key looked healthy | High | `keys` resolves every reference and turns red with the named env/file reference |
| 2026-11-08 | M20 | 20.5 | A bad reload could have replaced the effective policy with a broken config | High | `ConfigHolder` keeps the last-good config, returns the error, and the daemon records `inbox-config-changed(failed)` |
| 2026-11-08 | M20 | 20.2 | The matrix could silently skip a fault or allow through a sink/channel path | High | `FAILURE_MATRIX` is complete over `Fault`; tests assert no case allows by itself and the scheduler's zero-allow counter stays `0` |
| 2026-11-08 | M20 | 20.4 | A slow doctor would be ignored in cron | Medium | The healthy path is asserted under two seconds and every check is read-only |

## PRD conformance review (M0–M20, 2026-11-08)

Audit of the built milestones against PRDs 02/05/06/11/13/15/16/18/19/20/22. **Fixed in this pass** (each with a
regression test):

| Area | Finding | Fix |
|---|---|---|
| R5 / T7 | The audit chain re-hashed the stored digest but never the stored **payload body**, so editing a body while leaving the digest intact verified cleanly | New entries store the canonical payload; `verify_audit_chain` re-hashes it (exact seq); legacy v3 rows are `payload: null` and verify by digest only |
| R5 / E9 | A corrupt audit `payload` JSON raised a raw `JSONDecodeError`, crashing `verify-log` | `audit_entries` raises `StoreError` ("payload is corrupt"); `verify-log`/`doctor` fail closed with exit `4` |
| R5 / SC-20 | `export` included only audit rows whose `ref_id` matched the exported ask; interleaved delivery/flood rows broke `prev_hash` linkage, so the export was not offline-verifiable | Export carries the **whole chain in seq order**; a fixture verifies the exported chain offline |
| R1 / T2 / E5 | Trusted-class fields from an unauthenticated producer rendered **without** the promised "unverified" label | Card/desktop now render `[unverified] …` for class, criticality, reason code, rule, policy version, environment, data class, requested by; the webhook payload carries `trust.unverified` |
| R1 | The card lacked the PRD's "prior asks in this session" and "credential class" fields | Added (unknown when absent); terminal/desktop/webhook/CI card builders pass session history |
| R3 | The pre-expiry warning was recorded as a `warned` transition but **never delivered to a channel** | Scheduler publishes one `warn:<ask>` renotify job; the desktop sends a distinct "expiring soon" notification once (card warning flag); other channels re-render |
| R4 | The escalated card said "tier-1 → on-call", not the PRD's "tier 1 did not answer" | Escalation history now reads `tier-1 did not answer → on-call` |
| E6 / I-5 | Delivery errors could persist a channel URL (and its token) in the delivery record/audit | Channel errors are redacted (`CONNECTION_STRING`/secret patterns) before the record/event; the webhook no longer echoes the URL |
| R2 / E12 | CLI `ask` ingested without publishing a delivery job, so no channel was notified; and a producer could not publish while the daemon owned the spool lock | Added a lock-free `SpoolPublisher`; `ask` publishes through it (the daemon keeps the consumer lock) |
| PRD 18 binding | Claims were bound to ask/channel/tier but not to `action_identity` | `ClaimRecord.action_identity` is persisted (schema v5) and checked in the verifier; a forged identity is `identity_mismatch` |
| PRD 02 delivery modes | `serve` never started the loopback ingest API, so remote producers could not POST | `serve` starts the API on 127.0.0.1 (default 8377), writes a `0600` token to `<home>/api-token`, fails closed on a port conflict; `--no-api` opts out |
| R5 / read-only posture | `verify-log` opened the store through the migrating loader, writing an old DB it was only supposed to inspect | `verify-log` uses `read_audit_entries` (read-only sqlite, no migration); a v1 store stays v1 and gains no audit table |
| R5 / event log | The JSONL event sink replayed the whole chain after a restart (duplicate lines) | `EventTracer` persists the last **delivered** sequence in `<home>/logs/events.seq`; a down sink keeps the cursor behind and replays (at-least-once) instead of losing events |
| R1 / T10 | `requested_by` was never a trusted-class field, so a signed adapter's self-review anchor was still unverified | Added to the trusted profile; a signed adapter's value is verified, an unsigned producer's is labelled unverified |
| E3 | PRD 05 said the claim secret is 256-bit while PRD 18 and the implementation use 128-bit | PRD 05 E3 reconciled to **128-bit**; a test pins 32 hex chars (16 bytes) and the hashed-at-rest property |
| R7 | PRD 05 R7 said a 200/30 s pack yields 200 denies, contradicting the 20-action burst requirement | PRD 05 R7, PRD 17 SC-13, and WBS 12.3 reconciled: burst capacity allowed, remainder denied (20/180 defaults), one event, one digest; a test pins `allowed == per_agent_burst` |
| T10 | Unsigned producers can lie about `requested_by`, so self-review was unenforceable for them | The verifier uses a signed adapter's verified principal as the requester; `require_signed_producer = true` makes the class reject unsigned asks; the CLI sets `requested_by` to the agent (`--requested-by`), not the human |
| E9 / reload | A valid SIGHUP only swapped the escalation policy; channels/API kept the old config | Reload now rebuilds delivery channels/wiring, the scheduler escalator, retention, and `IngestAPI.update_config` (same bind/token); next tick uses the new policy |
| PRD 19/20 claims | No artifact separated code conformance from field/release claims | Added `docs/compliance/claims-and-limitations.md` with verified / not-verified / honest-label tables |

**Remaining, deliberately out of this pass:**

- **Unsigned `requested_by`:** an operator must set `require_signed_producer = true` to make the self-review
  anchor enforceable for a class; the default accepts unsigned local producers (the card labels the field
  unverified). This is a policy choice, not an unresolved bug.
- **Field/release verification:** zero-context studies, SC-01–SC-26/SC-68–SC-90, real agentwatch/agentpolicy
  joins, harness recipes, M21 ops, benches, signing/SBOM/Scorecard. These require the field-test box and the
  release pipeline; they are listed as **not verified** in
  [`docs/compliance/claims-and-limitations.md`](../../compliance/claims-and-limitations.md) and are not claimed
  as done.

## M21 operations review (2026-11-07)

| Date | M | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-07 | M21 | 21.2 | A naive `cp` of `inbox.db` is not WAL-safe; a live daemon could produce a torn backup | High | `backup_home` uses the SQLite **online-backup** API into a staging DB, then verifies the chain before packaging |
| 2026-11-07 | M21 | 21.2 | A backup could carry resolved signing secrets or the API token | High | The archive is an allow-list (`manifest`, `inbox.db`, `config.toml`, `keys/slots.json`); key slots hold **reference strings only**; `api-token`, `keys/`, spool, exports, logs are excluded; a test asserts the secret bytes are absent |
| 2026-11-07 | M21 | 21.2 | Restore could resurrect an approval whose TTL lapsed while the backup sat on disk | High | Restore expires overdue **pending** asks once (scheduler recovery semantics) and never rewrites an approved/denied decision; a fixture restores an old backup and asserts `EXPIRED` |
| 2026-11-07 | M21 | 21.2 | An archive is untrusted input; extraction could write outside the home | High | Members are an allow-list; absolute paths, `..`, symlinks, and unknown members are refused; extraction happens in a staging directory and only after chain verification is the tree installed |
| 2026-11-07 | M21 | 21.2 | Restore could clobber a live home or leave a half-written one | High | A non-empty home requires `--force`; a chain mismatch aborts before any destination write |
| 2026-11-07 | M21 | 21.1 | SIGTERM could leave a stale `serve.lock`, and a waiting `gate` could hang until its budget | Medium | The daemon writes/removes the lock; `gate` treats a lock whose PID is dead as **unavailable** (exit `4`) instead of waiting |
| 2026-11-07 | M21 | 21.1 | Service units could depend on the caller's `PATH` or require root | Medium | Units are user-scoped and use the absolute interpreter + `-m agentinbox --home … --config … serve`; install validates the config first and never calls `sudo` |
| 2026-11-07 | M21 | 21.1 | Unit paths with spaces would break the systemd `ExecStart` line | Low | `_systemd_join` quotes/escapes whitespace, quotes, and backslashes; a test renders a home with a space |
| 2026-11-07 | M21 | 21.3 | Contract/exit/event drift could ship silently | High | `agentinbox/compat.py` freezes the surface and `additive_violations` fails on a removed event, changed exit code/contract, event-version change, or schema downgrade; every released schema version has a forward-migration fixture |
| 2026-11-07 | M21 | 21.4 | A report could include answers without a delivery/creation bound or negative intervals | Medium | Response time uses the first successful delivery (falling back to `created_at`); unbounded and negative intervals are skipped; nearest-rank percentiles are pinned by a hand-computed corpus |
| 2026-11-07 | M21 | 21.4 | `report` could write evidence or call out | High | `report` is read-only (test asserts the audit length is unchanged) and opens no socket; `local_only: true` is part of the contract |
| 2026-11-07 | M21 | 21.5 | "Offline" could be asserted without proof | Medium | Doctor adds an `offline` check and the SC-26 fixture blocks non-loopback `connect`/`connect_ex` while running terminal, CI, audit, export, report, and doctor |
| 2026-11-07 | M21 | 21.6 | Bench floors could be measured on a different path than production | Medium | Benches call the real `ingest`, card renderer, resolve, spool bus, scheduler, webhook channel, and startup/doctor paths; the 10k load uses the admitted in-memory driver to isolate algorithmic cost |

## M22 security close-out review (2026-11-07)

| Date | M | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-07 | M22 | 22.1 | A scanner that shares no rules with redaction would drift and miss the classes the product actually redacts | High | The scanner imports `redaction.SENSITIVE_PATTERNS` (one source of truth); findings name rule/artifact/line, never the value |
| 2026-11-07 | M22 | 22.1 | Scanning the live store through the driver would migrate/write an old store | High | `store_artifacts_from_db` opens `mode=ro` and skips missing tables; a test asserts the mtime is unchanged |
| 2026-11-07 | M22 | 22.1 | Scanning an untrusted archive could extract members to disk | High | `scan_archive` reads member streams only; a non-tar archive is a no-op, never an exception or an extraction |
| 2026-11-07 | M22 | 22.2 | Packs that only pass in the happy case could hide a broken gate | High | A mutation fixture (`secret_matches` always true) turns `spoof-replay-forge` red; the CI job runs the packs |
| 2026-11-07 | M22 | 22.2 | The flood pack could count a digest per denied ask | High | Flood pack asserts one `ask-flood` event and one digest job for 200 asks (burst allowed, remainder denied) |
| 2026-11-07 | M22 | 22.3 | Invariant tests without a negative fixture can silently test nothing | High | Each invariant has a bad store/fixture that the shared checker detects (`agentinbox.invariants`) |
| 2026-11-07 | M22 | 22.4 | Distinct credential errors could become an oracle | High | Public causes collapse to `bad_claim`; internal causes stay in `answer-rejected` evidence; lockout is `guessing` |
| 2026-11-07 | M22 | 22.4 | Comparing secrets with `==` would leak timing | High | Claim hash, API token, and adapter HMAC all use `hmac.compare_digest`; a test asserts the call |
| 2026-11-07 | M22 | 22.5 | Caller-supplied error text could forge a log line | Medium | `sanitize_log_line` strips ANSI/control/newlines and caps length; the CLI parser and contract errors use it |
| 2026-11-07 | M22 | 22.5 | A permissive umask could create world-readable evidence | High | Creation paths force `0700`/`0600`; a test sets `umask 000` and checks home/config/store/unit modes |
| 2026-11-07 | M22 | 22.5 | A scripted approval shortcut would defeat the human gate | High | No `--yes`; only `init`/`doctor --restore` accept `--force`; a surface test pins the list |
| 2026-11-07 | M22 | 22.6 | "No ML" and SBOM claims could be marketing | Medium | The manifest reads `pyproject.toml` (runtime deps must be empty and non-ML); the SBOM is a dry run, signing deferred to M25 |
| 2026-11-07 | M22 | 22.6 | `security.txt` could ship expired | Medium | The source file is validated (Contact/Policy/Expires in the future); publishing at the domain is an explicit M25 step |

## M23 docs completion review (2026-11-07)

| Date | M | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-07 | M23 | 23.1 | A quickstart that is only read (never run) drifts immediately | High | `scripts/quickstart_step_test.py` replays the exact commands through a pty (the terminal channel is interactive by design) and asserts approval < 300 s; `tests/docs/test_quickstart.py` runs it |
| 2026-11-07 | M23 | 23.1 | A scripted answer could accidentally prove a non-interactive approval path | High | The step test uses a pseudo-terminal; the CLI still refuses scripted approval, and the test asserts the recorded approval, not a bypass |
| 2026-11-07 | M23 | 23.2 | A new flag or config key could ship undocumented | High | `tests/docs/test_doc_coverage.py` walks the parser and config dataclasses; a missing doc fails the build |
| 2026-11-07 | M23 | 23.2 | The config appendix could omit override fields | Medium | Added `allow_as`, `flood_burst`, `flood_rate_per_min`, `rescope_hint` and a complete command-options table |
| 2026-11-07 | M23 | 23.3 | A runbook with no verification step is a story | Medium | All eight RB files carry symptoms → steps → verify, matching M20/M21 behavior; a test enforces the shape |
| 2026-11-07 | M23 | 23.4 | Recipes could imply a support label the project has not earned | High | MCP/Temporal recipes are documented, not field-tested; they end in conformance + packs, not a compatibility claim |
| 2026-11-07 | M23 | 23.5 | An enterprise page that leads with features hides the gaps | High | `docs/guides/enterprise-honesty.md` leads with what v0.1.0 is **not** (no SSO, quorum, WORM, tenancy) and refuses unaudited claims |
| 2026-11-07 | M23 | 23.6 | The README still described the M0 skeleton | High | Status now reflects M22/M23; install/usage/quickstart are live and honest that PyPI/tag wait for M25 |
| 2026-11-07 | M23 | 23.6 | "Screenshots" could become stale images | Low | Terminal captures are committed text generated by the real ASCII renderer (N-40) |

## M26 ask readiness review (2026-11-07)

| Date | M | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-07 | M26 | 26.1 | A producer could self-assert a high readiness score in the payload | High | `_readiness` is reserved metadata and is stripped at ingest; the score is always derived |
| 2026-11-07 | M26 | 26.2 | Readiness rejection after the store write would leave a pending orphan | High | Scoring runs before `create_or_get`; a rejection writes nothing (test asserts empty audit/pending) |
| 2026-11-07 | M26 | 26.2 | A bare 400 would force producers to parse prose | High | `ReadinessRejection` carries `reason_code`, per-dimension `fix`, `retry`, and the readiness body; API and CLI both emit it |
| 2026-11-07 | M26 | 26.3 | "Deliver with a flag" could be silent if the card dropped it | High | The contradiction list rides `_readiness` and the banner; a 12-case corpus pins every label |
| 2026-11-07 | M26 | 26.4 | Evidence labels could say "insufficient" without naming the gap | Medium | Labels are `strong/partial/weak/absent` and the repair names the missing dimension(s) |
| 2026-11-07 | M26 | 26.4 | Freshness could be inferred from receipt time | High | Only producer-pinned `at`/`fetched_at` are used; no basis → `unknown freshness`; mixed is explicit |
| 2026-11-07 | M26 | 26.5 | Similar cases could read as a recommendation | High | Rendered as `precedent only` with outcome/fields, never "approve"; limited to 3 |
| 2026-11-07 | M26 | 26.6 | Enforcing readiness without a threshold would use a silent default | Medium | Load error names the class; `doctor --explain` prints the effective settings |

## M27 constrained allows review (2026-11-07)

| Date | M | Item | Finding | Severity | Resolution |
|---|---|---|---|---|---|
| 2026-11-07 | M27 | 27.1 | A constraint offered without an enforcer would be unenforceable | High | Selectable only when `enforcer` is declared **and** the fingerprint matches; otherwise advice-only and unpickable |
| 2026-11-07 | M27 | 27.1 | A tampered fingerprint could bind a different action | High | The fingerprint is recomputed from canonical `{id,label,enforcer,arguments,constraints}` and must match |
| 2026-11-07 | M27 | 27.2 | Suggestions could be mistaken for choices | Medium | Rendered with `suggestion` and never recorded; unpicked leaves zero constraints (test) |
| 2026-11-07 | M27 | 27.3 | A deny with no guidance forces prose parsing | High | Structured packet (invariant, missing evidence, scope, safe alternative, retry worthiness, tier) on resolve + audit |
| 2026-11-07 | M27 | 27.3 | Blind retries on a pointless denial | Medium | `retry_worthiness=pointless` for red readiness or hard objections |
| 2026-11-07 | M27 | 27.4 | An edit could silently approve a different action than the one reviewed | High | Edits are schema-bound, re-canonicalized, re-fingerprinted, and both identities are recorded |
| 2026-11-07 | M27 | 27.4 | Edits on a deny or both choice types at once | Medium | Mutually exclusive; refused with `conflicting_choice` |
| 2026-11-07 | M27 | 27.5 | Extending `status` would break old clients | High | `status` stays allow/deny/pending; `decision`/`constraints`/`edits`/`repair` are additive |
| 2026-11-07 | M27 | 27.5 | Recall could recommend an outcome | Medium | Prior denials render as `prior objection … denied once`, evidence only |
