#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# add_client.sh - Phantom-WG add_client API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/add_client
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

# ─── Step 2: Add a new client with default settings ─────────
run_command 'phantom-api core add_client client_name="demo-client"' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 3: Show the created client details ────────────────
run_command 'phantom-api core list_clients search="demo-client"' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
