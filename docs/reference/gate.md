# `gate` reference (v0.1.0 · M10)

**BLUF:** `agentinbox gate` blocks an irreversible CI step on a human decision and maps it to the reserved exit
codes. It is read-only except for one `cancelled` transition on `SIGTERM`/`SIGINT`.

```sh
agentinbox gate --ask <ask-id> [--wait] [--timeout <seconds>]
```

| Option | Meaning |
|---|---|
| `--ask ID` | required; the ask id from the ingest response |
| `--wait` | block until resolved or the deadline lapses |
| `--timeout S` | CI budget in seconds; `min(budget, ask.expires_at)` |

## Exit codes

| Outcome | Code |
|---|---|
| approved | `0` |
| denied / flood-denied / cancelled | `2` |
| expired (ask TTL) or gate budget lapsed | `3` |
| unknown ask, bad config, unreadable/locked store | `4` |
| pending (no `--wait`, or still within the budget) | `5` |

Only `5` is retryable. A lapsed `--timeout` returns `3` **without** mutating the ask, so a later CI retry can
still see a real decision.

## Output

The command prints the M5 card rendered for the `ci` surface (ask id, fingerprint, status, TTL, blocks) followed
by one line:

```text
agentinbox: ask ask_…: approved (allow_ask_approved)
```

## Cancellation

`SIGTERM`/`SIGINT` sets a cancel flag; the gate records a `pending → cancelled` transition with kind
`gate-cancelled`, channel `ci`, the OS principal, and `detail.signal`, then exits `2`. If another writer won the
race, the real outcome is reported and no cancellation is written.

## Recipes

GitHub Actions, GitLab, Jenkins, and Argo examples: [ci-recipes.md](../adapters/ci-recipes.md).
