#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# firewall_status.sh - Phantom-WG get_firewall_status API Demo
# ═══════════════════════════════════════════════════════════════
# Usage: Start ./record.sh first, then run this script
# Output: recordings/api/get_firewall_status
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

# ─── Step 2: Get firewall status ────────────────────────────
run_command 'phantom-api core get_firewall_status' "$PAUSE_AFTER_EXEC_LONG"

do_clear

# ─── Step 3: Extract UFW rules with jq ───────────────────────
run_command "phantom-api core get_firewall_status | jq '.data.ufw.rules'" "$PAUSE_AFTER_EXEC_LONG"

# ─── End ────────────────────────────────────────────────────
sleep 1.0
