#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# tweak_settings.sh - Phantom-WG tweak_settings API Demo Recording
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/tweak_settings
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

# ─── Step 2: Show current settings ──────────────────────────
run_command 'phantom-api core get_tweak_settings' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 3: Update a specific setting ──────────────────────
run_command 'phantom-api core update_tweak_setting setting_name="restart_service_after_client_creation" value=true' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 4: Verify the change ──────────────────────────────
run_command 'phantom-api core get_tweak_settings' "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
