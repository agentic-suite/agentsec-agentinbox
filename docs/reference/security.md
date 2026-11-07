# Security reference (v0.1.0 · M22)

**BLUF:** the five PRD 06 invariants are enforced by tests that fail when violated; an evidence
scanner proves zero secret-shaped findings across store dumps, renders, exports, and backups; and the
spoof/replay/forge, injection, and flood packs are release-blocking CI jobs.

- Design: [`docs/design/v0.1.0/security-closeout.md`](../design/v0.1.0/security-closeout.md)
- Claims and limits: [`docs/compliance/claims-and-limitations.md`](../compliance/claims-and-limitations.md)
- Disclosure: [`SECURITY.md`](../../SECURITY.md) · [`docs/security.txt`](../security.txt)

## Invariants

| Invariant | Where enforced | Test |
|---|---|---|
| **I-1** no answer without a claim **and** a principal | `AnswerVerifier` (channel auth + claim + roster); the answer transition records both | `tests/security/test_invariants.py` |
| **I-2** identity binding | claim bound to ask, channel, tier, and `action_identity` (schema v5) | `tests/security/test_invariants.py`, `tests/answers/test_claims.py` |
| **I-3** timeout never allows | scheduler expiry → `expired`; zero-allow counter | `tests/security/test_invariants.py`, `tests/scheduler` |
| **I-4** untrusted text is inert | card escape/label rules; webhook payload is display-only | `tests/security/test_invariants.py`, `tests/card` |
| **I-5** no secret persisted | redaction before storage; scanner over every artifact class | `tests/security/test_invariants.py`, `tests/security/test_scanner.py` |

`agentinbox.invariants.check_store` re-checks the store from evidence: answers without a claim or
principal, and an expiry that settled as anything but `expired`, are violations.

## Evidence scanner

```sh
python -m agentinbox.scanner --self-test                 # CI gate: clean corpus = 0, seeded leak = found
python -m agentinbox.scanner --home "$HOME/.agentinbox"  # read-only store scan
python -m agentinbox.scanner --archive backup.tar        # backup members
make scan
```

Rules are the redaction pattern set (`agentinbox.redaction.SENSITIVE_PATTERNS`): provider tokens,
bearer tokens, private keys, connection strings with credentials, emails, and phone numbers.
Findings name the rule, artifact, and line — never the value. Exit `1` on any finding.

**Honest limit:** pattern scanning is a tripwire for the classes the product redacts; it does not prove
that no secret can ever be stored.

## Attack packs (release-blocking)

```sh
python -m agentinbox.packs    # exit 0 only when all three are green
make packs
```

| Pack | Attempts | Green means |
|---|---|---|
| `spoof-replay-forge` | unauthenticated answer, unknown claim, wrong secret, off-roster principal, self-review, claim reused on another ask/action, replayed claim | every attempt rejected with evidence; one valid approval; store invariants clean |
| `injection` | embedded instructions, fake urgency/CISO impersonation, markup in context | untrusted labels, markup stripped, webhook offers no decision, zero approvals from text |
| `flood` | 200 asks from one bucket | burst allowed, remainder `flood_denied`, one `ask-flood` event, one digest |

A broken gate fixture (e.g. secret comparison always true) turns `spoof-replay-forge` red; the CI job
blocks the build. The packs are standalone so M24/M32 can re-run them as drills.

## Uniform errors and constant-time comparisons

- Claim hash, API bearer token, and adapter HMAC comparisons use `hmac.compare_digest`.
- Credential failures collapse to the public cause `bad_claim`; the distinct internal cause is
  recorded in `answer-rejected` evidence (readable from the store, not from the caller).
- Five bad attempts on one claim produce `guessing`; the public body stays uniform.

## Input, log, and permission hygiene

- `sanitize_log_line` strips ANSI/control characters and newlines; CLI parse/contract errors use it.
- Per-field/total size caps reject oversized asks with a diagnostic and store nothing.
- Every creation path forces `0700` directories and `0600` files even under a permissive umask.
- There is no `--yes`; the only destructive flag is `--force` on `init` and `doctor --restore`.

## Own posture

```sh
python -m agentinbox.posture manifest      # runtime deps = 0, no ML package
python -m agentinbox.posture sbom          # CycloneDX 1.5 dry run (signed at M25)
python -m agentinbox.posture security-txt  # RFC 9116 source validation
```

`security.txt` is committed; publishing it at the project domain and signing the SBOM are M25 release
steps. Disclosure SLA: acknowledge in 48 h, triage in 5 business days, critical fix target 7 days,
coordinated disclosure 90 days.
