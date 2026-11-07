#!/usr/bin/env bash
# Bring the field-test Docker stack up/down/verify for manual use.
#
#   stack-ft.sh up        # build + start the SUT, then WAIT until it is online
#   stack-ft.sh down      # tear down (and drop volumes)
#   stack-ft.sh ps        # show status
#   stack-ft.sh verify    # wait for running + healthy + SUT answering (exit 1 if not)
#   stack-ft.sh reset     # down -v + up (waits for readiness)
#
# Single source of truth: this reuses lib.sh's STACK_COMPOSE and FT_SERVICES.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export FT_RUN_ID="${FT_RUN_ID:-manual}"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

case "${1:-}" in
  up)
    echo "==> building + starting: ${FT_SERVICES[*]}"
    "${STACK_COMPOSE[@]}" up -d --build "${FT_SERVICES[@]}"
    if ft_wait_ready; then
      echo "==> docker setup READY (log: $FT_SETUP_LOG)"
    else
      echo "==> docker setup FAILED to come online (log: $FT_SETUP_LOG)" >&2
      "${STACK_COMPOSE[@]}" ps >&2 || true
      exit 1
    fi
    ;;
  down)
    "${STACK_COMPOSE[@]}" down -v
    ;;
  ps)
    "${STACK_COMPOSE[@]}" ps
    ;;
  verify)
    if ft_wait_ready; then echo "==> stack ONLINE (log: $FT_SETUP_LOG)"; exit 0; fi
    echo "==> stack NOT online (log: $FT_SETUP_LOG)" >&2
    exit 1
    ;;
  reset)
    "${STACK_COMPOSE[@]}" down -v
    "${STACK_COMPOSE[@]}" up -d --build "${FT_SERVICES[@]}"
    if ft_wait_ready; then
      echo "==> docker setup READY (log: $FT_SETUP_LOG)"
    else
      echo "==> docker setup FAILED to come online (log: $FT_SETUP_LOG)" >&2
      exit 1
    fi
    ;;
  *)
    echo "usage: stack-ft.sh up|down|ps|verify|reset" >&2
    exit 2
    ;;
esac
