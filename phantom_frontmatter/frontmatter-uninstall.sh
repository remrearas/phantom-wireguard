#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
# Licensed under AGPL-3.0 - see LICENSE file for details
# Third-party licenses - see THIRD_PARTY_LICENSES file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.
#
# Phantom-WG Frontmatter — Uninstall
#
# Returns the front server to the pre-install state and removes
# Phantom-WG Frontmatter from the host.
#
# What this script cleans up:
#   1. systemd services (wstunnel, egress — stop + disable + remove unit)
#   2. Any lingering wstunnel / socat processes started by those units
#   3. Installation directory (/opt/phantom-frontmatter)
#   4. Global command symlinks (frontmatter-api, frontmatter-uninstall)
#   5. systemd daemon-reload to clear the unit cache
#
#
# Usage:
#   sudo frontmatter-uninstall
#   sudo frontmatter-uninstall --yes    # skip confirmation
#
#   (Or run the script directly from the installation directory:
#    sudo /opt/phantom-frontmatter/phantom_frontmatter/frontmatter-uninstall.sh)

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────

INSTALL_DIR="/opt/phantom-frontmatter"
BIN_LINK="/usr/local/bin/frontmatter-api"
CERTBOT_LINK="/usr/local/bin/frontmatter-certbot"
UNINSTALL_LINK="/usr/local/sbin/frontmatter-uninstall"

WSTUNNEL_SERVICE="phantom-frontmatter-ghost-wstunnel.service"
EGRESS_SERVICE="phantom-frontmatter-ghost-egress.service"

# ── Colors ───────────────────────────────────────────────────────

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' WHITE='' NC=''
fi

log() {
    echo -e "${2:-$NC}[$(date '+%H:%M:%S')] $1${NC}"
}

# ── UI ──────────────────────────────────────────────────────────

print_header() {
    echo -e "${CYAN}"
    echo "██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗"
    echo "██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║"
    echo "██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║"
    echo "██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║"
    echo "██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║"
    echo "╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝"
    echo -e "${NC}"
    echo -e "${CYAN}Phantom-WG Frontmatter — Uninstall${NC}"
    echo -e "${WHITE}Copyright (c) 2025 Rıza Emre ARAS${NC}"
    echo ""
}

# ── Pre-flight ──────────────────────────────────────────────────

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR: This script must be run as root (use sudo)" "$RED"
        exit 1
    fi
}

confirm() {
    if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
        return 0
    fi

    echo -e "${YELLOW}This will remove:${NC}"
    echo -e "  ${WHITE}• ${INSTALL_DIR}${NC}"
    echo -e "  ${WHITE}• ${BIN_LINK}${NC}"
    echo -e "  ${WHITE}• ${CERTBOT_LINK}${NC}"
    echo -e "  ${WHITE}• ${UNINSTALL_LINK}${NC}"
    echo -e "  ${WHITE}• systemd units (${WSTUNNEL_SERVICE}, ${EGRESS_SERVICE})${NC}"
    echo ""
    echo -e "${YELLOW}It will NOT touch:${NC}"
    echo -e "  ${WHITE}• The backend host (any WireGuard server / UDP endpoint)${NC}"
    echo -e "  ${WHITE}• The system-wide socat package${NC}"
    echo -e "  ${WHITE}• Any other services or data on this host${NC}"
    echo ""
    printf "Type 'UNINSTALL' to confirm: "
    read -r answer
    if [[ "$answer" != "UNINSTALL" ]]; then
        log "Aborted." "$RED"
        exit 1
    fi
}

# ── Cleanup steps ───────────────────────────────────────────────

stop_services() {
    log "Stopping systemd services..." "$CYAN"

    for svc in "$WSTUNNEL_SERVICE" "$EGRESS_SERVICE"; do
        if systemctl list-unit-files 2>/dev/null | grep -q "^${svc}"; then
            systemctl stop "$svc" 2>/dev/null || true
            systemctl disable "$svc" 2>/dev/null || true
            log "  stopped + disabled: $svc" "$GREEN"
        fi
    done
}

remove_service_units() {
    log "Removing systemd unit files..." "$CYAN"

    for svc in "$WSTUNNEL_SERVICE" "$EGRESS_SERVICE"; do
        local unit_path="/etc/systemd/system/${svc}"
        if [[ -f "$unit_path" ]]; then
            rm -f "$unit_path"
            log "  removed: $unit_path" "$GREEN"
        fi
    done

    systemctl daemon-reload 2>/dev/null || true
    systemctl reset-failed 2>/dev/null || true
}

kill_stray_processes() {
    # Kill any wstunnel or socat process still holding the loopback
    # port from a removed unit.
    for pattern in "wstunnel" "socat.*UDP4-LISTEN:.*bind=127\.0\.0\.1"; do
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            log "Killing stray process(es) matching: $pattern" "$CYAN"
            pkill -f "$pattern" 2>/dev/null || true
        fi
    done
}

remove_global_command() {
    log "Removing global command symlinks..." "$CYAN"
    for link in "$BIN_LINK" "$CERTBOT_LINK" "$UNINSTALL_LINK"; do
        if [[ -L "$link" ]] || [[ -f "$link" ]]; then
            rm -f "$link"
            log "  removed: $link" "$GREEN"
        fi
    done
}

remove_install_dir() {
    log "Removing installation directory..." "$CYAN"
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log "  removed: $INSTALL_DIR" "$GREEN"
    fi
}

# ── Verification ────────────────────────────────────────────────

verify_clean() {
    log "Verifying clean state..." "$CYAN"

    local issues=0

    [[ -d "$INSTALL_DIR" ]] && { log "  ! still present: $INSTALL_DIR" "$YELLOW"; ((issues++)); }
    [[ -e "$BIN_LINK" ]] && { log "  ! still present: $BIN_LINK" "$YELLOW"; ((issues++)); }
    [[ -e "$CERTBOT_LINK" ]] && { log "  ! still present: $CERTBOT_LINK" "$YELLOW"; ((issues++)); }
    [[ -e "$UNINSTALL_LINK" ]] && { log "  ! still present: $UNINSTALL_LINK" "$YELLOW"; ((issues++)); }

    for svc in "$WSTUNNEL_SERVICE" "$EGRESS_SERVICE"; do
        if [[ -f "/etc/systemd/system/${svc}" ]]; then
            log "  ! still present: /etc/systemd/system/${svc}" "$YELLOW"
            ((issues++))
        fi
    done

    if (( issues == 0 )); then
        log "Clean state verified" "$GREEN"
        return 0
    else
        log "$issues issue(s) remain — manual cleanup may be needed" "$YELLOW"
        return 1
    fi
}

# ── Footer ──────────────────────────────────────────────────────

print_footer() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Uninstall complete.${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Host is back to pre-install state."
    echo "Re-run the installer when ready:"
    echo ""
    echo "  sudo ./frontmatter-install.sh"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────

main() {
    print_header
    check_root
    confirm "${1:-}"

    stop_services
    kill_stray_processes
    remove_service_units
    remove_global_command
    remove_install_dir

    verify_clean || true

    print_footer
}

main "$@"
