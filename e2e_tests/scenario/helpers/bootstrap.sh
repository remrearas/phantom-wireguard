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
# Scenario E2E Bootstrap — generates all secrets and auth DB
#
# Produces a clean, isolated environment under e2e_tests/scenario/container-data/
# Independent from the main development secrets.
#
# Usage:
#   e2e_tests/scenario/helpers/bootstrap.sh          (from repo root)
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCENARIO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCENARIO_DIR/../.." && pwd)"

DATA_DIR="${SCENARIO_DIR}/container-data"
SECRETS_DIR="${DATA_DIR}/secrets"
DB_DIR="${DATA_DIR}/auth-db"

AUTH_DIR="${REPO_ROOT}/services/auth-service"
DAEMON_IMAGE="phantom-daemon-dev:latest"
AUTH_IMAGE="phantom-auth:latest"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

# ── Clean slate ─────────────────────────────────────────────────

bold "Cleaning previous state..."
find "$DATA_DIR" -mindepth 1 -not -name '.gitkeep' -delete 2>/dev/null || true
mkdir -p "$SECRETS_DIR" "$DB_DIR"

# ── 1. WireGuard keypair (daemon image) ─────────────────────────

bold "Building daemon image..."
docker build -t "$DAEMON_IMAGE" -f "${REPO_ROOT}/dev.Dockerfile" "$REPO_ROOT" -q

bold "Generating WireGuard keypair..."
KEYS=$(docker run --rm "$DAEMON_IMAGE" python -c "
from wireguard_go_bridge.keys import generate_private_key, derive_public_key
priv = generate_private_key()
pub = derive_public_key(priv)
print(priv)
print(pub)
")

PRIVATE_KEY=$(echo "$KEYS" | sed -n '1p')
PUBLIC_KEY=$(echo "$KEYS" | sed -n '2p')

if [[ -z "$PRIVATE_KEY" || -z "$PUBLIC_KEY" ]]; then
    red "WireGuard key generation failed."
    exit 1
fi

printf '%s' "$PRIVATE_KEY" > "${SECRETS_DIR}/wg_private_key"
printf '%s' "$PUBLIC_KEY"  > "${SECRETS_DIR}/wg_public_key"
chmod 600 "${SECRETS_DIR}/wg_private_key" "${SECRETS_DIR}/wg_public_key"
green "  WireGuard keys generated."

# ── 2. Auth keys + DB (auth-service image) ──────────────────────

bold "Building auth image..."
docker build -t "$AUTH_IMAGE" -f "${AUTH_DIR}/Dockerfile" "$AUTH_DIR" -q

bold "Bootstrapping auth service..."
docker run --rm \
    -v "${SECRETS_DIR}:/secrets" \
    -v "${DB_DIR}:/db" \
    -v "${AUTH_DIR}/tools/bootstrap.py:/tmp/bootstrap.py:ro" \
    "$AUTH_IMAGE" \
    python /tmp/bootstrap.py \
        --secrets-dir /secrets \
        --db-dir /db \
        --admin-username admin

chmod 600 "${SECRETS_DIR}/auth_signing_key" "${SECRETS_DIR}/auth_verify_key" 2>/dev/null || true
chmod 600 "${SECRETS_DIR}/.admin_password" 2>/dev/null || true
green "  Auth keys + DB generated."

# ── Summary ─────────────────────────────────────────────────────

echo ""
green "Bootstrap complete."
echo "  Secrets:  ${SECRETS_DIR}/"
echo "  Auth DB:  ${DB_DIR}/auth.db"
echo "  Password: ${SECRETS_DIR}/.admin_password"
echo ""
ls -la "$SECRETS_DIR"
