#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS
# Licensed under AGPL-3.0 - see LICENSE file for details
# Third-party licenses - see THIRD_PARTY_LICENSES file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.
#
# Phantom-WG Frontmatter Installation Script
#
# Sets up the frontmatter entry-point layer on the front server. Does NOT
# install or touch any backend components — frontmatter only forwards UDP
# to a configured backend (any WireGuard server or arbitrary UDP endpoint).
#
# Installation Flow:
#   1. System checks (OS, root privileges)
#   2. Install system dependencies (Python, socat, openssl)
#   3. Create directory structure (/opt/phantom-frontmatter)
#   4. Copy source files
#   5. Create Python virtual environment (.phantom-venv)
#   6. Install Python dependencies
#   7. Create global command (frontmatter-api)
#   8. Install systemd service templates
#   9. Verify installation and print next steps

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────

INSTALL_DIR="/opt/phantom-frontmatter"
VENV_DIR="${INSTALL_DIR}/.phantom-venv"
BIN_LINK="/usr/local/bin/frontmatter-api"
UNINSTALL_LINK="/usr/local/sbin/frontmatter-uninstall"

SUPPORTED_DEBIAN_VERSIONS=("12" "13")
SUPPORTED_UBUNTU_VERSIONS=("22.04" "24.04")

# Source layout (where this script lives before install)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    echo -e "${CYAN}Phantom-WG Frontmatter — Installation${NC}"
    echo -e "${WHITE}Copyright (c) 2025 Rıza Emre ARAS${NC}"
    echo -e "${WHITE}Licensed under AGPL-3.0${NC}"
    echo ""
}

# ── Pre-flight checks ───────────────────────────────────────────

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR: This script must be run as root (use sudo)" "$RED"
        exit 1
    fi
    log "Root privileges confirmed" "$GREEN"
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        log "ERROR: Cannot determine OS (missing /etc/os-release)" "$RED"
        exit 1
    fi

    # shellcheck disable=SC1091
    source /etc/os-release
    OS_ID="$ID"
    OS_VERSION_ID="$VERSION_ID"

    local supported=0
    case "$OS_ID" in
        debian)
            for v in "${SUPPORTED_DEBIAN_VERSIONS[@]}"; do
                [[ "$OS_VERSION_ID" == "$v" ]] && supported=1
            done
            ;;
        ubuntu)
            for v in "${SUPPORTED_UBUNTU_VERSIONS[@]}"; do
                [[ "$OS_VERSION_ID" == "$v" ]] && supported=1
            done
            ;;
    esac

    if [[ $supported -eq 0 ]]; then
        log "WARNING: Untested OS: ${PRETTY_NAME:-$OS_ID $OS_VERSION_ID}" "$YELLOW"
        log "Supported: Debian ${SUPPORTED_DEBIAN_VERSIONS[*]}, Ubuntu ${SUPPORTED_UBUNTU_VERSIONS[*]}" "$YELLOW"
        printf "Continue anyway? [y/N]: "
        read -r confirm
        [[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 1
    else
        log "OS check passed: ${PRETTY_NAME:-$OS_ID $OS_VERSION_ID}" "$GREEN"
    fi
}

# ── System dependencies ────────────────────────────────────────

install_system_deps() {
    log "Installing system dependencies..." "$CYAN"

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        socat \
        openssl \
        ca-certificates \
        > /dev/null

    log "System dependencies installed" "$GREEN"
}

# ── Directory setup ───────────────────────────────────────────

create_directories() {
    log "Creating installation directories..." "$CYAN"

    mkdir -p "${INSTALL_DIR}/config"
    mkdir -p "${INSTALL_DIR}/data"
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/secrets"
    mkdir -p "${INSTALL_DIR}/bin"

    chmod 755 "${INSTALL_DIR}"
    chmod 755 "${INSTALL_DIR}/config"
    chmod 755 "${INSTALL_DIR}/data"
    chmod 755 "${INSTALL_DIR}/logs"
    chmod 700 "${INSTALL_DIR}/secrets"
    chmod 755 "${INSTALL_DIR}/bin"

    log "Directory structure created at ${INSTALL_DIR}" "$GREEN"
}

copy_sources() {
    log "Copying source files..." "$CYAN"

    # Python package
    rm -rf "${INSTALL_DIR}/phantom_frontmatter"
    cp -r "${SCRIPT_DIR}/phantom_frontmatter" "${INSTALL_DIR}/phantom_frontmatter"

    # Requirements
    cp "${SCRIPT_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"

    # Meta files (optional — skip if missing)
    for f in LICENSE THIRD_PARTY_LICENSES README.md README_TR.md SECURITY.md ARCHITECTURE ARCHITECTURE_TR; do
        if [[ -f "${SCRIPT_DIR}/${f}" ]]; then
            cp "${SCRIPT_DIR}/${f}" "${INSTALL_DIR}/${f}"
        fi
    done

    log "Source files copied" "$GREEN"
}

# ── Python environment ───────────────────────────────────────

create_venv() {
    log "Creating Python virtual environment..." "$CYAN"

    if [[ -d "$VENV_DIR" ]]; then
        rm -rf "$VENV_DIR"
    fi

    python3 -m venv "$VENV_DIR"
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip

    log "Virtual environment created at ${VENV_DIR}" "$GREEN"
}

install_python_deps() {
    log "Installing Python dependencies..." "$CYAN"

    # Only run pip install when requirements.txt has at least one
    # non-comment line.
    if [[ -s "${INSTALL_DIR}/requirements.txt" ]] && \
       grep -qvE '^\s*(#|$)' "${INSTALL_DIR}/requirements.txt"; then
        "${VENV_DIR}/bin/pip" install --quiet -r "${INSTALL_DIR}/requirements.txt"
        log "Python dependencies installed" "$GREEN"
    else
        log "No Python dependencies to install (stdlib only)" "$GREEN"
    fi
}

# ── Global command ───────────────────────────────────────────

create_global_command() {
    log "Creating global commands..." "$CYAN"

    local api_script="${INSTALL_DIR}/phantom_frontmatter/bin/frontmatter-api.py"
    local uninstall_script="${INSTALL_DIR}/phantom_frontmatter/frontmatter-uninstall.sh"

    chmod +x "$api_script"
    chmod +x "$uninstall_script"

    # Re-write shebang to point at the venv we just created
    sed -i "1s|.*|#!${VENV_DIR}/bin/python3|" "$api_script"

    # Symlinks
    ln -sf "$api_script" "$BIN_LINK"
    ln -sf "$uninstall_script" "$UNINSTALL_LINK"

    log "Global command: $BIN_LINK" "$GREEN"
    log "Uninstall:      $UNINSTALL_LINK" "$GREEN"
}

# ── Verification ─────────────────────────────────────────────

verify_installation() {
    log "Verifying installation..." "$CYAN"

    # Test import
    if ! "${VENV_DIR}/bin/python3" -c "
import sys
sys.path.insert(0, '${INSTALL_DIR}')
from phantom_frontmatter import __version__
print(f'phantom_frontmatter {__version__}')
" > /dev/null 2>&1; then
        log "ERROR: Package import failed" "$RED"
        exit 1
    fi

    # Test CLI
    if ! "$BIN_LINK" --version > /dev/null 2>&1; then
        log "ERROR: frontmatter-api CLI failed" "$RED"
        exit 1
    fi

    log "Installation verified" "$GREEN"
}

# ── Next steps ───────────────────────────────────────────────

print_next_steps() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installation complete.${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Install location: ${INSTALL_DIR}"
    echo "Python venv:      ${VENV_DIR}"
    echo "Global command:   ${BIN_LINK}"
    echo "Uninstall:        ${UNINSTALL_LINK}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "  Phantom-WG Frontmatter is a Ghost Mode entry point for"
    echo "  any WireGuard server (or any UDP endpoint). The client"
    echo "  sees only the front; the backend address lives exclusively"
    echo "  on this host inside one rendered systemd unit and one"
    echo "  SQLite row."
    echo ""
    echo "  1. Bootstrap the host (one-shot):"
    echo "     frontmatter-api setup init backend=<BACKEND_IP[:PORT]>"
    echo ""
    echo "     This generates a self-signed TLS cert, downloads the"
    echo "     pinned wstunnel binary, generates a fresh secret, and"
    echo "     renders both ghost systemd units. It does NOT start"
    echo "     any service yet."
    echo ""
    echo "  2. Bring the data path up:"
    echo "     frontmatter-api ghost start"
    echo ""
    echo "     This enables + starts phantom-frontmatter-ghost-wstunnel,"
    echo "     which pulls in phantom-frontmatter-ghost-egress via"
    echo "     systemd Requires=/After= dependencies."
    echo ""
    echo "  Verify:"
    echo "     frontmatter-api setup status"
    echo "     frontmatter-api ghost status"
    echo ""
    echo "  Get the client [Wstunnel] block for Ghost Mode:"
    echo "     frontmatter-api ghost client_config | jq -r '.data.wstunnel_block'"
    echo ""
    echo "  Replace <FRONTMATTER-PUBLIC-IP> in the snippet with this"
    echo "  host's public IP (or hostname) before pasting it into a"
    echo "  client .conf — frontmatter never queries an external IP"
    echo "  service on its own."
    echo ""
    echo "  Reset (full re-init): frontmatter-api setup clean yes=true"
    echo ""
    echo "Backend note: No changes required on the backend host."
    echo "  Whatever WireGuard server (or other UDP endpoint) you point"
    echo "  frontmatter at keeps running unchanged — frontmatter just"
    echo "  forwards datagrams to it from the front host's own outbound"
    echo "  socket, hidden from every client artifact."
    echo ""
}

# ── Main ─────────────────────────────────────────────────────

main() {
    print_header
    check_root
    check_os
    install_system_deps
    create_directories
    copy_sources
    create_venv
    install_python_deps
    create_global_command
    verify_installation
    print_next_steps
}

main "$@"
