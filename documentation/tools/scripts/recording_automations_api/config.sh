#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# config.sh - Configuration for API Recording Automations
# ═══════════════════════════════════════════════════════════════
# Source this file in your recording scripts:
#   source "$(dirname "$0")/../config.sh"
#
# Requirements:
#   - asciinema (for recording)
#   - jq (for API demos)
#
# Install on Ubuntu/Debian:
#   apt-get install -y asciinema jq
# ═══════════════════════════════════════════════════════════════

# shellcheck disable=SC2034  # Variables used by sourcing scripts

# ─── Base directory ──────────────────────────────────────────
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── MOTD file ───────────────────────────────────────────────
MOTD_FILE="$CONFIG_DIR/motd.txt"

# ─── Timing settings ─────────────────────────────────────────
TYPING_MIN_DELAY=0.03       # Min delay between characters (sec)
TYPING_MAX_DELAY=0.10       # Max delay between characters (sec)
PAUSE_AFTER_TYPE=0.5        # Pause after typing before Enter (sec)
PAUSE_AFTER_EXEC=2.5        # Pause after command output (sec)
PAUSE_AFTER_EXEC_LONG=3.5   # Longer pause for verbose output (sec)
PAUSE_BEFORE_CLEAR=0.3      # Brief pause before clearing screen (sec)

# ─── Prompt styles ────────────────────────────────────────────
LOCAL_PS1="\033[1;32m❯\033[0m "
SERVER_PS1="\033[1;32mroot@server\033[0m:\033[1;34m~\033[0m# "

# ─── Output directory ─────────────────────────────────────────
RECORDINGS_DIR="./recordings/api"
