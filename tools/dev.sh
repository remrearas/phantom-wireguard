#!/usr/bin/env bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
#
# Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
# Licensed under AGPL-3.0 - see LICENSE file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.
# ──────────────────────────────────────────────────────────────────
# Auth Service Developer Helper
# ──────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose-dev.yml"
AUTH="auth"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

cmd_build() {
    bold "Building dev image..."
    $COMPOSE build
    green "Image built."
}

cmd_up() {
    bold "Starting auth service..."
    $COMPOSE up -d --build
    green "Auth service: http://localhost:8443"
}

cmd_down() {
    bold "Stopping auth service..."
    $COMPOSE down
    green "Stopped."
}

cmd_restart() {
    bold "Restarting auth service..."
    $COMPOSE restart "$AUTH"
    green "Restarted."
}

cmd_logs() {
    $COMPOSE logs -f "$AUTH"
}

cmd_test() {
    local docker=false
    local args=()

    for arg in "$@"; do
        if [[ "$arg" == "--docker" ]]; then
            docker=true
        else
            args+=("$arg")
        fi
    done

    if [[ "$docker" == true ]]; then
        bold "Running docker tests (inside container)..."
        $COMPOSE exec "$AUTH" python -m pytest tests/ -v -s -m "docker" "${args[@]}"
    else
        bold "Running local tests (unit + integration, excluding docker)..."
        python -m pytest tests/ -m "not docker and not slow" "${args[@]}"
    fi
}

cmd_test_full() {
    bold "Running local tests (unit + integration)..."
    python -m pytest tests/ -m "not docker and not slow" "$@"

    bold "Running docker tests (inside container)..."
    $COMPOSE exec "$AUTH" python -m pytest tests/ -v -s -m "docker" "$@"

    green "All tests passed."
}

cmd_shell() {
    $COMPOSE exec "$AUTH" /bin/bash
}

cmd_status() {
    $COMPOSE ps
}

cmd_setup() {
    bold "Running bootstrap..."
    exec tools/setup.sh "$@"
}

cmd_help() {
    cat <<'HELP'
Usage: ./tools/dev.sh <command>

  build       Build dev image
  up          Build & start auth service
  down        Stop auth service
  restart     Restart auth container
  logs        Follow auth logs
  test        Run local tests (unit + integration)
  test --docker  Run docker tests (live service scenarios)
  test-full   Run all tests (local + docker)
  shell       Open shell in auth container
  status      Show container status
  setup       Bootstrap auth service (keys + DB + admin)
HELP
}

# ── Main ─────────────────────────────────────────────────────────

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
    build)      cmd_build ;;
    up)         cmd_up ;;
    down)       cmd_down ;;
    restart)    cmd_restart ;;
    logs)       cmd_logs ;;
    test)       cmd_test "$@" ;;
    test-full)  cmd_test_full "$@" ;;
    shell)      cmd_shell ;;
    status)     cmd_status ;;
    setup)      cmd_setup "$@" ;;
    help|*)     cmd_help ;;
esac
