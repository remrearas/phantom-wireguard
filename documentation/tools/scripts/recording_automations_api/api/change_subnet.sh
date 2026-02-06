#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# change_subnet.sh - Phantom-WG change_subnet API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/change_subnet
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

# ─── Step 2: Show current subnet info ───────────────────────
run_command 'phantom-api core get_subnet_info' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 3: Validate new subnet before change ─────────────
run_command 'phantom-api core validate_subnet_change new_subnet="192.168.100.0/24"' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Change to the new subnet ───────────────────────
run_command 'phantom-api core change_subnet new_subnet="192.168.100.0/24" confirm=true' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 5: Verify the change ──────────────────────────────
run_command 'phantom-api core get_subnet_info' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
