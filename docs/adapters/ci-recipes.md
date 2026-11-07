# CI checkpoint recipes (v0.1.0 · M10)

**BLUF:** every recipe is the same primitive: run `agentinbox gate --ask <id> --wait --timeout <s>` and let the
exit code decide. `0` = proceed; `2` = denied/cancelled; `3` = expired or budget lapsed; `4` = fail-closed;
`5` = retry. Nothing vendor-specific lives in the core.

- Design of record: [`docs/design/v0.1.0/gate.md`](../design/v0.1.0/gate.md)
- Exit contract: [`docs/reference/cli.md`](../reference/cli.md)

## Prerequisites

The runner must be on the same box as the agentinbox home (`AGENTINBOX_HOME`, default `~/.agentinbox`) and must
be able to read the store. The gate is read-only; it does not require the HTTP API to be up.

## GitHub Actions

```yaml
- name: Ask a human before the irreversible step
  env:
    AGENTINBOX_HOME: /var/lib/agentinbox
  run: |
    set -o pipefail
    agentinbox gate --ask "$ASK_ID" --wait --timeout 900 | tee gate.log
    {
      echo "### agentinbox decision"
      echo '```'
      cat gate.log
      echo '```'
    } >> "$GITHUB_STEP_SUMMARY"
```

A non-zero exit fails the step. `5` is the only code worth retrying; a later job can rerun the same command for
the same ask id.

## GitLab CI

```yaml
approve_prod_drop:
  stage: gate
  environment:
    name: production
    action: prepare
  script:
    - agentinbox gate --ask "$ASK_ID" --wait --timeout 900
  retry:
    max: 2
    when:
      - script_failure
```

Map the job to a protected environment when GitLab approvals are also required; the agentinbox ask is the
authoritative decision, the GitLab approval is additional policy, not a replacement.

## Jenkins

```groovy
stage('Human gate') {
  steps {
    withEnv(["AGENTINBOX_HOME=/var/lib/agentinbox"]) {
      sh 'agentinbox gate --ask "$ASK_ID" --wait --timeout 900'
    }
  }
}
```

A failed `sh` step aborts the pipeline; no `catch` block should turn the exit code into success.

## Argo Workflows (suspend template)

```yaml
- name: human-gate
  suspend: {}
- name: check-decision
  container:
    image: agentinbox:0.1.0
    command: ["agentinbox", "gate"]
    args: ["--ask", "{{workflow.parameters.ask-id}}", "--wait", "--timeout", "900"]
  volumes:
    - name: inbox
      hostPath: {path: /var/lib/agentinbox}
```

Argo's `suspend` parks the workflow; resume it once the ask is answered, then let `gate` re-read the store and
exit with the recorded decision.

## Cancellation

`SIGTERM`/`SIGINT` while waiting records a `cancelled` transition (channel `ci`, the OS principal) and exits `2`.
A cancelled CI job never leaves the ask pending; re-running the gate reports the cancellation consistently.

## Anti-patterns

- `agentinbox gate ... || true` — turns a denial into success.
- Parsing stdout instead of using the exit code.
- Raising `--timeout` above the ask TTL: the ask TTL still wins and returns `3`.
- A retry loop on `2/3/4`: only `5` is retryable.
