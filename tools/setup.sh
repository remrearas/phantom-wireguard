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
# Auth Service Bootstrap
#
# Generates Ed25519 keypair, creates auth.db, and creates initial
# admin user inside the auth container image.
#
# Usage:
#   ./tools/setup.sh                Bootstrap auth service (development)
#   ./tools/setup.sh --production   Bootstrap for production (Docker secrets)
#   ./tools/setup.sh -f             Force re-bootstrap
#   ./tools/setup.sh --username X   Custom admin username
# ──────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="phantom-auth:latest"
DOCKERFILE="Dockerfile"
DB_DIR="container-data/auth-db"
FORCE=false
ADMIN_USERNAME="admin"
ENV="development"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--force) FORCE=true; shift ;;
        --username) ADMIN_USERNAME="$2"; shift 2 ;;
        --production) ENV="production"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ "$ENV" == "production" ]]; then
    SECRETS_DIR="container-data/secrets"
else
    SECRETS_DIR="container-data/secrets/development"
fi

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

# ── Check existing setup ─────────────────────────────────────────

if [[ -f "${SECRETS_DIR}/auth_signing_key" && -f "${DB_DIR}/auth.db" ]]; then
    if [[ "$FORCE" != true ]]; then
        red "Auth service already bootstrapped."
        echo "  Keys: ${SECRETS_DIR}/"
        echo "  DB:   ${DB_DIR}/auth.db"
        echo ""
        echo "Use -f to force re-bootstrap (destroys existing data)."
        exit 1
    fi
    bold "Force re-bootstrap — removing existing data..."
    rm -f "${SECRETS_DIR}/auth_signing_key" "${SECRETS_DIR}/auth_verify_key"
    rm -f "${SECRETS_DIR}/.admin_password"
    rm -f "${DB_DIR}/auth.db" "${DB_DIR}/auth.db-wal" "${DB_DIR}/auth.db-shm"
fi

# ── Ensure directories exist ─────────────────────────────────────

mkdir -p "$SECRETS_DIR" "$DB_DIR"

# ── Ensure image exists ──────────────────────────────────────────

if ! docker image inspect "$IMAGE" &>/dev/null; then
    bold "Image $IMAGE not found. Building..."
    docker build -t "$IMAGE" -f "$DOCKERFILE" .
fi

# ── Run bootstrap inside container ───────────────────────────────

bold "Bootstrapping auth service..."

OUTPUT=$(docker run --rm \
    -v "$(pwd)/${SECRETS_DIR}:/secrets" \
    -v "$(pwd)/${DB_DIR}:/db" \
    -v "$(pwd)/tools/bootstrap.py:/tmp/bootstrap.py:ro" \
    "$IMAGE" \
    python /tmp/bootstrap.py \
        --secrets-dir /secrets \
        --db-dir /db \
        --admin-username "$ADMIN_USERNAME")

# ── Validate output ──────────────────────────────────────────────

if ! echo "$OUTPUT" | grep -q "BOOTSTRAP_OK=1"; then
    red "Bootstrap failed:"
    echo "$OUTPUT"
    exit 1
fi

# ── Set permissions ──────────────────────────────────────────────

chmod 600 "${SECRETS_DIR}/auth_signing_key" "${SECRETS_DIR}/auth_verify_key"
chmod 600 "${SECRETS_DIR}/.admin_password"

# ── Summary ───────────────────────────────────────────────────────

PASSWORD_FILE="${SECRETS_DIR}/.admin_password"

echo ""
green "Auth service bootstrapped successfully!"
echo ""
echo "  Signing key: ${SECRETS_DIR}/auth_signing_key"
echo "  Verify key:  ${SECRETS_DIR}/auth_verify_key"
echo "  Database:    ${DB_DIR}/auth.db"
echo ""
bold "Admin credentials:"
echo "  Username: ${ADMIN_USERNAME}"
echo "  Password: *****"
echo ""
bold "To retrieve the admin password:"
echo "  cat ${PASSWORD_FILE}"
echo ""
red "IMPORTANT: Read and delete the password file after first login:"
echo "  rm ${PASSWORD_FILE}"
