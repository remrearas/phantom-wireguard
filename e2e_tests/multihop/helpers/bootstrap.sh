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
# Multihop E2E Bootstrap — generates WireGuard keypair
#
# Produces a clean, isolated environment under e2e_tests/multihop/container-data/
# Independent from the main development secrets.
#
# Usage:
#   e2e_tests/multihop/helpers/bootstrap.sh          (from repo root)
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUITE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SUITE_DIR/../.." && pwd)"

DATA_DIR="${SUITE_DIR}/container-data"
SECRETS_DIR="${DATA_DIR}/secrets"

DAEMON_IMAGE="phantom-daemon-dev:latest"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

# ── Clean slate ─────────────────────────────────────────────────

bold "Cleaning previous state..."
find "$DATA_DIR" -mindepth 1 -not -name '.gitkeep' -delete 2>/dev/null || true
mkdir -p "$SECRETS_DIR"

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

# ── Summary ─────────────────────────────────────────────────────

echo ""
green "Bootstrap complete."
echo "  Secrets: ${SECRETS_DIR}/"
echo ""
ls -la "$SECRETS_DIR"