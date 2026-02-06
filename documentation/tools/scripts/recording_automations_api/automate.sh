#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# automate.sh - API Recording Automation
# ═══════════════════════════════════════════════════════════════
# Records all API scripts in logical order.
# Output: ./recordings/api/<script>.cast
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CAST_DIR="./recordings/api"
COLS=120
ROWS=48
IDLE_LIMIT=2

# ─── Script Order (logical flow) ────────────────────────────────
SCRIPTS=(
    "server_status"
    "add_client"
    "list_clients"
    "export_client"
    "latest_clients"
    "tweak_settings"
    "change_subnet"
    "get_firewall_status"
    "service_logs"
    "restart_service"
    "remove_client"
)

mkdir -p "$CAST_DIR"

for name in "${SCRIPTS[@]}"; do
    script="$SCRIPT_DIR/api/${name}.sh"

    if [[ ! -f "$script" ]]; then
        echo "Warning: $script not found, skipping"
        continue
    fi

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
