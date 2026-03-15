"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Konfigürasyon İşleyicisi
    =========================================

    WireGuard VPN konfigürasyonlarını ayrıştırır, doğrular ve yönetir.
    Import edilen konfigürasyonları analiz eder ve multihop yapısına uyarlar.

EN: Multihop Module Configuration Handler
    ======================================

    Parses, validates and manages WireGuard VPN configurations.
    Analyzes imported configurations and adapts them to multihop structure.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import ipaddress
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .common_tools import (
    DEFAULT_VPN_DNS, AUTO_PERSISTENT_KEEP_ALIVE, REQUIRED_SECTIONS,
    REQUIRED_INTERFACE_KEYS, REQUIRED_PEER_KEYS,
)


class ConfigHandler:

    def __init__(self, exit_configs_dir: Path, config: Dict[str, Any], logger):
        self.exit_configs_dir = exit_configs_dir
        self.config = config
        self.logger = logger

    # noinspection PyMethodMayBeStatic
    def parse_wireguard_config_sections(self, config_content: str) -> Dict[str, Dict[str, str]]:
        # noinspection DuplicatedCode
        sections = {}
        current_section = None

        for line in config_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('[') and line.endswith(']'):
                current_section = line
                sections[current_section] = {}
                continue

            if current_section and '=' in line:
                key, value = line.split('=', 1)
                sections[current_section][key.strip()] = value.strip()

        return sections

    # noinspection PyMethodMayBeStatic
    def extract_endpoint(self, config_content: str) -> Optional[str]:  # noinspection PyMethodMayBeStatic
        for line in config_content.split('\n'):
            line = line.strip()
            if line.startswith('Endpoint'):
                return line.split('=', 1)[1].strip()
        return None

    def extract_vpn_ip(self, config_content: str) -> Optional[str]:
        try:
            for line in config_content.split('\n'):
                line = line.strip()
                if line.startswith('Address'):
                    address = line.split('=', 1)[1].strip()
                    return address.split('/')[0]  # Remove CIDR notation
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract VPN IP: {e}")
            return None

    def validate_vpn_config(self, config_content: str) -> Dict[str, Any]:
        sections = self.parse_wireguard_config_sections(config_content)

        # Check required sections
        for section in REQUIRED_SECTIONS:
            if section not in sections:
                return {"valid": False, "error": f"Missing required section: {section}"}

        # Check interface keys
        interface = sections.get('[Interface]', {})
        for key in REQUIRED_INTERFACE_KEYS:
            if key not in interface:
                return {"valid": False, "error": f"Missing required Interface key: {key}"}

        # Check peer keys
        peer = sections.get('[Peer]', {})
        for key in REQUIRED_PEER_KEYS:
            if key not in peer:
                return {"valid": False, "error": f"Missing required Peer key: {key}"}

        # Validate AllowedIPs includes 0.0.0.0/0
        allowed_ips = peer.get('AllowedIPs', '')
        if '0.0.0.0/0' not in allowed_ips:
            self.logger.warning("Config may not route all traffic (AllowedIPs doesn't include 0.0.0.0/0)")

        return {"valid": True}

    def enhance_vpn_config_for_multihop(self, config_content: str) -> Tuple[str, List[str]]:
        multihop_config = self.config.get("multihop", {})
        keepalive_value = multihop_config.get("auto_persistent_keep_alive", AUTO_PERSISTENT_KEEP_ALIVE)

        lines = config_content.strip().split('\n')
        enhanced_lines = []
        in_peer_section = False
        peer_has_keepalive = False
        optimizations_applied = []

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('[Peer]'):
                in_peer_section = True
                peer_has_keepalive = False
                enhanced_lines.append(line)
                continue
            elif stripped_line.startswith('[') and in_peer_section:
                if not peer_has_keepalive:
                    enhanced_lines.append(f"PersistentKeepalive = {keepalive_value}")
                    optimizations_applied.append(
                        f"Added PersistentKeepalive = {keepalive_value} for multihop stability")
                in_peer_section = False
                enhanced_lines.append(line)
                continue
            elif in_peer_section and stripped_line.startswith('PersistentKeepalive'):
                peer_has_keepalive = True
                try:
                    existing_value = int(stripped_line.split('=')[1].strip())
                    if existing_value == 0:
                        enhanced_lines.append(f"PersistentKeepalive = {keepalive_value}")
                        optimizations_applied.append(f"Enabled PersistentKeepalive = {keepalive_value} (was disabled)")
                    elif existing_value > 60:
                        enhanced_lines.append(f"PersistentKeepalive = {keepalive_value}")
                        optimizations_applied.append(
                            f"Optimized PersistentKeepalive: {existing_value}s -> {keepalive_value}s")
                    else:
                        enhanced_lines.append(line)
                        optimizations_applied.append(f"Kept existing PersistentKeepalive = {existing_value}s")
                except (ValueError, IndexError):
                    enhanced_lines.append(f"PersistentKeepalive = {keepalive_value}")
                    optimizations_applied.append(f"Fixed malformed PersistentKeepalive -> {keepalive_value}s")
                continue
            else:
                enhanced_lines.append(line)

        if in_peer_section and not peer_has_keepalive:
            enhanced_lines.append(f"PersistentKeepalive = {keepalive_value}")
            optimizations_applied.append(f"Added PersistentKeepalive = {keepalive_value} to final peer")

        return '\n'.join(enhanced_lines), optimizations_applied

    def parse_vpn_config(self, config_content: str) -> Optional[Dict[str, str]]:
        try:
            sections = self.parse_wireguard_config_sections(config_content)
            # noinspection DuplicatedCode
            interface = sections.get('[Interface]', {})

            if 'Address' not in interface:
                self.logger.error("VPN config missing required 'Address' field in [Interface] section")
                return None

            try:
                address = interface['Address']
                ipaddress.IPv4Interface(address)  # Validate IP format

                return {
                    'address': address,
                    'private_key': interface.get('PrivateKey', ''),
                    'dns': interface.get('DNS', DEFAULT_VPN_DNS)
                }
            except ValueError as e:
                self.logger.error(f"Invalid Address format in VPN config: {e}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to parse VPN config: {e}")
            return None

    # noinspection DuplicatedCode
    def clean_vpn_config(self, config_content: str) -> str:
        try:
            lines = []
            current_section = None

            # Valid parameters for wg setconf
            interface_valid_params = {'PrivateKey', 'ListenPort', 'FwMark'}
            peer_valid_params = {'PublicKey', 'PresharedKey', 'AllowedIPs', 'Endpoint', 'PersistentKeepalive'}

            for line in config_content.split('\n'):
                line = line.strip()

                # Track current section
                if line.startswith('[Interface]'):
                    current_section = 'interface'
                    lines.append(line)
                elif line.startswith('[Peer]'):
                    current_section = 'peer'
                    lines.append(line)
                elif line and '=' in line:
                    # Extract parameter name
                    param_name = line.split('=')[0].strip()

                    # Keep only valid parameters for current section
                    if current_section == 'interface' and param_name in interface_valid_params:
                        lines.append(line)
                    elif current_section == 'peer' and param_name in peer_valid_params:
                        lines.append(line)
                    # Skip all other parameters (Address, DNS, MTU, Table, PreUp, PostUp, etc.)
                elif not line or line.startswith('#'):
                    # Keep empty lines and comments
                    lines.append(line)

            return '\n'.join(lines)

        except Exception as e:
            self.logger.error(f"Failed to clean VPN config: {e}")
            return config_content
