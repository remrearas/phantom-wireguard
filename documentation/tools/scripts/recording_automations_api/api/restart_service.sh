#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# restart_service.sh - Phantom-WG restart_service API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/restart_service
# ═══════════════════════════════════════════════════════════════

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

# ═══════════════════════════════════════════════════════════════
# SCENARIO FLOW
# ═══════════════════════════════════════════════════════════════

# ─── Step 0: Initial setup ──────────────────────────────────
clear
sleep 0.5

# ─── Step 1: SSH into the server ────────────────────────────
ssh_connect

# ─── Step 2: Check current service status ───────────────────
run_command 'phantom-api core server_status | jq ".data.service.running"' "$PAUSE_AFTER_EXEC"

do_clear

# ─── Step 3: Restart the WireGuard service ──────────────────
run_command 'phantom-api core restart_service' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Verify service is running ──────────────────────
run_command 'phantom-api core server_status | jq ".data.service.running"' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
