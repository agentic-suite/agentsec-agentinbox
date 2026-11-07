# Desktop notification channel (v0.1.0)

Desktop notifications are a **wake-up**, not a decision surface. The notification tells you an ask exists and
how long is left; you answer in the terminal.

## Enable

```toml
[channels.desktop]
enabled = true
```

`agentinbox doctor` reports a `desktop` check:

| State | Result |
|---|---|
| channel disabled | `ok` (`disabled`) |
| enabled and reachable | `ok` with the backend |
| enabled and unreachable (headless SSH, missing program) | `fail`, exit `4` |

An unreachable desktop never changes an ask: it stays pending and expires exactly on time.

## What a notification contains

- the ask class (for example `irreversible`);
- the action fingerprint (`sha256:…`, first 12 characters);
- the remaining TTL;
- the escalation tier, once the ladder moves;
- one line telling you the terminal command.

It **never** contains tool arguments, tool output, blast-radius text, or credentials. Notification buttons are
not wired to answers: a tap cannot approve anything, and a spoofed notification cannot name a principal.

## Platform support

| OS | Backend | Notes |
|---|---|---|
| macOS | `osascript` / Notification Center | requires a GUI session; headless SSH is reported by `doctor` |
| Linux | `notify-send` / Freedesktop | requires `DISPLAY` or `DBUS_SESSION_BUS_ADDRESS` |
| other | none | `doctor` fails when the channel is enabled |

## Notification hygiene

- one notification per `(ask, tier)`: re-running `inbox` or a redelivered bus job does not re-ping;
- escalation to the next tier produces exactly one new notification with the new tier;
- a flood produces exactly one digest notification for the window, never one notification per denied ask.

## Answering

```bash
agentinbox inbox                 # what is pending
agentinbox answer <ask-id>       # interactive, OS principal
```

The desktop channel has no `answer` path by construction: it implements `deliver()` and
`authenticate()` returns `None` always.
