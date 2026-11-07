# Decision-card design — v0.1.0 (M5)

**BLUF:** One surface-neutral card core renders the four blocks — **action**, **policy**, **blast radius**,
**session so far**. Missing fields are an explicit `unknown` (never blank, never guessed), agent-supplied text
is inert plain text (labelled, escaped/stripped, capped), redaction receipts are shown instead of values, and
no approve affordance exists inside untrusted content. Every channel frontend inherits this core.

- **Milestone:** M5 ([WBS Part 3](../../wbs/v0.1.0/wbs-v0.1.0-part3-scheduler-card.md), issues #158–#168)
- **Requirements:** R1, E5 · PRD 18 §anti-injection · PRD 06 T2/T3

## 1. Model

```python
Card(ask_id, status, ttl_seconds, fingerprint, blocks[4], redactions[], flags, alternatives)
build_card(ask, now=..., transitions=...) -> Card
card.render(surface)  # text | terminal | desktop | ci
```

The four blocks are fixed and always present. Fields whose source is missing render the literal `unknown`;
there is no code path that renders an empty value. `reversibility` missing on an `irreversible` class renders
`unknown (irreversible class)` — the honest ambiguous label, not a guess in either direction.

| Block | Fields |
|---|---|
| **ACTION** | tool, action, arguments, fingerprint, class, criticality, requested by |
| **POLICY** | reason code, rule, policy version, clause |
| **BLAST RADIUS** | resource, reversibility, affected estimate, environment, data class |
| **SESSION SO FAR** | session, agent, session tail, flags, alternatives, transition count |

Trust from M2 is carried into the card: fields in `_trust.unverified` are labelled unverified; agent fields are
always untrusted.

## 2. Inert rendering (E5)

| Rule | Implementation |
|---|---|
| plain text only | no markdown/HTML renderer exists; `**x**` stays literal |
| no markup | angle-bracket tags are stripped (`<button>`, `<a …>`); no HTML surface |
| no links/actions | no URL auto-detection, no OSC-8 hyperlinks, no buttons; the only action is the documented CLI command in the footer |
| source label | untrusted non-`unknown` values are prefixed `[untrusted: tool output]` |
| control chars | C0/C1, zero-width, bidi, BOM stripped before rendering |
| caps | 512 chars per field, 4000 chars per card, visible `+N chars omitted` |
| colour | never the sole signal; `NO_COLOR` yields the same layout |

The poisoned corpus asserts these rules over 10 attack strings (fake buttons, markdown links, "ignore previous
instructions", CISO impersonation, zero-width, ANSI, comments, JSON intent).

## 3. Redaction receipts (E6)

`_redactions` is rendered as `field: [CLASS xN]`. The card never receives the raw value, so a receipt cannot
leak what it describes.

## 4. Corpora (study groundwork for M24)

`tests/fixtures/card_corpus/corpus.json` is frozen with a sha256 in `corpus.sha256`:

- **12 clean** cards (normal asks),
- **12 degraded** cards (missing context — the `unknown` discipline),
- **10 poisoned** cards (injection corpus — release-gating posture).

The checksum test makes edits deliberate; M24 owns the pre-registered answers and the 15-second study.

## 5. Tests

| File | Covers |
|---|---|
| `tests/card/test_card.py` | four blocks on all surfaces, unknown-labeling, inert/poisoned corpus, caps, receipts, corpus checksum |
