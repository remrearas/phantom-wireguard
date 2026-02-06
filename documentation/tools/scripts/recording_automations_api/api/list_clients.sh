#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# list_clients.sh - Phantom-WG list_clients API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/list_clients
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

# ─── Step 2: Create 5 demo clients ──────────────────────────
run_command 'phantom-api core add_client client_name="alice-laptop"' 1.0
run_command 'phantom-api core add_client client_name="bob-phone"' 1.0
run_command 'phantom-api core add_client client_name="charlie-tablet"' 1.0
run_command 'phantom-api core add_client client_name="diana-desktop"' 1.0
run_command 'phantom-api core add_client client_name="eve-server"' 1.5

do_clear

# ─── Step 3: List all clients (default pagination) ──────────
run_command 'phantom-api core list_clients' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Pagination demo - page 1 ───────────────────────
run_command 'phantom-api core list_clients per_page=2 page=1' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4b: Pagination demo - page 2 ──────────────────────
run_command 'phantom-api core list_clients per_page=2 page=2' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 5: Search filter demo ─────────────────────────────
run_command 'phantom-api core list_clients search="bob"' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 6: Latest clients ─────────────────────────────────
run_command 'phantom-api core latest_clients count=3' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 7: jq - name and IP table ─────────────────────────
run_command "phantom-api core list_clients | jq -r '.data.clients[] | \"\\(.name)\\t\\(.ip)\"'" "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 8: jq - total client count ────────────────────────
run_command "phantom-api core list_clients | jq '.data.total'" "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
