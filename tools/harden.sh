#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
# Licensed under AGPL-3.0 - see LICENSE file for details
#
# Phantom-WG Frontmatter — Server Hardening
#
# One-shot hardening script for the front server. Run before
# frontmatter-install.sh on a fresh Debian/Ubuntu host.
#
# What this script does:
#   1. SSH: randomized port, key-only auth, hardened config
#   2. journald: volatile (RAM only, no persistent logs)
#   3. sysctl: network stack hardening
#   4. Core dumps disabled
#   5. Automatic security updates (unattended-upgrades)
#
# Usage:
#   sudo ./harden.sh

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' NC=''
fi

log() {
    echo -e "${2:-$NC}[$(date '+%H:%M:%S')] $1${NC}"
}

# ── Pre-flight ──────────────────────────────────────────────────

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR: This script must be run as root (use sudo)" "$RED"
        exit 1
    fi
}

# ── SSH Hardening ───────────────────────────────────────────────

harden_ssh() {
    log "Hardening SSH..." "$CYAN"

    local ssh_port
    ssh_port=$(shuf -i 10000-65000 -n 1)

    # shellcheck disable=SC2034
    local sshd_config="/etc/ssh/sshd_config"
    local drop_in_dir="/etc/ssh/sshd_config.d"
    local drop_in="${drop_in_dir}/00-phantom-harden.conf"

    mkdir -p "$drop_in_dir"

    cat > "$drop_in" <<EOF
Port ${ssh_port}
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
X11Forwarding no
MaxAuthTries 3
MaxSessions 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowAgentForwarding no
AllowTcpForwarding no
EOF

    # Verify config before restarting
    if sshd -t 2>/dev/null; then
        systemctl restart sshd
        log "SSH hardened — port: ${ssh_port}" "$GREEN"
    else
        rm -f "$drop_in"
        log "ERROR: sshd config test failed, reverted" "$RED"
        exit 1
    fi

    # Write port to a file for operator reference
    echo "$ssh_port" > /etc/ssh/.phantom-ssh-port
    chmod 600 /etc/ssh/.phantom-ssh-port

    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  SSH PORT: ${ssh_port}                           ║${NC}"
    echo -e "${YELLOW}║                                                  ║${NC}"
    echo -e "${YELLOW}║  Save this port before closing your session.     ║${NC}"
    echo -e "${YELLOW}║  Reconnect: ssh -p ${ssh_port} root@<host>       ║${NC}"
    echo -e "${YELLOW}║                                                  ║${NC}"
    echo -e "${YELLOW}║  Stored at: /etc/ssh/.phantom-ssh-port           ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── journald Volatile ───────────────────────────────────────────

harden_journald() {
    log "Configuring journald (volatile)..." "$CYAN"

    local drop_in_dir="/etc/systemd/journald.conf.d"
    mkdir -p "$drop_in_dir"

    cat > "${drop_in_dir}/00-phantom-volatile.conf" <<EOF
[Journal]
Storage=volatile
RuntimeMaxUse=64M
EOF

    systemctl restart systemd-journald

    # Remove persistent journal if it exists
    if [[ -d /var/log/journal ]]; then
        rm -rf /var/log/journal
        log "Removed /var/log/journal (persistent logs)" "$GREEN"
    fi

    log "journald: volatile, 64M max, persistent logs removed" "$GREEN"
}

# ── sysctl Hardening ───────────────────────────────────────────

harden_sysctl() {
    log "Applying sysctl hardening..." "$CYAN"

    cat > /etc/sysctl.d/90-phantom-harden.conf <<EOF
# ICMP
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Reverse path filtering
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Source routing disabled
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# ICMP redirects disabled
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Shared memory hardening
kernel.randomize_va_space = 2
EOF

    sysctl --system > /dev/null 2>&1

    log "sysctl hardened" "$GREEN"
}

# ── Core Dumps ──────────────────────────────────────────────────

disable_core_dumps() {
    log "Disabling core dumps..." "$CYAN"

    cat > /etc/security/limits.d/00-phantom-nocore.conf <<EOF
* hard core 0
* soft core 0
EOF

    if [[ -d /etc/sysctl.d ]]; then
        echo "fs.suid_dumpable = 0" > /etc/sysctl.d/91-phantom-nocore.conf
        sysctl -p /etc/sysctl.d/91-phantom-nocore.conf > /dev/null 2>&1
    fi

    log "Core dumps disabled" "$GREEN"
}

# ── Automatic Security Updates ──────────────────────────────────

setup_auto_updates() {
    log "Configuring automatic security updates..." "$CYAN"

    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y --no-install-recommends unattended-upgrades > /dev/null 2>&1

    cat > /etc/apt/apt.conf.d/50-phantom-auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

    log "Automatic security updates enabled" "$GREEN"
}

# ── Summary ─────────────────────────────────────────────────────

print_summary() {
    local ssh_port
    ssh_port=$(cat /etc/ssh/.phantom-ssh-port 2>/dev/null || echo "unknown")

    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Hardening complete.${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  SSH port:        ${ssh_port}"
    echo "  SSH auth:        key-only (password disabled)"
    echo "  journald:        volatile (RAM, 64M limit)"
    echo "  sysctl:          network stack hardened"
    echo "  Core dumps:      disabled"
    echo "  Auto-updates:    security patches"
    echo ""
    echo "  Next: install frontmatter"
    echo "    sudo ./frontmatter-install.sh"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────

main() {
    check_root
    harden_ssh
    harden_journald
    harden_sysctl
    disable_core_dumps
    setup_auto_updates
    print_summary
}

main "$@"
