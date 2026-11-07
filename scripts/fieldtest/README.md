# Field-test harness (`scripts/fieldtest/`)

The runnable Docker harness behind
[`docs/field-test/v0.1.0/FIELD_TEST_PLAN.md`](../../docs/field-test/v0.1.0/FIELD_TEST_PLAN.md)
and the hand-maintained
[`FIELD_TEST_REPORT.md`](../../docs/field-test/v0.1.0/FIELD_TEST_REPORT.md).

It boots the **agentinbox CLI** in a container and drives the frozen M32 matrix
through the shipped suites, with deep verification and a leak gate. There is no
LLM container and no hosted model: agentinbox's decision path is deterministic.

## Layout

| File | Role |
|---|---|
| `agentinbox.Dockerfile` | the SUT image (CLI + dev/test deps) |
| `docker-compose.fieldtest.yml` | the field-test stack (one service, no LLM) |
| `stack-ft.sh` | bring the stack up/down/verify for manual use |
| `gen_cases.py` | registry → `cases/registry.json` + `cases/steps/<ID>.sh` |
| `run-case.sh` | run one case (sources `cases/steps/<ID>.sh`) |
| `run-suite.sh` | run every case in a suite (runs the gates itself) |
| `run-all.sh` | run every suite (strict on BLOCKED) |
| `lib.sh` | per-case lifecycle, assertions, grounding, leak gate, Docker exec |
| `run_pytest.py` | grounded pytest: skip or no-tests is a failure |
| `collect-results.py` | aggregate verdicts into `summary.json` / `summary.md` |
| `check_grounding.py` | every PASS re-derived from disk (no shallow passes) |
| `scan_results.py` | leak gate over committed results |
| `verify_harness.py` | verifies the verifier (rejects a shallow pass + a planted key) |
| `t1_claude.sh` | real Claude Code `PreToolUse` harness (3-call live triple) |
| `t1_codex.sh` | real Codex CLI wrapper harness (allow + deny) |

## Run

```sh
cp scripts/fieldtest/.env.example scripts/fieldtest/.env
bash scripts/fieldtest/stack-ft.sh up            # build + start the SUT
bash scripts/fieldtest/run-suite.sh s8-readiness # one suite
bash scripts/fieldtest/run-all.sh                # all suites
```

Results land under `field-test/<FT_VERSION>/results/<suite>/`; raw setup
logs under `results/_setup/`.

## Honesty rules

- **No skips.** A case that cannot run is a failure, or `BLOCKED` for a `P/F|B`
  case with a named environment limitation (study participants, real Claude
  Code / Codex CLI). `run-all.sh` exits non-zero while any case is BLOCKED
  (`FT_STRICT_BLOCKED=1`).
- **No shallow PASS / deep validation.** `run_pytest.py` fails on skip or
  no-tests. Every case records `assertions.ndjson`; `ft_finalize` requires at
  least one grounded assertion. `check_grounding.py` re-reads every verdict from
  disk and rejects: an ungrounded PASS, a PASS containing any failed assertion,
  a count mismatch between `verdict.json` and `assertions.ndjson`, a PASS marked
  blocked, and a BLOCKED case without limitation + release-gate item.
  `verify_harness.py` proves every one of those gates can fail (and that the
  leak gate catches a planted AWS key) before a run is trusted.
- **LLM capture is mandatory for Tier-1.** `t1_proxy.py` sits between Claude
  Code / Codex CLI and the model endpoint and logs every request/response pair
  (sanitized) to `artifacts/llm/`. A Tier-1 PASS requires at least one balanced
  pair, every response 2xx, and zero secrets; deep validation fails otherwise
  (`verify_harness.py` plants each bad shape to prove the gate rejects it).
- **No leaks.** `scan_results.py` refuses unmasked secrets before results are
  committed.
- **No automation writes the report.** The report carries a
  `HAND-MAINTAINED` marker; verdicts are entered by hand from the result files.

## Current case drivers

Each registry entry names the shipped pytest selection that backs its scenario;
`gen_cases.py` generates the step scripts. The flagship CLI-level step scripts
(SC-01/68/72/75/79/83/87) are the next harness item — they will be hand-written
in `cases/steps/` and will not be clobbered by the generator.
