#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# server_status.sh - Phantom-WG server_status API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/server_status
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

# ─── Step 2: Get full server status ─────────────────────────
run_command 'phantom-api core server_status' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
