"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Ortak Araçlar ve Sabitler
    ==========================================

    Multihop VPN yönlendirme için gerekli sabitler, yardımcı fonksiyonlar
    ve paylaşılan araçları içerir.

EN: Multihop Module Common Tools and Constants
    ===========================================

    Contains constants, utility functions and shared tools required for
    multihop VPN routing.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

# =============================================================================
# MULTIHOP MODULE CONSTANTS
# =============================================================================

# Network Configuration
DEFAULT_VPN_DNS = "8.8.8.8"
AUTO_PERSISTENT_KEEP_ALIVE = 5  # Default PersistentKeepalive value in seconds

# Interface Names
VPN_INTERFACE_NAME = "wg_vpn"
DEFAULT_MAIN_INTERFACE = "wg_main"

# Service Names
MONITOR_SERVICE_NAME = "phantom-multihop-monitor"
NETWORKD_SERVICE_NAME = "systemd-networkd"

# File Paths
SYSTEMD_NETWORK_DIR = "/etc/systemd/network"
WIREGUARD_CONFIG_DIR = "/etc/wireguard"
RT_TABLES_FILE = "/etc/iproute2/rt_tables"

# Network Configuration
DEFAULT_WG_NETWORK = "10.8.0.0/24"
FALLBACK_VPN_SUBNET = "172.16.0.0/24"

# Routing Tables
MULTIHOP_TABLE_ID = 100
MULTIHOP_TABLE_NAME = "multihop"

# Policy Priorities
PEER_TRAFFIC_PRIORITY = 99
MULTIHOP_TRAFFIC_PRIORITY = 100

# Timeouts and Intervals
DEFAULT_HANDSHAKE_TIMEOUT = 30  # seconds
DEFAULT_LOG_LINES = 50
INTERFACE_SETUP_DELAY = 2  # seconds
SERVICE_START_DELAY = 1  # seconds

# Required Config Sections and Keys
REQUIRED_SECTIONS = ['[Interface]', '[Peer]']
REQUIRED_INTERFACE_KEYS = ['PrivateKey']
REQUIRED_PEER_KEYS = ['PublicKey', 'Endpoint', 'AllowedIPs']

# Generic Filename Exclusions
GENERIC_CONFIG_NAMES = ["wg", "client", "config"]

# Log Levels (aligned with multihop-monitor-service.py)
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "SUCCESS": "SUCCESS",
    "WARNING": "WARNING",
    "ERROR": "ERROR"
}


def build_networkd_config_path(interface: str) -> str:
    """
    Builds systemd-networkd configuration file path.
    
    Args:
        interface: Interface name
        
    Returns:
        str: Full path to networkd config file
    """
    return f"{SYSTEMD_NETWORK_DIR}/90-phantom-{interface}.network"


def build_wireguard_config_path(interface: str) -> str:
    """
    Builds WireGuard configuration file path.
    
    Args:
        interface: Interface name
        
    Returns:
        str: Full path to WireGuard config file
    """
    return f"{WIREGUARD_CONFIG_DIR}/{interface}.conf"
