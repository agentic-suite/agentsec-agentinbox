# PRD 19 — Harness Compatibility (REQUIRED: agnostic or explicitly compatible)

**BLUF:** agentinbox is **harness-agnostic by construction** — it consumes a small JSON contract (`ask/1.0`)
reachable via HTTP, CLI, or file, so *any* agentic system with a pause-for-human mechanism can emit an ask.
For the highest-traffic surfaces we ship **named adapters** (channels: terminal/desktop/CI/webhook — Matrix
next, chat platforms optional; producers:
agentpolicy, a LangGraph reference, hook recipes per coding agent) and publish an **honest, tested
compatibility table** — every row says *field-tested*, *conformance-tested*, *documented*, or *not-supported*, and
**unsupported is stated, not implied**. agentdrill verifies the attack-facing rows with per-harness packs.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## The compatibility model (why construction beats adapters)

| Layer | How an agentic system reaches agentinbox | Effort |
|---|---|---|
| **Policy-emitting producers** (agentpolicy) | The ask contract, directly — the reference producer | Zero (shipped) |
| **Harness hooks** (Claude Code `PreToolUse`, Codex sandbox/approval surfaces, Gemini CLI approval modes, any pre-exec hook) | The hook calls `agentinbox ask` (CLI/HTTP) and translates the resolve to the harness's native permission decision | A thin recipe per harness |
| **Framework interrupts** (LangGraph `interrupt()`, OpenAI Agents SDK `needs_approval` interruptions, CrewAI `human_input`, AutoGen `human_input_mode`, PydanticAI hooks) | The interrupt payload → `ask/1.0`; the resume ← `resolve/1.0` | A thin adapter per framework |
| **Anything with a process** (CI steps, cron, glue scripts) | `agentinbox ask --exec` / `gate` | Zero (shipped) |
| **MCP surfaces** | Tool-wrapping recipe (a tool that gates itself via the local daemon); elicitation bridge for presentation | Recipe now, bridge v0.2.0 |

Because agentinbox is the **destination**, it does not need a per-harness build — it needs *producers*, and the
contract is the universal producer surface. The mandate — "never built for a single harness" — is satisfied by
construction, and the named adapters make the top surfaces **convenient**, which is a different (and real)
requirement.

## Tier 1 — Coding agents (the ≥2 at v0.1.0, all-5 by v0.3.0 mandate)

| Harness | Surface we bind to | v0.1.0 status | Evidence bar |
|---|---|---|---|
| **Claude Code** | `PreToolUse` hook → permission decision (`ask` outcome handed to us) | ◐ **documented / capture-verified** recipe (`docs/adapters/harness-recipes.md`); **not field-tested** | 11/11 LLM pairs captured; the s15 end-to-end suite was removed (see the v0.1.0 compatibility matrix) |
| **OpenAI Codex CLI** | Sandbox + approval surface; `--exec` wrapper for gated tools | ◐ **documented / capture-verified** recipe; **not field-tested** | 11/11 LLM pairs captured; the s15 end-to-end suite was removed |
| **agentpolicy-driven agents** (any harness behind our PDP) | The `ask` decision itself | ✅ **the reference path** — this is Tier-1 coverage *by construction* for every enforcer that calls agentpolicy (covers Claude Code, Codex, Copilot-class closed surfaces, and MCP traffic via agentgate) | Wave-0 demo |
| **GitHub Copilot (agent mode)** | Closed hook surface → reached at the lower layers (agentgate/agentseatbelt), **documented** | ◐ documented lower-layer coverage (same honest rule as agentpolicy's matrix) | Doc + layer pointer |
| **Cursor** | No headless/evidence-capturing hook on the field-test box | ✗ **not supported** — stated with reason; revisit if a headless surface ships | — |
| **Gemini CLI** | Approval modes exist; field-test surface unstable in this CLI build | ◐ **v0.1.x target**, not claimed at v0.1.0 | — |

**v0.1.0 ships two Tier-1 coding-agent recipes plus the agentpolicy path** (which is harness-superset by
construction). The harness recipes are **documented / capture-verified, not field-tested** because the
end-to-end s15 suite was removed; the published matrix records that label honestly rather than promoting
the captures.

## Tier 2 — Agent frameworks (≥3 by v0.3.0)

| Framework | Native HITL | Adapter status |
|---|---|---|
| **LangGraph** | `interrupt()` + checkpointer + `Command(resume=…)` | ✅ **reference adapter shipped v0.1.0** (SC-25) |
| **OpenAI Agents SDK** (py/js) | `needs_approval` → interruptions → resumable run | ◐ v0.1.x (pattern identical to reference) |
| **CrewAI** | `human_input=True` per task | ◐ v0.1.x |
| **AutoGen / AG2** | `human_input_mode` + `register_reply` | ◐ v0.1.x |
| **PydanticAI** | tool approval hooks | ◐ v0.2.0 |
| **Temporal / durable workflows** | signals + timers (ask-shaped) | ✅ recipe documented v0.1.0 |
| **LlamaIndex / smolagents / Agno / Letta / kagent** | framework-specific pauses | ○ v0.3.0 by community pull; kagent explicitly on watchlist |

**Requirement:** ≥3 Tier-2 adapters by v0.3.0 — the LangGraph reference + OpenAI Agents SDK + CrewAI are the
committed three; the adapter pattern is identical across all of them (one file each in
`docs/adapters/<framework>/` + conformance fixtures).

## Tier 3 — Protocol & enterprise surfaces

| Surface | Relationship | Version |
|---|---|---|
| **Generic MCP clients** (incl. Claude Desktop) | Ask-gating MCP tool recipe (a tool that calls the local daemon before acting) | ✅ v0.1.0 recipe |
| **MCP elicitation** | Presentation bridge; authoritative decision + audit remain ours | v0.2.0 bridge |
| **CI/CD** (GitHub Actions, GitLab, Jenkins, Argo) | `gate` step + reserved exit codes; native environment-gate semantics preserved | ✅ v0.1.0 recipes |
| **Chat platforms** (Matrix, Slack, Teams) | **Matrix is the second interactive surface (v0.1.x, open federation protocol)**; Slack/Teams are **optional community adapters** behind the identical InboxChannel contract — the product is complete with none of them | Matrix v0.1.x; Slack/Teams v0.1.x (optional) |
| **Enterprise platforms** (Copilot Studio, Agentforce, Bedrock agents) | Via standards (MCP, HTTP, OTel), never bespoke integrations | v2.x, design-partner driven |
| **A2A / CHAP-class research protocols** | Watchlist; bridge when stable | v0.3.0+ |

## The compatibility table (published per release, honest labels only)

| Surface | v0.1.0 | Label meaning |
|---|---|---|
| Claude Code | ◐ documented (capture-verified) | LLM pairs captured; no end-to-end field run |
| Codex CLI | ◐ documented (capture-verified) | LLM pairs captured; no end-to-end field run |
| LangGraph | ✅ conformance-tested | Adapter passes the fixture suite (SC-25) in CI |
| Temporal recipe | ✅ documented | Recipe + example, not field-tested |
| Generic CLI/HTTP producer | ✅ conformance-tested | The contract fixtures are the tests |
| Copilot agent mode | ◐ documented | Reached via lower layers; no field test |
| OpenAI Agents SDK / CrewAI / AutoGen | ◐ planned v0.1.x | Pattern shipped with the reference adapter |
| Cursor | ✗ not supported | Stated with reason (no headless surface) |
| MCP elicitation bridge | ◐ designed | Design doc v0.1.0, implementation v0.2.0 |

**Rules:** (1) No row is ✅ without a field-test report or a CI fixture. (2) ✗ rows state their reason. (3) The
table is regenerated per release from the field-test evidence — it is output, not aspiration
([PRD 20 §G/H](20-standards-and-claims.md)).

## Verification & governance

- **agentdrill packs** verify the attack-facing rows (flood pack, spoof pack, injection corpus) per release.
- **Conformance fixtures** (`tests/fixtures/conformance/`) let third-party adapter authors self-verify; an
  adapter enters the matrix by PR passing the same fixtures.
- **Drift watchlist:** harness hook surfaces (Claude Code hooks, Codex config, MCP elicitation evolution,
  Slack Block Kit/signing) are tracked; **policyweave**-style drift alerts apply where formats overlap.
- **The escape hatch stays forever:** `agentinbox ask --exec` means "no harness is ever blocked on us" — a
  compatibility row can regress without stranding a user.

## The portability angle (agentinbox × ecosystem)

agentpolicy **decides** (`ask`); agentinbox **serves the human** and returns the outcome; agentwatch **records**
both; agentdrill **attacks** the combination. Because the ask contract is public and small, a *competing*
inbox could replace agentinbox without rewiring the ecosystem — that is deliberate (the anti-lock-in
property the ecosystem claims elsewhere), and the compatibility table is how we stay the best consumer of
our own contract.
