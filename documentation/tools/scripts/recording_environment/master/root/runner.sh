#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# Runner Setup Script - Installs dependencies for README animation workflow
# Run this ONCE on the self-hosted runner
# ═══════════════════════════════════════════════════════════════════════════
# Reference: https://raw.githubusercontent.com/ARAS-Workspace/.github/refs/heads/main/.github/main/scripts/runner.sh

set -euo pipefail

echo "═══════════════════════════════════════════════════════════════════════════"
echo " ARAS-Workspace Runner Setup"
echo "═══════════════════════════════════════════════════════════════════════════"
echo

# ─────────────────────────────────────────────────────────────
# 1. Install asciinema
# ─────────────────────────────────────────────────────────────

echo "[1/2] Installing asciinema..."

if command -v asciinema &>/dev/null; then
    echo "  ✅ asciinema already installed: $(asciinema --version)"
else
    apt-get update
    apt-get install -y asciinema
    echo "  ✅ asciinema installed: $(asciinema --version)"
fi

# ─────────────────────────────────────────────────────────────
# 2. Install additional dependencies
# ─────────────────────────────────────────────────────────────

echo "[2/2] Installing dependencies (jq, bc, curl)..."

apt-get install -y jq bc curl
echo "  ✅ Dependencies installed"

# ─────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────

echo
echo "═══════════════════════════════════════════════════════════════════════════"
echo " Verification"
echo "═══════════════════════════════════════════════════════════════════════════"

echo -n "asciinema: "
command -v asciinema && asciinema --version || echo "❌ NOT FOUND"

echo
echo "═══════════════════════════════════════════════════════════════════════════"
echo " ✅ Setup complete! Runner is ready for README animation workflow."
echo "═══════════════════════════════════════════════════════════════════════════"