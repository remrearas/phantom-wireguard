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
# phantom-daemon  ·  Production Tools
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

SECRETS_DIR="container-data/secrets/production"
AUTH_DB_DIR="container-data/auth-db"
DAEMON_IMAGE="phantom-daemon:latest"
AUTH_IMAGE="phantom-auth:latest"

COMPOSE="docker compose -f docker-compose.yml"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

# ── Setup ─────────────────────────────────────────────────────────

cmd_setup() {
    bold "Full production setup..."
    cmd_gen_keys "$@"
    cmd_setup_auth "$@"
    green "Production setup complete."
    echo ""
    echo "  WG keys:      ${SECRETS_DIR}/"
    echo "  Auth keys:    ${SECRETS_DIR}/"
    echo "  Auth DB:      ${AUTH_DB_DIR}/auth.db"
    echo "  Admin pass:   ${SECRETS_DIR}/.admin_password"
    echo ""
    bold "Start with: ./tools/prod.sh up"
}

cmd_gen_keys() {
    local force=false
    for arg in "$@"; do
        [[ "$arg" == "-f" || "$arg" == "--force" ]] && force=true
    done

    if [[ -s "${SECRETS_DIR}/wg_private_key" && -s "${SECRETS_DIR}/wg_public_key" ]]; then
        if [[ "$force" != true ]]; then
            green "WG keys already exist. Use -f to overwrite."
            return 0
        fi
        bold "Overwriting WG keys (--force)..."
    fi

    # Build daemon image if needed
    if ! docker image inspect "$DAEMON_IMAGE" &>/dev/null; then
        bold "Building daemon image..."
        docker build -t "$DAEMON_IMAGE" -f Dockerfile .
    fi

    bold "Generating WireGuard keypair..."
    local keys
    keys=$(docker run --rm "$DAEMON_IMAGE" python -c "
from wireguard_go_bridge.keys import generate_private_key, derive_public_key
priv = generate_private_key()
pub = derive_public_key(priv)
print(priv)
print(pub)
")

    local private_key public_key
    private_key=$(echo "$keys" | sed -n '1p')
    public_key=$(echo "$keys" | sed -n '2p')

    if [[ -z "$private_key" || -z "$public_key" ]]; then
        red "WG key generation failed."
        exit 1
    fi

    if [[ ${#private_key} -ne 64 || ${#public_key} -ne 64 ]]; then
        red "WG key generation failed — unexpected length."
        exit 1
    fi

    mkdir -p "$SECRETS_DIR"
    printf '%s' "$private_key" > "${SECRETS_DIR}/wg_private_key"
    printf '%s' "$public_key"  > "${SECRETS_DIR}/wg_public_key"
    chmod 600 "${SECRETS_DIR}/wg_private_key" "${SECRETS_DIR}/wg_public_key"

    green "WG keys written to ${SECRETS_DIR}/"
    bold "Public key:"
    echo "  $public_key"
}

cmd_setup_auth() {
    local force=false
    local admin_username="admin"

    for arg in "$@"; do
        case "$arg" in
            -f|--force) force=true ;;
        esac
    done

    if [ ! -d "services/auth-service" ]; then
        red "services/auth-service directory not found."
        exit 1
    fi

    if [[ -f "${SECRETS_DIR}/auth_signing_key" && -f "${AUTH_DB_DIR}/auth.db" ]]; then
        if [[ "$force" != true ]]; then
            green "Auth service already bootstrapped. Use -f to overwrite."
            return 0
        fi
    fi

    mkdir -p "$SECRETS_DIR" "$AUTH_DB_DIR"

    # Build auth image if needed
    if ! docker image inspect "$AUTH_IMAGE" &>/dev/null; then
        bold "Building auth image..."
        docker build -t "$AUTH_IMAGE" -f services/auth-service/Dockerfile services/auth-service
    fi

    bold "Bootstrapping auth service..."
    local output
    output=$(docker run --rm \
        -v "$(pwd)/${SECRETS_DIR}:/secrets" \
        -v "$(pwd)/${AUTH_DB_DIR}:/db" \
        -v "$(pwd)/services/auth-service/tools/bootstrap.py:/tmp/bootstrap.py:ro" \
        "$AUTH_IMAGE" \
        python /tmp/bootstrap.py \
            --secrets-dir /secrets \
            --db-dir /db \
            --admin-username "$admin_username")

    echo "$output"

    chmod 600 "${SECRETS_DIR}/auth_signing_key" "${SECRETS_DIR}/auth_verify_key" 2>/dev/null || true
    chmod 600 "${SECRETS_DIR}/.admin_password" 2>/dev/null || true

    green "Auth service bootstrapped."
    echo "  Admin password: ${SECRETS_DIR}/.admin_password"
}

# ── Container Management ──────────────────────────────────────────

cmd_build() {
    bold "Building production images..."
    $COMPOSE build
    green "Images built."
}

cmd_up() {
    _check_secrets
    bold "Starting production stack..."
    $COMPOSE up -d
    green "Stack started."
}

cmd_down() {
    bold "Stopping production stack..."
    $COMPOSE down
    green "Stopped."
}

cmd_restart() {
    local service="${1:-}"
    if [[ -z "$service" ]]; then
        bold "Restarting all services..."
        $COMPOSE restart
    else
        bold "Restarting ${service}..."
        $COMPOSE restart "$service"
    fi
    green "Restarted."
}

cmd_logs() {
    local service="${1:-}"
    if [[ -z "$service" ]]; then
        $COMPOSE logs -f
    else
        $COMPOSE logs -f "$service"
    fi
}

cmd_status() {
    $COMPOSE ps
}

cmd_shell() {
    local service="${1:-daemon}"
    $COMPOSE exec "$service" /bin/bash
}

cmd_exec() {
    if [[ $# -lt 2 ]]; then
        red "Usage: ./tools/prod.sh exec <service> <command...>"
        exit 1
    fi
    local service="$1"
    shift
    $COMPOSE exec "$service" "$@"
}

# ── Helpers ───────────────────────────────────────────────────────

_check_secrets() {
    local missing=false
    for key in wg_private_key wg_public_key auth_signing_key auth_verify_key; do
        if [[ ! -s "${SECRETS_DIR}/${key}" ]]; then
            red "Missing: ${SECRETS_DIR}/${key}"
            missing=true
        fi
    done
    if [[ "$missing" == true ]]; then
        red "Run './tools/prod.sh setup' first."
        exit 1
    fi
}

cmd_help() {
    cat <<'HELP'
Usage: ./tools/prod.sh <command>

  Setup:
    setup               Full setup (gen-keys + setup-auth)
    gen-keys            Generate WireGuard keypair
    setup-auth          Bootstrap auth service (keys + DB + admin)

  Container:
    build               Build production images
    up                  Start production stack
    down                Stop production stack
    restart [service]   Restart all or specific service
    logs [service]      Follow logs (all or specific)
    status              Show container status
    shell [service]     Open shell (default: daemon)
    exec <svc> <cmd>    Execute command in service

  Options:
    -f, --force         Overwrite existing keys/bootstrap
HELP
}

# ── Main ──────────────────────────────────────────────────────────

case "${1:-help}" in
    setup)      shift; cmd_setup "$@" ;;
    gen-keys)   shift; cmd_gen_keys "$@" ;;
    setup-auth) shift; cmd_setup_auth "$@" ;;
    build)      cmd_build ;;
    up)         cmd_up ;;
    down)       cmd_down ;;
    restart)    shift; cmd_restart "$@" ;;
    logs)       shift; cmd_logs "$@" ;;
    status)     cmd_status ;;
    shell)      shift; cmd_shell "$@" ;;
    exec)       shift; cmd_exec "$@" ;;
    help|*)     cmd_help ;;
esac
