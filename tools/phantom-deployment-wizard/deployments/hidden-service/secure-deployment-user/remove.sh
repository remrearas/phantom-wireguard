#!/bin/bash
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="/var/log/secure-deployment-removal.log"

# Fixed configuration (must match create.sh)
DEPLOY_USER="deployment-user"
DEPLOY_HOME="/home/${DEPLOY_USER}"
CHROOT_PATH="/securepath"
SECRETS_DIR="/opt/deployment-secrets"
DEPLOYMENT_DIR="/tmp/deployment"
DEPLOYMENT_LOCK="/var/lock/deployment.lock"

# ============================================================================
# HELPERS
# ============================================================================

log() {
    echo -e "${2:-$NC}[$(date '+%H:%M:%S')] $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}" 2>/dev/null || true
}

error_exit() {
    log "ERROR: $1" "$RED"
    exit 1
}

check_root() {
    [[ $EUID -eq 0 ]] || error_exit "This script must be run as root"
}

print_header() {
    clear
    echo -e "${RED}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║     SECURE DEPLOYMENT USER REMOVAL                             ║"
    echo "║     Complete cleanup of deployment-user                        ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

confirm_removal() {
    echo ""
    echo -e "${YELLOW}WARNING: This will PERMANENTLY remove:${NC}"
    echo -e "  - User: ${RED}${DEPLOY_USER}${NC}"
    echo -e "  - Chroot: ${RED}${CHROOT_PATH}${NC}"
    echo -e "  - Secrets: ${RED}${SECRETS_DIR}${NC}"
    echo -e "  - Systemd services"
    echo -e "  - AppArmor profile"
    echo -e "  - SSH configuration"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Removal cancelled by user" "$YELLOW"
        exit 0
    fi
}

# ============================================================================
# REMOVAL FUNCTIONS
# ============================================================================

check_user_exists() {
    if ! id -u "${DEPLOY_USER}" &>/dev/null; then
        echo ""
        log "User '${DEPLOY_USER}' does not exist!" "$YELLOW"
        echo ""
        echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  Deployment user not found - nothing to remove                 ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 0
    fi
}

stop_watcher_service() {
    log "Stopping deployment watcher..." "$BLUE"

    # Stop and disable path unit
    if systemctl is-active deployment-watcher.path &>/dev/null; then
        systemctl stop deployment-watcher.path 2>/dev/null || true
        log "✓ Stopped deployment-watcher.path" "$GREEN"
    fi

    if systemctl is-enabled deployment-watcher.path &>/dev/null; then
        systemctl disable deployment-watcher.path 2>/dev/null || true
        log "✓ Disabled deployment-watcher.path" "$GREEN"
    fi

    # Stop service unit (if running)
    if systemctl is-active deployment-watcher.service &>/dev/null; then
        systemctl stop deployment-watcher.service 2>/dev/null || true
        log "✓ Stopped deployment-watcher.service" "$GREEN"
    fi

    # Remove systemd units
    rm -f /etc/systemd/system/deployment-watcher.path
    rm -f /etc/systemd/system/deployment-watcher.service
    log "✓ Removed watcher systemd units" "$GREEN"

    # Remove watcher script
    rm -f /usr/local/bin/deployment-watcher.py
    log "✓ Removed watcher script" "$GREEN"

    # Reload systemd
    systemctl daemon-reload
    log "✓ Reloaded systemd" "$GREEN"
}

stop_remover_service() {
    log "Stopping deployment remover..." "$BLUE"

    # Stop and disable path unit
    if systemctl is-active deployment-remover.path &>/dev/null; then
        systemctl stop deployment-remover.path 2>/dev/null || true
        log "✓ Stopped deployment-remover.path" "$GREEN"
    fi

    if systemctl is-enabled deployment-remover.path &>/dev/null; then
        systemctl disable deployment-remover.path 2>/dev/null || true
        log "✓ Disabled deployment-remover.path" "$GREEN"
    fi

    # Stop service unit (if running)
    if systemctl is-active deployment-remover.service &>/dev/null; then
        systemctl stop deployment-remover.service 2>/dev/null || true
        log "✓ Stopped deployment-remover.service" "$GREEN"
    fi

    # Remove systemd units
    rm -f /etc/systemd/system/deployment-remover.path
    rm -f /etc/systemd/system/deployment-remover.service
    log "✓ Removed remover systemd units" "$GREEN"

    # Reload systemd
    systemctl daemon-reload
    log "✓ Reloaded systemd" "$GREEN"
}

remove_apparmor_profile() {
    log "Removing AppArmor profile..." "$BLUE"

    # Unload profile
    if aa-status 2>/dev/null | grep -q "${DEPLOY_USER}"; then
        aa-disable "${DEPLOY_USER}" 2>/dev/null || true
        apparmor_parser -R "/etc/apparmor.d/${DEPLOY_USER}" 2>/dev/null || true
        log "✓ Unloaded AppArmor profile" "$GREEN"
    fi

    # Remove profile file
    rm -f "/etc/apparmor.d/${DEPLOY_USER}"
    log "✓ Removed profile file" "$GREEN"

    # Remove wrapper script
    rm -f "/usr/local/bin/${DEPLOY_USER}-shell"
    log "✓ Removed wrapper script" "$GREEN"
}

remove_user() {
    log "Removing user..." "$BLUE"

    # Kill all user processes
    if pgrep -u "${DEPLOY_USER}" &>/dev/null; then
        pkill -9 -u "${DEPLOY_USER}" 2>/dev/null || true
        sleep 1
        log "✓ Killed user processes" "$GREEN"
    fi

    # Remove user and home directory
    userdel -r "${DEPLOY_USER}" 2>/dev/null || true
    log "✓ Removed user: ${DEPLOY_USER}" "$GREEN"

    # Ensure home directory is removed (in case userdel -r failed)
    if [[ -d "${DEPLOY_HOME}" ]]; then
        rm -rf "${DEPLOY_HOME}"
        log "✓ Removed home directory" "$GREEN"
    fi
}

remove_directories() {
    log "Removing directories..." "$BLUE"

    # Remove chroot path
    if [[ -d "${CHROOT_PATH}" ]]; then
        rm -rf "${CHROOT_PATH}"
        log "✓ Removed: ${CHROOT_PATH}" "$GREEN"
    fi

    # Remove secrets directory
    if [[ -d "${SECRETS_DIR}" ]]; then
        rm -rf "${SECRETS_DIR}"
        log "✓ Removed: ${SECRETS_DIR}" "$GREEN"
    fi

    # Remove deployment directory
    if [[ -d "${DEPLOYMENT_DIR}" ]]; then
        rm -rf "${DEPLOYMENT_DIR}"
        log "✓ Removed: ${DEPLOYMENT_DIR}" "$GREEN"
    fi

    # Remove deployment lock
    if [[ -f "${DEPLOYMENT_LOCK}" ]]; then
        rm -f "${DEPLOYMENT_LOCK}"
        log "✓ Removed: ${DEPLOYMENT_LOCK}" "$GREEN"
    fi
}

remove_ssh_config() {
    log "Removing SSH configuration..." "$BLUE"

    local config_file="/etc/ssh/sshd_config.d/deployment-hardening.conf"

    if [[ -f "${config_file}" ]]; then
        rm -f "${config_file}"
        log "✓ Removed SSH hardening config" "$GREEN"
        log "Restart SSH: systemctl restart sshd" "$YELLOW"
    else
        log "SSH config not found (already removed)" "$CYAN"
    fi
}

cleanup_logs() {
    log "Cleaning up logs..." "$BLUE"

    # Remove deployment logs
    if [[ -f "/var/log/deployment.log" ]]; then
        rm -f /var/log/deployment.log
        log "✓ Removed deployment.log" "$GREEN"
    fi

    # Keep setup/removal logs for reference
    log "Setup/removal logs kept in /var/log/" "$CYAN"
}

# ============================================================================
# VERIFICATION
# ============================================================================

verify_removal() {
    log "Verifying removal..." "$BLUE"

    local errors=0

    # Check user removed
    if id -u "${DEPLOY_USER}" &>/dev/null; then
        log "✗ User still exists" "$RED"
        ((errors++))
    else
        log "✓ User removed" "$GREEN"
    fi

    # Check chroot removed
    if [[ -d "${CHROOT_PATH}" ]]; then
        log "✗ Chroot still exists" "$RED"
        ((errors++))
    else
        log "✓ Chroot removed" "$GREEN"
    fi

    # Check secrets removed
    if [[ -d "${SECRETS_DIR}" ]]; then
        log "✗ Secrets directory still exists" "$RED"
        ((errors++))
    else
        log "✓ Secrets removed" "$GREEN"
    fi

    # Check AppArmor unloaded
    if aa-status 2>/dev/null | grep -q "${DEPLOY_USER}"; then
        log "✗ AppArmor profile still loaded" "$RED"
        ((errors++))
    else
        log "✓ AppArmor profile removed" "$GREEN"
    fi

    # Check watcher stopped
    if systemctl is-active deployment-watcher.path &>/dev/null; then
        log "✗ Watcher still active" "$RED"
        ((errors++))
    else
        log "✓ Watcher stopped" "$GREEN"
    fi

    if [[ $errors -eq 0 ]]; then
        log "All verification checks passed!" "$GREEN"
        return 0
    else
        log "Verification failed: $errors errors" "$RED"
        return 1
    fi
}

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

display_results() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}║     DEPLOYMENT USER REMOVED SUCCESSFULLY!                      ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Removed Components:${NC}"
    echo -e "  User:          ${GREEN}✓${NC} ${DEPLOY_USER}"
    echo -e "  Chroot:        ${GREEN}✓${NC} ${CHROOT_PATH}"
    echo -e "  Secrets:       ${GREEN}✓${NC} ${SECRETS_DIR}"
    echo -e "  AppArmor:      ${GREEN}✓${NC} Profile unloaded"
    echo -e "  Systemd:       ${GREEN}✓${NC} Services removed"
    echo -e "  SSH Config:    ${GREEN}✓${NC} Hardening removed"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "  Restart SSH:   ${YELLOW}systemctl restart sshd${NC}"
    echo -e "  Recreate:      ${YELLOW}./create.sh --gpg-pubkey <key.asc>${NC}"
    echo ""
    echo -e "${CYAN}Logs:${NC}"
    echo -e "  Removal log:   ${YELLOW}${LOG_FILE}${NC}"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header
    check_root
    check_user_exists
    confirm_removal

    log "Starting deployment user removal..." "$CYAN"
    echo ""

    stop_watcher_service
    stop_remover_service
    remove_apparmor_profile
    remove_user
    remove_directories
    remove_ssh_config
    cleanup_logs

    echo ""
    verify_removal

    display_results

    log "Removal completed successfully!" "$GREEN"
}

main "$@"
