# Producer adapters design — v0.1.0 (M18)

**BLUF:** three producer paths, one contract. The **agentpolicy reference adapter** signs the trusted fields; the
**universal CLI** gates a file or an exact command; the **loopback HTTP API** is the transport, hardened with a
token, optional producer signatures, uid recording, caps, and flood limiting. CUJ-1 (install → first recorded
approval) is measured here.

- **Milestone:** M18 ([WBS Part 10](../../wbs/v0.1.0/wbs-v0.1.0-part10-adapters-conformance.md), issues #29–#39)
- **Requirements:** E1, E4, E19, N-31 · PRD 16 §E.1/E.2/E.5, PRD 18 T13/T14 · D-6, D-7 · CUJ-1

---

## 1. Producer profile

| Producer | Transport | Identity | Trusted fields |
|---|---|---|---|
| agentpolicy adapter | `POST /v1/asks` + long-poll | adapter key HMAC + principal header | trusted (`class`, `criticality`, `data_class`, `environment`, `policy_ref`, `reason_code`) |
| universal CLI (`ask`) | direct store | local OS user | unverified (no adapter) |
| loopback HTTP | `POST /v1/asks` | per-process bearer token | unverified unless signed |

The bearer token authenticates the *client*; the adapter HMAC authenticates the *trusted fields*. A valid token
without an adapter signature is an ordinary unauthenticated producer — it cannot claim trusted class/policy
fields.

## 2. Signed trusted fields

```http
POST /v1/asks
Authorization: Bearer <token>
X-AgentInbox-Adapter: agentpolicy
X-AgentInbox-Principal: maya@team
X-AgentInbox-Signature: sha256=<HMAC-SHA256 over the exact canonical body>
```

The key comes from `[producers.agentpolicy].key_ref` (env/file reference, never a literal). An unknown adapter or
a bad signature is `401` and nothing is ingested. The `_producer` evidence records adapter, authenticated,
principal, and remote address; `_trust` then marks the trusted fields verified.

## 3. `ask --exec` / `ask --file`

```
agentinbox ask --exec "<command>" [--class C] [--environment E] [--ttl S] [--timeout S]
agentinbox ask --file ask.json [--timeout S]
```

- `--exec` builds a contract-valid `ask/1.0` body (tool `shell`, action `run_command`) with a computed
  `action_identity`, ingests it, and waits on the gate.
- The command is executed **only** on exit `0`; deny (`2`), expiry (`3`), and unavailable (`4`) never run it.
- The executed command is split with `shlex` and run without a shell; shell features require `sh -c`.
- The command's own exit status is returned after an allow; the decision itself is printed to stderr.
- `--file` ingests a validated ask and prints the `resolve/1.0` outcome (`--json`) or a one-line
  `status (reason_code)`.

The CLI ingests directly into the local store; it does not need the HTTP API to be running. Flood protection and
caps apply exactly as on the API path.

## 4. API hardening

- Bearer token compared in constant time; the bind is loopback only.
- Producer adapter signatures as above; unknown/invalid adapters fail closed with `401`.
- Body caps (per-field, object, total) are re-verified at this level; oversize is drained then `413`.
- Loopback TCP does not expose a peer uid; the recorded identity is the remote address plus the adapter
  principal. Unix-socket credentials are the forward-slate upgrade.
- Ingest is flood-limited by the M12 guard (per agent/session/environment/producer key).

## 5. CUJ-1 timing

`init` (terminal-only scaffold) → `ask --exec` → terminal answer → resolve is well under five minutes by
construction; the local path is measured by a fixture. The install step is measured on the field-test box at M24
and recorded there.

## 6. Tests

`tests/adapters/test_agentpolicy.py` covers signed trusted fields, bad/unknown signatures, and the full
create → answer → allow round-trip. `tests/cli/test_ask.py` covers `--exec` allow/deny/expiry and `--file`.
`tests/cli/test_cuj1.py` measures the onboarding path.
