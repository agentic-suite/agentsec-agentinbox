# Desktop notification design — v0.1.0 (M8)

**BLUF:** Desktop notifications are a **wake-up, never a decision surface**. The notification carries only the
fingerprint, class, and remaining TTL; the human answers in the terminal under the OS session. There is no
notification button, reply path, or deep link that can submit an answer — a spoofed notification cannot forge a
principal. Unavailability (headless SSH, no daemon) is a `doctor` finding and leaves the ask pending with its TTL
unchanged.

- **Milestone:** M8 ([WBS Part 5](../../wbs/v0.1.0/wbs-v0.1.0-part5-desktop-bus.md), issues #192–#202)
- **Requirements:** R2, E4, E9 · PRD 16 §B.2, PRD 06 channel table, PRD 13 N-3a/N-34 · CUJ-3, CUJ-5

---

## 1. Content rules

| Field | Source | Rule |
|---|---|---|
| title | `ask.payload.class` + `ask.ask_id` | plain text, capped |
| fingerprint | `ask.action_identity` | first 12 hex chars, prefixed `sha256:` |
| body | class + remaining TTL | `class=… · expires in mm:ss` |
| thread | `ask.ask_id` | re-notify replaces/updates the same conversation |
| footer | constant | `Answer in the terminal: agentinbox answer <id>` |

**Never included:** `arguments`, `tool`, `action`, blast radius, session tail, policy clause, any payload text.
The renderer selects fields from `AskRecord`, not from the card body. Tests assert that marker secrets placed in
the payload do not appear in the notification.

Notification action buttons are **not wired**. The desktop backend is invoked with the message only; no
per-platform callback URL, no reply parser.

## 2. Backends

| OS | Program | Invocation |
|---|---|---|
| macOS | `osascript` | argv list, `display notification … with title …` |
| Linux | `notify-send` | argv list, `--app-name agentinbox --urgency critical` |
| otherwise | none | `UnavailableNotifier` raises `ChannelError` |

Commands are executed with an argv list (`subprocess.run(..., shell=False)`) and a bounded timeout. A backend
failure is a delivery failure — the ask stays pending.

## 3. The channel contract

`DesktopChannel` implements `InboxChannel`:

- `deliver(ask, card)` renders and sends the notification, then records nothing (delivery accounting is M13);
- `authenticate()` returns `None` **always** — a notification authenticates no principal, so no answer can be
  submitted through this channel;
- no `answer`, `submit`, or `decide` method exists.

The shared channel conformance suite (`tests/channels/conformance.py`) asserts the no-decide property for every
channel; the desktop adapter additionally asserts `authenticate() is None`.

## 4. Escalation and flood hygiene

- A notification key is `(ask_id, tier)`; a repeated delivery for the same key in the same tier is suppressed.
  After the scheduler moves the ask to a new tier, exactly one new notification is emitted, with tier context.
- A flood digest is one notification per window (`kind="digest"`), keyed by `(digest_window, first_ask_id)`.
  Individual flood-denied asks never notify.
- `quiet` behaviour honours the channel `enabled` flag: a disabled desktop channel delivers nothing and records
  no error.

## 5. Reachability and `doctor`

`desktop_availability()` reports `(available: bool, detail: str)`:

- macOS: `osascript` is on `PATH` **and** the process has a GUI session (not `SSH_CONNECTION`-only);
- Linux: `notify-send` is on `PATH` **and** `DISPLAY` or `DBUS_SESSION_BUS_ADDRESS` is set;
- disabled channel: availability is irrelevant; `doctor` reports `ok` with `disabled`.

`doctor` gains a `desktop` check:

- disabled → `ok` (`disabled`);
- enabled + available → `ok`;
- enabled + unavailable → `fail` (exit `4`), with the reason and the remediation;
- the ask path is unaffected: delivery failure never extends or shortens a TTL.

## 6. Tests

`tests/channels/test_desktop.py` covers rendering/content rules, both backends (mocked subprocess), the
deliver-only contract, once-per-tier and single-digest counts, disabled behaviour, and availability detection.
`tests/cli/test_doctor_desktop.py` covers the `doctor` check and exit code.
