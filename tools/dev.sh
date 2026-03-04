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
# phantom-daemon  ·  Development Tools
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE="docker compose -f docker-compose-dev.yml"
DAEMON="daemon"
GATEWAY_PORT=9080

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

cmd_up() {
    bold "Starting dev stack..."
    $COMPOSE up -d --build
    green "Gateway: http://localhost:${GATEWAY_PORT}"
}

cmd_down() {
    bold "Stopping dev stack..."
    $COMPOSE down
    green "Stopped."
}

cmd_restart() {
    bold "Restarting daemon..."
    $COMPOSE restart daemon
    green "Restarted."
}

cmd_rebuild() {
    bold "Rebuilding..."
    $COMPOSE down
    $COMPOSE build --no-cache
    green "Rebuilt. Run './tools/dev.sh up' to start."
}

cmd_logs() {
    $COMPOSE logs -f daemon
}

cmd_test() {
    bold "Running pytest (ASGI mode)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v -s
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v -s "$@"
    fi
}

cmd_test_uds() {
    bold "Running pytest (UDS mode)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v --uds /var/run/phantom/daemon.sock
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v --uds /var/run/phantom/daemon.sock "$@"
    fi
}

cmd_shell() {
    $COMPOSE exec "$DAEMON" /bin/bash
}

cmd_curl() {
    local path="${1:-/api/core/hello}"
    curl -s "http://localhost:${GATEWAY_PORT}${path}" | python3 -m json.tool
}

cmd_status() {
    $COMPOSE ps
}

cmd_db_ls() {
    bold "Local db/ contents:"
    ls -lah container-data/db/ 2>/dev/null || red "db/ is empty or missing"
}

cmd_db_ls_r() {
    bold "Container db/ contents:"
    $COMPOSE exec "$DAEMON" ls -lah /var/lib/phantom/db/ 2>/dev/null || red "No db files in container"
}

cmd_db_reset() {
    bold "Wiping db/..."
    rm -rf container-data/db/*
    green "db/ cleared."
}

cmd_state_reset() {
    bold "Wiping state/db/..."
    rm -rf container-data/state/db/*
    green "state/db cleared."
}

cmd_stubs() {
    local image="phantom-daemon-dev:latest"
    local dockerfile="dev.Dockerfile"
    local out_dir="typings"
    local vendor_dir="/opt/phantom/vendor"

    # Ensure image exists
    if ! docker image inspect "$image" &>/dev/null; then
        bold "Image $image not found. Building..."
        docker build -t "$image" -f "$dockerfile" .
    fi

    # Prepare output directory
    rm -rf "$out_dir"
    mkdir -p "$out_dir"

    # Generate stubs inside container
    bold "Generating type stubs from vendor packages..."
    docker run --rm \
        -v "$(pwd)/tools/gen_stubs.py:/tmp/gen_stubs.py:ro" \
        -v "$(pwd)/$out_dir:/out" \
        "$image" \
        python /tmp/gen_stubs.py "$vendor_dir" /out

    green "Stubs written to ${out_dir}/"
}

cmd_help() {
    cat <<'HELP'
Usage: ./tools/dev.sh <command>

  up          Build & start dev stack
  down        Stop dev stack
  restart     Restart daemon container
  rebuild     Full rebuild (no-cache)
  logs        Follow daemon logs
  test        Run pytest (ASGI)
  test-uds    Run pytest (UDS)
  shell       Open shell in daemon
  curl <path> Query via gateway
  status      Show containers
  db-ls       List db/ (local)
  db-ls-r     List db/ (container)
  db-reset    Wipe db/
  state-reset Wipe state/db/
  stubs       Generate .pyi vendor stubs
HELP
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-help}" in
    up)       cmd_up ;;
    down)     cmd_down ;;
    restart)  cmd_restart ;;
    rebuild)  cmd_rebuild ;;
    logs)     cmd_logs ;;
    test)     shift; cmd_test "$@" ;;
    test-uds) shift; cmd_test_uds "$@" ;;
    shell)    cmd_shell ;;
    curl)     shift; cmd_curl "$@" ;;
    status)   cmd_status ;;
    db-ls)    cmd_db_ls ;;
    db-ls-r)  cmd_db_ls_r ;;
    db-reset)    cmd_db_reset ;;
    state-reset) cmd_state_reset ;;
    stubs)       cmd_stubs ;;
    help|*)      cmd_help ;;
esac