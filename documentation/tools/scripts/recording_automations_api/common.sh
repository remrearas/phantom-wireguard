#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# common.sh - Shared Functions for API Recording Automations
# ═══════════════════════════════════════════════════════════════
# Source this file in your recording scripts:
#   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
#   source "$SCRIPT_DIR/../common.sh"
# ═══════════════════════════════════════════════════════════════

# Determine base directory (recording_automations/)
COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source configuration
# shellcheck source=config.sh
source "$COMMON_DIR/config.sh"

# ─── Functions ────────────────────────────────────────────────

# Natural typing effect - simulates human typing
# Usage: type_text "command to type"
type_text() {
    local text="$1"
    local i
    for (( i=0; i<${#text}; i++ )); do
        local char="${text:$i:1}"
        printf '%s' "$char"

        local delay
        delay=$(awk -v min="$TYPING_MIN_DELAY" -v max="$TYPING_MAX_DELAY" \
            'BEGIN { srand(); printf "%.4f", min + rand() * (max - min) }')

        # Slightly longer pause on spaces and special chars
        if [[ "$char" == " " || "$char" == "=" || "$char" == "|" ]]; then
            delay=$(awk -v d="$delay" 'BEGIN { printf "%.4f", d + 0.04 }')
        fi

        sleep "$delay"
    done
}

# Type and execute a command locally (simulating server execution)
# Usage: run_command "phantom-api core list_clients" [pause_duration]
run_command() {
    local cmd="$1"
    local pause="${2:-$PAUSE_AFTER_EXEC}"

    # Show server prompt
    printf '%b' "${SERVER_PS1}"

    # Type the command naturally
    type_text "$cmd"

    # Brief pause before hitting Enter
    sleep "$PAUSE_AFTER_TYPE"
    printf '\n'

    # Execute the command locally
    eval "$cmd"

    # Wait for the viewer to read the output
    sleep "$pause"
}

# Execute command silently (no typing, for setup/cleanup)
# Usage: run_silent "phantom-api core remove_client client_name=test"
run_silent() {
    local cmd="$1"
    eval "$cmd" >/dev/null 2>&1 || true
}

# Clear screen with a short transition pause
do_clear() {
    sleep "$PAUSE_BEFORE_CLEAR"
    clear
}

# Show scenario header/title
# Usage: show_header "List Clients API Demo"
show_header() {
    local title="$1"
    clear
    printf '\n'
    printf '  \033[1;36m%s\033[0m\n' "═══════════════════════════════════════════════════════════"
    printf '  \033[1;37m%s\033[0m\n' "$title"
    printf '  \033[1;36m%s\033[0m\n' "═══════════════════════════════════════════════════════════"
    printf '\n'
    sleep 1.5
}

# Simulate SSH connection and show MOTD from file
# Usage: show_motd
show_motd() {
    printf '%b' "${LOCAL_PS1}"
    type_text "ssh root@server"
    sleep "$PAUSE_AFTER_TYPE"
    printf '\n'

    # Show MOTD from local file
    cat "$MOTD_FILE"
    printf '\n'
    sleep 1.5
    do_clear
}

# Alias for backward compatibility
ssh_connect() {
    show_motd
}

# Create test clients for demos
# Usage: create_test_clients "alice" "bob" "charlie"
create_test_clients() {
    local clients=("$@")
    for client in "${clients[@]}"; do
        run_command "phantom-api core add_client client_name=\"$client\"" 1.0
    done
}

# Cleanup test clients silently
# Usage: cleanup_clients "alice" "bob" "charlie"
cleanup_clients() {
    local clients=("$@")
    for client in "${clients[@]}"; do
        run_silent "phantom-api core remove_client client_name=\"$client\""
    done
}

# Wait with visible countdown (optional)
# Usage: wait_seconds 3
wait_seconds() {
    local seconds="${1:-1}"
    sleep "$seconds"
}

# Print info message (for debugging, not recorded)
# Usage: info "Starting scenario..."
info() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        printf '\033[90m[INFO] %s\033[0m\n' "$1" >&2
    fi
}

# ─── Initialization ────────────────────────────────────────────

# Ensure strict mode
set -euo pipefail

# Export functions for subshells
export -f type_text run_command run_silent do_clear show_header
export -f show_motd ssh_connect create_test_clients cleanup_clients wait_seconds info
