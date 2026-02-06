#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# record.sh - Asciinema Terminal Recorder
# ═══════════════════════════════════════════════════════════════
# Usage: ./record.sh <recording-name> [title]
#
# Examples:
#   ./record.sh add_client
#   ./record.sh add_client "Add Client API"
#
# Output: recordings/api/<name>
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Configuration ──────────────────────────────────────────
COLS=120
ROWS=48
IDLE_LIMIT=2

# Output directory
CAST_DIR="./recordings"

# ─── Functions ──────────────────────────────────────────────

usage() {
    echo "Usage: $0 <recording-name> [title]"
    echo ""
    echo "Examples:"
    echo "  $0 add_client"
    echo "  $0 add_client \"Add Client API\""
    exit 1
}

check_dependencies() {
    if ! command -v asciinema &>/dev/null; then
        echo "Error: asciinema not found"
        echo "Install: pip install asciinema"
        exit 1
    fi
}

interactive_trim() {
    local cast_file="$1"

    clear
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "POST-PROCESS: Trim Recording"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Last 25 lines of the recording:"
    echo "────────────────────────────────────────────────────────────"
    nl -ba "$cast_file" | tail -n 25
    echo "────────────────────────────────────────────────────────────"
    echo ""
    echo "Enter a line number to remove that line and everything below."
    echo "Press Enter to skip."
    echo ""
    # shellcheck disable=SC2162
    read -p "Trim from line: " trim_line

    if [[ -n "$trim_line" ]]; then
        sed -i "${trim_line},\$d" "$cast_file"
        echo ""
        echo "✓ Trimmed: Removed line $trim_line and below"
    else
        echo ""
        echo "✓ No trimming"
    fi

    sleep 1
}

# ─── Main ───────────────────────────────────────────────────

main() {
    [[ $# -lt 1 ]] && usage

    local name="$1"
    local title="${2:-$name}"
    local cast_file="${CAST_DIR}/${name}"

    check_dependencies

    mkdir -p "$CAST_DIR"

    # Set terminal size
    printf '\033[8;%d;%dt' "$ROWS" "$COLS"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Recording: $title"
    echo "Output: $cast_file"
    echo "Exit with: Ctrl+D"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo

    # Record
    asciinema rec \
        --cols "$COLS" \
        --rows "$ROWS" \
        --idle-time-limit "$IDLE_LIMIT" \
        -t "$title" \
        "$cast_file"

    echo
    echo "Recording complete: $cast_file"
    echo

    # Ask for trim
    # shellcheck disable=SC2162
    read -p "Trim last lines? [y/N]: " trim_choice

    if [[ "$trim_choice" =~ ^[Yy]$ ]]; then
        interactive_trim "$cast_file"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✓ Complete: $cast_file"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main "$@"
