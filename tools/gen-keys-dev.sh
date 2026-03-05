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
# Development WireGuard Server Keypair Generator
#
# Usage:
#   ./tools/gen-keys-dev.sh        Generate development keys
#   ./tools/gen-keys-dev.sh -f     Overwrite existing keys
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

IMAGE="phantom-daemon-dev:latest"
DOCKERFILE="dev.Dockerfile"
SECRETS_DIR="container-data/secrets/development"
FORCE=false

[[ "${1:-}" == "-f" || "${1:-}" == "--force" ]] && FORCE=true

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

# ── Check existing keys ──────────────────────────────────────────

if [[ -s "${SECRETS_DIR}/wg_private_key" && -s "${SECRETS_DIR}/wg_public_key" ]]; then
    if [[ "$FORCE" != true ]]; then
        red "Keys already exist in ${SECRETS_DIR}/"
        echo "Use -f to overwrite."
        exit 1
    fi
    bold "Overwriting existing keys (--force)..."
fi

# ── Ensure image exists ──────────────────────────────────────────

if ! docker image inspect "$IMAGE" &>/dev/null; then
    bold "Image $IMAGE not found. Building..."
    docker build -t "$IMAGE" -f "$DOCKERFILE" .
fi

# ── Generate keypair via bridge FFI ──────────────────────────────

bold "Generating keypair (development)..."

KEYS=$(docker run --rm "$IMAGE" python -c "
from wireguard_go_bridge.keys import generate_private_key, derive_public_key
priv = generate_private_key()
pub = derive_public_key(priv)
print(priv)
print(pub)
")

PRIVATE_KEY=$(echo "$KEYS" | sed -n '1p')
PUBLIC_KEY=$(echo "$KEYS" | sed -n '2p')

# ── Validate output ──────────────────────────────────────────────

if [[ -z "$PRIVATE_KEY" || -z "$PUBLIC_KEY" ]]; then
    red "Key generation failed — empty output."
    exit 1
fi

if [[ ${#PRIVATE_KEY} -ne 64 || ${#PUBLIC_KEY} -ne 64 ]]; then
    red "Key generation failed — unexpected key length."
    exit 1
fi

# ── Write to secrets directory ────────────────────────────────────

mkdir -p "$SECRETS_DIR"
printf '%s' "$PRIVATE_KEY" > "${SECRETS_DIR}/wg_private_key"
printf '%s' "$PUBLIC_KEY"  > "${SECRETS_DIR}/wg_public_key"
chmod 600 "${SECRETS_DIR}/wg_private_key" "${SECRETS_DIR}/wg_public_key"

# ── Summary ───────────────────────────────────────────────────────

green "Keys written to ${SECRETS_DIR}/"
echo ""
echo "  Private: ${SECRETS_DIR}/wg_private_key (${#PRIVATE_KEY} chars)"
echo "  Public:  ${SECRETS_DIR}/wg_public_key  (${#PUBLIC_KEY} chars)"
echo ""
bold "Public key:"
echo "  $PUBLIC_KEY"
