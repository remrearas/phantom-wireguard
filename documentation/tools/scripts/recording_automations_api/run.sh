#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# run.sh - Run an API Recording Script
# ═══════════════════════════════════════════════════════════════
# Usage: ./run.sh api/<script>.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 api/<script>.sh"
    echo ""
    echo "Available API scripts:"
    for script in "$SCRIPT_DIR/api/"*.sh; do
        [[ -f "$script" ]] && echo "  api/$(basename "$script")"
    done
    exit 1
fi

FULL_PATH="$SCRIPT_DIR/$1"

if [[ ! -f "$FULL_PATH" ]]; then
    echo "Script not found: $1"
    exit 1
fi

bash "$FULL_PATH"
