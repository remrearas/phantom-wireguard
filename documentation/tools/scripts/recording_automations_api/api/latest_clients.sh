#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# latest_clients.sh - Phantom-WG latest_clients API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/latest_clients
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

# ─── Step 2: Create multiple clients with timestamps ────────
run_command 'phantom-api core add_client client_name="first-client"' 1.0
run_command 'phantom-api core add_client client_name="second-client"' 1.0
run_command 'phantom-api core add_client client_name="third-client"' 1.0
run_command 'phantom-api core add_client client_name="fourth-client"' 1.5

do_clear

# ─── Step 3: Get latest 2 clients ───────────────────────────
run_command 'phantom-api core latest_clients count=2' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Get latest 4 clients ───────────────────────────
run_command 'phantom-api core latest_clients count=4' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
