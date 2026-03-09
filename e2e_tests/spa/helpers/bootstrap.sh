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
# SPA E2E Bootstrap — generates all secrets, TLS cert, auth DB
#
# Produces a clean, isolated environment under e2e_tests/spa/container-data/
# Independent from the main development secrets.
#
# Usage:
#   e2e_tests/spa/helpers/bootstrap.sh          (from repo root)
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SPA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SPA_DIR/../.." && pwd)"

DATA_DIR="${SPA_DIR}/container-data"
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

# ── 3. TLS certificate (openssl) ────────────────────────────────

bold "Generating TLS certificate..."
docker run --rm \
    -v "${SECRETS_DIR}:/secrets" \
    alpine/openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
        -days 365 -nodes \
        -keyout /secrets/tls_key \
        -out /secrets/tls_cert \
        -subj "/C=TR/ST=Istanbul/L=Istanbul/O=Phantom-WG/OU=E2E-Test/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:nginx,IP:127.0.0.1" \
        2>/dev/null

chmod 600 "${SECRETS_DIR}/tls_key" "${SECRETS_DIR}/tls_cert" 2>/dev/null || true
green "  TLS certificate generated."

# ── Summary ─────────────────────────────────────────────────────

echo ""
green "Bootstrap complete."
echo "  Secrets:  ${SECRETS_DIR}/"
echo "  Auth DB:  ${DB_DIR}/auth.db"
echo "  Password: ${SECRETS_DIR}/.admin_password"
echo ""
ls -la "$SECRETS_DIR"
