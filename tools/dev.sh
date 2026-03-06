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

cmd_build() {
    bold "Building dev images..."
    $COMPOSE build
    green "Images built."
}

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
    bold "Running pytest (ASGI mode, excluding slow)..."
    if [ $# -eq 0 ]; then
        $COMPOSE exec "$DAEMON" python -m pytest tests/ -v -s -m "not slow"
    else
        $COMPOSE exec "$DAEMON" python -m pytest -v -s -m "not slow" "$@"
    fi
}

cmd_test_full() {
    bold "Running pytest (ASGI mode, all tests)..."
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

cmd_openapi() {
    bold "Exporting OpenAPI schema..."
    $COMPOSE exec "$DAEMON" python -c "
import json
from phantom_daemon.main import create_app
app = create_app(lifespan_func=None)
print(json.dumps(app.openapi(), indent=2))
" > openapi.json
    green "Written to openapi.json"
}

cmd_test_multighost_e2e() {
    if [ ! -d "lib/compose_bridge" ] || [ -z "$(ls lib/compose_bridge/*.so lib/compose_bridge/*.dylib 2>/dev/null)" ]; then
        red "compose-bridge not found. Run: ./tools/dev.sh fetch-compose-bridge"
        exit 1
    fi
    bold "Running multighost E2E tests..."
    local lib_file
    lib_file="$(find lib/compose_bridge -maxdepth 1 \( -name '*.dylib' -o -name '*.so' \) -print -quit)"
    COMPOSE_BRIDGE_LIB_PATH="$(pwd)/${lib_file}" \
    PYTHONPATH="$(pwd)/lib:${PYTHONPATH:-}" \
    python3 e2e_tests/multighost/runner.py "$@"
}

cmd_test_chaos_e2e() {
    if [ ! -d "lib/compose_bridge" ] || [ -z "$(ls lib/compose_bridge/*.so lib/compose_bridge/*.dylib 2>/dev/null)" ]; then
        red "compose-bridge not found. Run: ./tools/dev.sh fetch-compose-bridge"
        exit 1
    fi
    bold "Running chaos E2E tests..."
    local lib_file
    lib_file="$(find lib/compose_bridge -maxdepth 1 \( -name '*.dylib' -o -name '*.so' \) -print -quit)"
    COMPOSE_BRIDGE_LIB_PATH="$(pwd)/${lib_file}" \
    PYTHONPATH="$(pwd)/lib:${PYTHONPATH:-}" \
    python3 e2e_tests/chaos/runner.py "$@"
}

cmd_test_scenario_e2e() {
    if [ ! -d "lib/compose_bridge" ] || [ -z "$(ls lib/compose_bridge/*.so lib/compose_bridge/*.dylib 2>/dev/null)" ]; then
        red "compose-bridge not found. Run: ./tools/dev.sh fetch-compose-bridge"
        exit 1
    fi
    bold "Running scenario E2E tests..."
    local lib_file
    lib_file="$(find lib/compose_bridge -maxdepth 1 \( -name '*.dylib' -o -name '*.so' \) -print -quit)"
    COMPOSE_BRIDGE_LIB_PATH="$(pwd)/${lib_file}" \
    PYTHONPATH="$(pwd)/lib:${PYTHONPATH:-}" \
    python3 e2e_tests/scenario/runner.py "$@"
}

cmd_fetch_compose_bridge() {
    local repo="ARAS-Workspace/phantom-wg"
    local run_id="22726661393"
    local version="1.0.0"
    local dest="lib/compose_bridge"

    # Detect platform
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"
    case "$arch" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        arm64)   arch="arm64" ;;
        *)       red "Unsupported architecture: $arch"; exit 1 ;;
    esac

    local artifact_name="compose-bridge-${version}-${os}-${arch}"

    if ! command -v gh &>/dev/null; then
        red "GitHub CLI (gh) required: brew install gh"
        exit 1
    fi

    if ! gh auth status &>/dev/null; then
        red "Not authenticated. Run: gh auth login"
        exit 1
    fi

    bold "Fetching ${artifact_name}..."

    # Clean destination
    rm -rf "$dest"
    mkdir -p "$dest"

    # Download artifact zip
    local tmp_dir
    tmp_dir="$(mktemp -d)"

    gh run download "$run_id" \
        --repo "$repo" \
        --name "$artifact_name" \
        --dir "$tmp_dir"

    # The artifact contains a zip: compose-bridge-VERSION-PLATFORM.zip
    local zip_file="$tmp_dir/${artifact_name}.zip"
    if [ -f "$zip_file" ]; then
        # Zip contains compose_bridge/ directory — extract contents to dest
        unzip -o "$zip_file" -d "$tmp_dir/extracted"
        cp "$tmp_dir/extracted/compose_bridge/"* "$dest/"
    else
        # gh download extracts the artifact directly
        cp "$tmp_dir/"* "$dest/" 2>/dev/null || true
    fi

    rm -rf "$tmp_dir"

    green "Installed to ${dest}/"
    ls -lh "$dest/"
}

cmd_setup_auth() {
    local auth_dir="services/auth-service"
    local secrets_dir="container-data/secrets/development"
    local db_dir="container-data/auth-db"
    local image="phantom-auth:latest"
    local admin_username="admin"
    local force=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--force) force=true; shift ;;
            --username) admin_username="$2"; shift 2 ;;
            *) red "Unknown option: $1"; exit 1 ;;
        esac
    done

    if [ ! -d "$auth_dir" ]; then
        red "auth-service not found. Run: ./tools/dev.sh fetch-auth-service"
        exit 1
    fi

    if [[ -f "${secrets_dir}/auth_signing_key" && -f "${db_dir}/auth.db" ]]; then
        if [[ "$force" != true ]]; then
            red "Auth service already bootstrapped."
            echo "  Keys: ${secrets_dir}/"
            echo "  DB:   ${db_dir}/auth.db"
            echo "  Use -f to force re-bootstrap."
            exit 0
        fi
    fi

    mkdir -p "$secrets_dir" "$db_dir"

    bold "Building auth image..."
    docker build -t "$image" -f "${auth_dir}/Dockerfile" "$auth_dir"

    bold "Running bootstrap..."
    local output
    output=$(docker run --rm \
        -v "$(pwd)/${secrets_dir}:/secrets" \
        -v "$(pwd)/${db_dir}:/db" \
        -v "$(pwd)/${auth_dir}/tools/bootstrap.py:/tmp/bootstrap.py:ro" \
        "$image" \
        python /tmp/bootstrap.py \
            --secrets-dir /secrets \
            --db-dir /db \
            --admin-username "$admin_username")

    echo "$output"

    chmod 600 "${secrets_dir}/auth_signing_key" "${secrets_dir}/auth_verify_key" 2>/dev/null || true
    chmod 600 "${secrets_dir}/.admin_password" 2>/dev/null || true

    green "Auth service bootstrapped."
    echo "  Keys:     ${secrets_dir}/"
    echo "  DB:       ${db_dir}/auth.db"
    echo "  Password: ${secrets_dir}/.admin_password"
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

  build       Build dev images (no start)
  up          Build & start dev stack
  down        Stop dev stack
  restart     Restart daemon container
  rebuild     Full rebuild (no-cache)
  logs        Follow daemon logs
  test        Run pytest (ASGI, excluding slow)
  test-full   Run pytest (ASGI, all tests incl. slow)
  test-uds    Run pytest (UDS)
  test-multighost-e2e Run multighost E2E tests (5-container)
  test-chaos-e2e Run chaos E2E tests (5-container, restart recovery)
  test-scenario-e2e Run scenario E2E tests (5-container, auth-service user journey)
  shell       Open shell in daemon
  curl <path> Query via gateway
  status      Show containers
  db-ls       List db/ (local)
  db-ls-r     List db/ (container)
  db-reset    Wipe db/
  state-reset Wipe state/db/
  stubs       Generate .pyi vendor stubs
  openapi     Export OpenAPI schema (openapi.json)
  fetch-compose-bridge  Download compose-bridge artifact for current platform
  setup-auth            Bootstrap auth service (keys + DB + admin)
HELP
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-help}" in
    build)    cmd_build ;;
    up)       cmd_up ;;
    down)     cmd_down ;;
    restart)  cmd_restart ;;
    rebuild)  cmd_rebuild ;;
    logs)     cmd_logs ;;
    test)          shift; cmd_test "$@" ;;
    test-full)     shift; cmd_test_full "$@" ;;
    test-uds)      shift; cmd_test_uds "$@" ;;
    test-multighost-e2e) shift; cmd_test_multighost_e2e "$@" ;;
    test-chaos-e2e) shift; cmd_test_chaos_e2e "$@" ;;
    test-scenario-e2e) shift; cmd_test_scenario_e2e "$@" ;;
    shell)    cmd_shell ;;
    curl)     shift; cmd_curl "$@" ;;
    status)   cmd_status ;;
    db-ls)    cmd_db_ls ;;
    db-ls-r)  cmd_db_ls_r ;;
    db-reset)    cmd_db_reset ;;
    state-reset) cmd_state_reset ;;
    stubs)       cmd_stubs ;;
    openapi)     cmd_openapi ;;
    fetch-compose-bridge) cmd_fetch_compose_bridge ;;
    setup-auth) shift; cmd_setup_auth "$@" ;;
    help|*)      cmd_help ;;
esac