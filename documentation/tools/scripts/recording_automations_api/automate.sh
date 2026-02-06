#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# automate.sh - API Recording Automation
# ═══════════════════════════════════════════════════════════════
# Records all API scripts. Output: ./recordings/api/<script>.cast
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CAST_DIR="./recordings/api"
COLS=120
ROWS=48
IDLE_LIMIT=2

mkdir -p "$CAST_DIR"

for script in "$SCRIPT_DIR/api/"*.sh; do
    [[ -f "$script" ]] || continue

    name=$(basename "$script" .sh)
    cast_file="${CAST_DIR}/${name}.cast"

    echo "Recording: $name"

    asciinema rec \
        --cols "$COLS" \
        --rows "$ROWS" \
        --idle-time-limit "$IDLE_LIMIT" \
        -t "$name" \
        -c "bash '$script'" \
        "$cast_file" || echo "Failed: $name"

    sleep 1
done

echo "Done. Output: $CAST_DIR/"
