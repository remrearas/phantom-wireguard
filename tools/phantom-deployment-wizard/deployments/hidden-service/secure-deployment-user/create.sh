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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

LOG_FILE="/var/log/secure-deployment-setup.log"

# Fixed configuration
DEPLOY_USER="deployment-user"
DEPLOY_HOME="/home/${DEPLOY_USER}"
CHROOT_PATH="/securepath"
QUARANTINE_DIR="/securepath/incoming"
SECRETS_DIR="/opt/deployment-secrets"
GPG_HOME="${SECRETS_DIR}/gpg"
GPG_KEYRING="${SECRETS_DIR}/deployment.asc"

# Variables
GPG_PUBKEY_FILE=""

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
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║     SECURE DEPLOYMENT USER SETUP                               ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_usage() {
    cat << 'EOF'
Usage: ./create.sh --gpg-pubkey FILE

Arguments:
  --gpg-pubkey FILE      Path to GPG public key (.asc)

Creates:
  • User: deployment-user
  • Chroot: /securepath/
  • Upload: /securepath/incoming/ (blind upload)
  • Deployment: Deployment script based (run.sh)

Security Model:
  deployment-user CAN:
    • Upload files to /securepath/incoming/ (write-only)

  deployment-user CANNOT:
    • Read uploaded files (blind upload)
    • Execute any binaries
    • Escape chroot jail

  Root Watcher Service:
    • Monitors /securepath/incoming/
    • Verifies GPG signature
    • Extracts to /tmp/deployment/
    • Executes run.sh
    • Logs everything

Example:
  ./create.sh --gpg-pubkey deployment.asc
EOF
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

parse_arguments() {
    log "Debug: Received $# arguments: $*" "$CYAN"

    [[ $# -eq 0 ]] && { show_usage; exit 0; }

    while [[ $# -gt 0 ]]; do
        log "Debug: Processing '$1'" "$CYAN"
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --gpg-pubkey)
                if [[ -z "${2:-}" ]]; then
                    error_exit "Missing value for --gpg-pubkey"
                fi
                log "Debug: GPG pubkey file: $2" "$CYAN"
                GPG_PUBKEY_FILE="$2"
                shift 2
                ;;
            *)
                error_exit "Unknown argument: $1"
                ;;
        esac
    done

    log "Debug: Final GPG_PUBKEY_FILE='$GPG_PUBKEY_FILE'" "$CYAN"

    if [[ -z "$GPG_PUBKEY_FILE" ]]; then
        error_exit "Missing: --gpg-pubkey FILE"
    fi
}

# ============================================================================
# VALIDATION
# ============================================================================

check_existing_user() {
    if id -u "${DEPLOY_USER}" &>/dev/null; then
        echo ""
        log "User '${DEPLOY_USER}' already exists!" "$YELLOW"
        echo ""
        echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  Deployment user already configured                            ║${NC}"
        echo -e "${YELLOW}║  Run ./remove.sh first to recreate                             ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        exit 0
    fi
}

validate_gpg_pubkey() {
    log "Validating GPG public key..." "$BLUE"

    [[ -f "$GPG_PUBKEY_FILE" ]] || error_exit "GPG key file not found: $GPG_PUBKEY_FILE"
    [[ -s "$GPG_PUBKEY_FILE" ]] || error_exit "GPG key file is empty"
    grep -q "BEGIN PGP PUBLIC KEY BLOCK" "$GPG_PUBKEY_FILE" || \
        error_exit "Invalid GPG key format"

    # Import test
    local temp_gpghome="/tmp/gpg-test-$$"
    mkdir -p "$temp_gpghome"
    chmod 700 "$temp_gpghome"

    log "Testing GPG key import..." "$CYAN"
    if ! gpg --homedir "$temp_gpghome" --import "$GPG_PUBKEY_FILE" 2>&1; then
        rm -rf "$temp_gpghome"
        error_exit "GPG key import test failed"
    fi

    local key_id
    key_id=$(gpg --homedir "$temp_gpghome" --list-keys --with-colons 2>/dev/null | \
             grep "^pub" | head -1 | cut -d: -f5)

    [[ -n "$key_id" ]] && log "GPG Key ID: $key_id" "$CYAN"

    rm -rf "$temp_gpghome"
    log "GPG public key: OK" "$GREEN"
}

# ============================================================================
# SYSTEM CHECKS
# ============================================================================

check_system() {
    log "Checking system compatibility..." "$BLUE"

    # OS check
    [[ -f /etc/os-release ]] || error_exit "Cannot detect OS"
    source /etc/os-release
    [[ "$ID" == "debian" || "$ID" == "ubuntu" ]] || \
        error_exit "Only Debian/Ubuntu supported (detected: $ID)"

    log "OS: $PRETTY_NAME" "$GREEN"

    # AppArmor
    [[ -d /sys/kernel/security/apparmor ]] || error_exit "AppArmor not supported"
    log "AppArmor: OK" "$GREEN"

    # systemd
    command -v systemctl &>/dev/null || error_exit "systemd required"
    log "systemd: OK" "$GREEN"

    # Python3
    command -v python3 &>/dev/null || error_exit "python3 required"
    log "Python3: OK" "$GREEN"
}

install_dependencies() {
    log "Installing dependencies..." "$BLUE"
    echo ""

    log "Updating package lists..." "$CYAN"
    apt-get update || error_exit "apt-get update failed"
    echo ""

    local packages=("apparmor" "apparmor-utils" "gnupg" "unzip" "python3" "python3-gnupg" "lsof")

    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            log "Installing $pkg..." "$YELLOW"
            DEBIAN_FRONTEND=noninteractive apt-get install -y "$pkg" || \
                error_exit "Failed to install $pkg"
            echo ""
        else
            log "$pkg: already installed" "$CYAN"
        fi
    done

    log "Enabling AppArmor service..." "$CYAN"
    systemctl enable apparmor || true
    systemctl start apparmor || true

    echo ""
    log "Dependencies: OK" "$GREEN"
}

# ============================================================================
# USER SETUP
# ============================================================================

create_user() {
    log "Creating user: ${DEPLOY_USER}..." "$BLUE"

    useradd -m -s /bin/bash -c "Deployment User" "${DEPLOY_USER}" || \
        error_exit "Failed to create user"

    # SSH directory
    mkdir -p "${DEPLOY_HOME}/.ssh"
    chmod 700 "${DEPLOY_HOME}/.ssh"

    # Generate SSH key
    local ssh_key="${DEPLOY_HOME}/.ssh/id_ed25519"
    log "Generating SSH key..." "$YELLOW"
    ssh-keygen -t ed25519 -f "$ssh_key" -N "" \
        -C "${DEPLOY_USER}@deployment"
    chmod 600 "$ssh_key"
    chmod 644 "${ssh_key}.pub"

    # Authorized keys
    cat "${ssh_key}.pub" > "${DEPLOY_HOME}/.ssh/authorized_keys"
    chmod 600 "${DEPLOY_HOME}/.ssh/authorized_keys"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_HOME}/.ssh"

    log "User created: OK" "$GREEN"
}

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================

setup_directories() {
    log "Setting up directories..." "$BLUE"

    # Chroot jail base - MUST be root:root with 755 for SSH chroot
    mkdir -p "$CHROOT_PATH"
    chown root:root "$CHROOT_PATH"
    chmod 755 "$CHROOT_PATH"

    # Quarantine (blind upload zone)
    # - Owner: root (chroot requirement)
    # - Group: deployment-user (upload access)
    # - Permissions: 730 (rwx-wx---)
    #   * root: full access (rwx)
    #   * deployment-user: write+execute only, NO READ (wx)
    #   * others: no access (---)
    # This enforces blind upload at filesystem level
    mkdir -p "$QUARANTINE_DIR"
    chown root:${DEPLOY_USER} "$QUARANTINE_DIR"
    chmod 730 "$QUARANTINE_DIR"

    # Output directory (safe deployment status)
    # - Owner: root (watcher yazacak)
    # - Group: deployment-user (read erişimi için)
    # - Permissions: 750 (rwxr-x---)
    #   * root: full access (rwx)
    #   * deployment-user: read+execute (rx) - SFTP ile okuyabilir
    #   * others: no access (---)
    OUTPUT_DIR="$CHROOT_PATH/outputs"
    mkdir -p "$OUTPUT_DIR"
    chown root:${DEPLOY_USER} "$OUTPUT_DIR"
    chmod 750 "$OUTPUT_DIR"

    log "Chroot: $CHROOT_PATH (root:root, 755)" "$CYAN"
    log "Quarantine: $QUARANTINE_DIR (root:${DEPLOY_USER}, 730 - BLIND UPLOAD)" "$CYAN"
    log "Outputs: $OUTPUT_DIR (root:${DEPLOY_USER}, 750 - READ ONLY)" "$CYAN"

    # Secrets directory
    mkdir -p "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR"

    log "Directories: OK" "$GREEN"
}

# ============================================================================
# GPG SETUP
# ============================================================================

setup_gpg() {
    log "Setting up GPG verification..." "$BLUE"

    # Create GPG home directory
    mkdir -p "$GPG_HOME"
    chmod 700 "$GPG_HOME"

    # Copy public key for reference
    cp "$GPG_PUBKEY_FILE" "$GPG_KEYRING"
    chmod 644 "$GPG_KEYRING"

    # Import GPG public key into GPG home directory
    log "Importing GPG key to deployment GPG home..." "$CYAN"
    if ! gpg --homedir "$GPG_HOME" --import "$GPG_KEYRING" 2>&1; then
        error_exit "Failed to import GPG public key into GPG home"
    fi

    # List imported keys for verification
    local key_id
    key_id=$(gpg --homedir "$GPG_HOME" --list-keys --with-colons 2>/dev/null | \
             grep "^pub" | head -1 | cut -d: -f5)

    [[ -n "$key_id" ]] && log "GPG Key ID: $key_id imported into GPG home" "$CYAN"

    log "GPG keyring installed: $GPG_KEYRING" "$GREEN"
    log "GPG home initialized: $GPG_HOME" "$GREEN"
}

# ============================================================================
# APPARMOR SETUP
# ============================================================================

setup_apparmor_activation() {
    log "Setting up AppArmor activation wrapper..." "$BLUE"

    cat > "/usr/local/bin/${DEPLOY_USER}-shell" << EOF
#!/bin/bash
# Force AppArmor profile on SSH login
exec /usr/bin/aa-exec -p ${DEPLOY_USER} -- /bin/bash
EOF

    chmod 755 "/usr/local/bin/${DEPLOY_USER}-shell"
    usermod -s "/usr/local/bin/${DEPLOY_USER}-shell" "${DEPLOY_USER}"

    log "AppArmor wrapper: OK" "$GREEN"
}

install_apparmor_profile() {
    log "Installing AppArmor profile..." "$BLUE"

    local profile_template="${SCRIPT_DIR}/profiles/apparmor.profile"
    [[ -f "$profile_template" ]] || error_exit "Profile not found: $profile_template"

    local profile_path="/etc/apparmor.d/${DEPLOY_USER}"

    # Install profile
    sed "s/{{USERNAME}}/${DEPLOY_USER}/g" "$profile_template" > "$profile_path"

    # Load profile
    log "Loading AppArmor profile..." "$CYAN"
    apparmor_parser -r "$profile_path" || error_exit "Failed to load AppArmor profile"
    log "Enforcing AppArmor profile..." "$CYAN"
    aa-enforce "${DEPLOY_USER}" || true

    log "AppArmor profile: ENFORCED" "$GREEN"
}

# ============================================================================
# WATCHER SERVICE
# ============================================================================

install_watcher_service() {
    log "Installing deployment watcher..." "$BLUE"

    # Copy watcher script
    local watcher_script="${SCRIPT_DIR}/scripts/deployment-watcher.py"
    [[ -f "$watcher_script" ]] || error_exit "Watcher script not found: $watcher_script"

    cp "$watcher_script" /usr/local/bin/deployment-watcher.py
    chmod 755 /usr/local/bin/deployment-watcher.py

    # Copy systemd units
    local path_unit="${SCRIPT_DIR}/systemd/deployment-watcher.path"
    local service_unit="${SCRIPT_DIR}/systemd/deployment-watcher.service"

    [[ -f "$path_unit" ]] || error_exit "Path unit not found: $path_unit"
    [[ -f "$service_unit" ]] || error_exit "Service unit not found: $service_unit"

    cp "$path_unit" /etc/systemd/system/
    cp "$service_unit" /etc/systemd/system/

    # Enable and start
    log "Reloading systemd daemon..." "$CYAN"
    systemctl daemon-reload

    log "Enabling deployment-watcher.path..." "$CYAN"
    systemctl enable deployment-watcher.path

    log "Starting deployment-watcher.path..." "$CYAN"
    systemctl start deployment-watcher.path

    log "Deployment watcher: ACTIVE" "$GREEN"
}

install_remover_service() {
    log "Installing deployment remover..." "$BLUE"

    # Copy systemd units
    local path_unit="${SCRIPT_DIR}/systemd/deployment-remover.path"
    local service_unit="${SCRIPT_DIR}/systemd/deployment-remover.service"

    [[ -f "$path_unit" ]] || error_exit "Path unit not found: $path_unit"
    [[ -f "$service_unit" ]] || error_exit "Service unit not found: $service_unit"

    cp "$path_unit" /etc/systemd/system/
    cp "$service_unit" /etc/systemd/system/

    # Enable and start
    log "Reloading systemd daemon..." "$CYAN"
    systemctl daemon-reload

    log "Enabling deployment-remover.path..." "$CYAN"
    systemctl enable deployment-remover.path

    log "Starting deployment-remover.path..." "$CYAN"
    systemctl start deployment-remover.path

    log "Deployment remover: ACTIVE" "$GREEN"
}

# ============================================================================
# SSH HARDENING
# ============================================================================

configure_ssh() {
    log "Configuring SSH hardening..." "$BLUE"

    local ssh_template="${SCRIPT_DIR}/templates/ssh-hardening.conf"
    [[ -f "$ssh_template" ]] || error_exit "SSH template not found: $ssh_template"

    local config_file="/etc/ssh/sshd_config.d/deployment-hardening.conf"
    sed -e "s|{{USERNAME}}|${DEPLOY_USER}|g" \
        -e "s|{{CHROOT_PATH}}|${CHROOT_PATH}|g" \
        "$ssh_template" > "$config_file"

    log "SSH hardening: OK" "$GREEN"
    log "Restart SSH: systemctl restart sshd" "$YELLOW"
}

# ============================================================================
# TESTING
# ============================================================================

test_setup() {
    log "Testing setup..." "$BLUE"

    local errors=0

    # User exists
    if ! id -u "${DEPLOY_USER}" &>/dev/null; then
        log "✗ User not found" "$RED"
        ((errors++))
    else
        log "✓ User exists" "$GREEN"
    fi

    # Quarantine exists
    if [[ ! -d "$QUARANTINE_DIR" ]]; then
        log "✗ Quarantine not found" "$RED"
        ((errors++))
    else
        log "✓ Quarantine exists" "$GREEN"
    fi

    # AppArmor loaded
    if ! aa-status 2>/dev/null | grep -q "${DEPLOY_USER}"; then
        log "✗ AppArmor not loaded" "$RED"
        ((errors++))
    else
        log "✓ AppArmor loaded" "$GREEN"
    fi

    # Watcher active
    if ! systemctl is-active deployment-watcher.path &>/dev/null; then
        log "✗ Watcher not active" "$RED"
        ((errors++))
    else
        log "✓ Watcher active" "$GREEN"
    fi

    if [[ $errors -eq 0 ]]; then
        log "All tests passed!" "$GREEN"
        return 0
    else
        log "Tests failed: $errors errors" "$RED"
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
    echo -e "${GREEN}║     DEPLOYMENT USER CREATED SUCCESSFULLY!                      ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "  Username:      ${YELLOW}${DEPLOY_USER}${NC}"
    echo -e "  Chroot:        ${YELLOW}${CHROOT_PATH}/${NC}"
    echo -e "  Upload:        ${YELLOW}${QUARANTINE_DIR}/${NC}"
    echo -e "  GPG Keyring:   ${YELLOW}${GPG_KEYRING}${NC}"
    echo ""
    echo -e "${CYAN}Security Status:${NC}"
    echo -e "  Chroot Jail:   ${GREEN}✓ Enabled${NC} (escape-proof)"
    echo -e "  AppArmor:      ${GREEN}✓ Enforced${NC} (blind upload)"
    echo -e "  GPG Verify:    ${GREEN}✓ Mandatory${NC}"
    echo -e "  Watcher:       ${GREEN}✓ Active${NC}"
    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}SSH PRIVATE KEY LOCATION${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${YELLOW}⚠  IMPORTANT: Store this key securely!${NC}"
    echo ""
    echo -e "  Private key location:"
    echo -e "    ${GREEN}${DEPLOY_HOME}/.ssh/id_ed25519${NC}"
    echo ""
    echo -e "  Public key (for reference):"
    echo -e "    ${GREEN}${DEPLOY_HOME}/.ssh/id_ed25519.pub${NC}"
    echo ""
    echo -e "  To retrieve securely:"
    echo -e "    ${CYAN}scp root@SERVER:${DEPLOY_HOME}/.ssh/id_ed25519 ./deployment-key${NC}"
    echo -e "    ${CYAN}chmod 600 ./deployment-key${NC}"
    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}Deployment Package Format:${NC}"
    echo -e "  deployment.zip"
    echo -e "  ├── run.sh              # Deployment manifest"
    echo -e "  └── files/              # Your deployment files"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo -e "  View logs:       ${YELLOW}tail -f /var/log/deployment.log${NC}"
    echo -e "  Check watcher:   ${YELLOW}systemctl status deployment-watcher.path${NC}"
    echo -e "  Restart SSH:     ${YELLOW}systemctl restart sshd${NC}"
    echo -e "  Remove user:     ${YELLOW}./remove.sh${NC}"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header

    log "Step 1: Checking root privileges..." "$CYAN"
    check_root
    log "Root check: OK" "$GREEN"
    echo ""

    log "Step 2: Parsing arguments..." "$CYAN"
    parse_arguments "$@"
    log "Arguments parsed: OK" "$GREEN"
    echo ""

    log "Step 3: Checking for existing user..." "$CYAN"
    check_existing_user
    log "User check: OK" "$GREEN"
    echo ""

    log "Step 4: Validating GPG public key..." "$CYAN"
    validate_gpg_pubkey
    log "GPG validation: OK" "$GREEN"
    echo ""

    log "Starting deployment user setup..." "$CYAN"
    echo ""

    check_system
    install_dependencies
    create_user
    setup_directories
    setup_gpg
    install_apparmor_profile
    setup_apparmor_activation
    install_watcher_service
    install_remover_service
    configure_ssh

    echo ""
    test_setup

    display_results

    log "Setup completed successfully!" "$GREEN"
}

main "$@"