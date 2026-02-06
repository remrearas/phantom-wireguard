#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# service_logs.sh - Phantom-WG service_logs API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/service_logs
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

# ─── Step 2: Get recent service logs (default) ──────────────
run_command 'phantom-api core service_logs' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 3: Get last 5 log lines ───────────────────────────
run_command 'phantom-api core service_logs lines=5' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Extract just the log lines with jq ─────────────
run_command "phantom-api core service_logs lines=3 | jq -r '.data.logs[]'" "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
