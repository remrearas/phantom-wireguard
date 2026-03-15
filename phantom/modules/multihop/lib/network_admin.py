"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Ağ Yöneticisi
    ==============================

    WireGuard arayüzlerini yönetir, IP yönlendirme kurallarını yapılandırır,
    systemd-networkd entegrasyonunu sağlar ve ağ trafiğini kontrol eder.

EN: Multihop Module Network Administrator
    ======================================

    Manages WireGuard interfaces, configures IP routing rules,
    provides systemd-networkd integration and controls network traffic.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import ipaddress
import time
from pathlib import Path
from typing import Dict, Any

from .common_tools import (
    VPN_INTERFACE_NAME, DEFAULT_WG_NETWORK,
    build_wireguard_config_path, PEER_TRAFFIC_PRIORITY,
    MULTIHOP_TRAFFIC_PRIORITY, MULTIHOP_TABLE_NAME, DEFAULT_MAIN_INTERFACE
)


class NetworkAdmin:

    def __init__(self, config: Dict[str, Any], logger, run_command_func):
        self.config = config
        self.logger = logger
        self._run_command = run_command_func

    def detect_current_subnet(self) -> str:
        wg_config = self.config.get("wireguard", {})
        wg_interface = wg_config.get("interface", DEFAULT_MAIN_INTERFACE)

        try:
            result = self._run_command(["ip", "addr", "show", wg_interface])
            if result["success"]:
                for line in result["stdout"].split("\n"):
                    if "inet " in line and "scope global" in line:
                        addr_with_prefix = line.strip().split()[1]
                        interface = ipaddress.IPv4Interface(addr_with_prefix)
                        network = interface.network
                        return str(network)
        except Exception as e:
            self.logger.warning(f"Could not detect subnet from interface: {e}")

        return wg_config.get("network", DEFAULT_WG_NETWORK)

    def setup_vpn_interface(self, vpn_interface: str, config_content: str) -> Dict[str, Any]:
        try:
            from .config_handler import ConfigHandler

            config_handler = ConfigHandler(Path("/tmp"), self.config, self.logger)

            interface_config = config_handler.parse_vpn_config(config_content)
            if not interface_config:
                return {"success": False, "error": "Failed to parse VPN config - missing or invalid Address field"}

            # Address is guaranteed to exist here because parse_vpn_config returns None if Address is missing
            try:
                vpn_interface_addr = ipaddress.IPv4Interface(interface_config['address'])
                vpn_ip = str(vpn_interface_addr)
            except ValueError as e:
                return {"success": False, "error": f"Invalid VPN address: {e}"}

            clean_config = config_handler.clean_vpn_config(config_content)
            vpn_config_path = build_wireguard_config_path(vpn_interface)

            with open(vpn_config_path, 'w') as f:
                f.write(clean_config)

            # Remove existing interface if present
            self._run_command(["ip", "link", "del", vpn_interface])

            # Interface setup sequence
            setup_commands = [
                ["ip", "link", "add", vpn_interface, "type", "wireguard"],
                ["wg", "setconf", vpn_interface, vpn_config_path],
                ["ip", "-4", "address", "add", vpn_ip, "dev", vpn_interface],
                ["ip", "link", "set", "mtu", "1420", "up", "dev", vpn_interface]
            ]

            for cmd in setup_commands:
                result = self._run_command(cmd)
                if not result["success"]:
                    return {"success": False, "error": f"Failed command: {' '.join(cmd)}"}

            return {"success": True, "vpn_ip": vpn_ip}

        except Exception as e:
            self.logger.error(f"Failed to setup VPN interface: {e}")
            return {"success": False, "error": str(e)}

    def verify_vpn_connection(self, vpn_interface: str) -> Dict[str, Any]:
        try:
            result = self._run_command(["wg", "show", vpn_interface])
            if result["success"]:
                has_handshake = "latest handshake" in result["stdout"]
                return {"success": True, "has_handshake": has_handshake}

            return {"success": False, "error": "VPN interface not found"}

        except Exception as e:
            self.logger.error(f"Failed to verify VPN connection: {e}")
            return {"success": False, "error": str(e)}

    def get_vpn_interface_status(self) -> Dict[str, Any]:
        try:
            result = self._run_command(["wg", "show", VPN_INTERFACE_NAME])
            if result["success"]:
                return {
                    "active": True,
                    "output": result["stdout"].strip()
                }
            else:
                return {
                    "active": False,
                    "error": "VPN interface not active"
                }
        except Exception as e:
            return {
                "active": False,
                "error": f"Unable to check VPN interface status: {e}"
            }

    def cleanup_vpn_interface(self) -> Dict[str, Any]:
        try:
            wg_config = self.config.get("wireguard", {})
            wg_network = wg_config.get("network", DEFAULT_WG_NETWORK)
            wg_interface_name = wg_config.get("interface", DEFAULT_MAIN_INTERFACE)

            cleanup_commands = [
                ["ip", "link", "del", VPN_INTERFACE_NAME],
                ["ip", "rule", "del", "from", wg_network, "to", wg_network, "table", "main"],
                ["ip", "rule", "del", "from", wg_network, "table", "multihop"],
                ["ip", "route", "flush", "table", "multihop"],
                ["iptables", "-t", "nat", "-D", "POSTROUTING", "-s", wg_network, "-o", VPN_INTERFACE_NAME, "-j",
                 "MASQUERADE"],
                ["iptables", "-D", "FORWARD", "-i", wg_interface_name, "-o", VPN_INTERFACE_NAME, "-j", "ACCEPT"],
                ["iptables", "-D", "FORWARD", "-i", VPN_INTERFACE_NAME, "-o", wg_interface_name, "-m", "state",
                 "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
                ["iptables", "-D", "FORWARD", "-i", wg_interface_name, "-o", wg_interface_name, "-s", wg_network, "-d",
                 wg_network, "-j", "ACCEPT"]
            ]

            for cmd in cleanup_commands:
                self._run_command(cmd)

            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to cleanup VPN interface: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_vpn_interface_basic(self) -> Dict[str, Any]:
        try:
            wg_config = self.config.get("wireguard", {})
            wg_network = wg_config.get("network", DEFAULT_WG_NETWORK)
            wg_interface_name = wg_config.get("interface", DEFAULT_MAIN_INTERFACE)

            cleanup_commands = [
                ["sh", "-c", f"ip link del {VPN_INTERFACE_NAME} 2>/dev/null || true"],

                ["sh", "-c",
                 f"ip rule del from {wg_network} to {wg_network} table main priority {PEER_TRAFFIC_PRIORITY} 2>/dev/null || true"],
                ["sh", "-c",
                 f"ip rule del from {wg_network} table {MULTIHOP_TABLE_NAME} priority {MULTIHOP_TRAFFIC_PRIORITY} 2>/dev/null || true"],

                ["sh", "-c", f"ip route flush table {MULTIHOP_TABLE_NAME} 2>/dev/null || true"],

                ["sh", "-c",
                 f"iptables -t nat -D POSTROUTING -s {wg_network} -o {VPN_INTERFACE_NAME} -j MASQUERADE 2>/dev/null || true"],
                ["sh", "-c",
                 f"iptables -D FORWARD -i {wg_interface_name} -o {VPN_INTERFACE_NAME} -j ACCEPT 2>/dev/null || true"],
                ["sh", "-c",
                 f"iptables -D FORWARD -i {VPN_INTERFACE_NAME} -o {wg_interface_name} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true"],
                ["sh", "-c",
                 f"iptables -D FORWARD -i {wg_interface_name} -o {wg_interface_name} -s {wg_network} -d {wg_network} -j ACCEPT 2>/dev/null || true"]
            ]

            for cmd in cleanup_commands:
                self._run_command(cmd)

            if not self._verify_rules_cleaned(wg_network):
                self.logger.warning("Some rules may still exist after cleanup")

            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to cleanup VPN interface: {e}")
            return {"success": False, "error": str(e)}

    def _verify_rules_cleaned(self, wg_network: str) -> bool:
        try:
            result = self._run_command(["ip", "rule", "show"])
            if result["success"]:
                output = result["stdout"]

                if f"from {wg_network}" in output:
                    self.logger.warning(f"Found leftover routing rules with 'from {wg_network}' after cleanup")
                    self._force_cleanup_rules(wg_network)
                    return False

            nat_result = self._run_command(["sh", "-c", f"iptables -t nat -L POSTROUTING -n | grep {wg_network}"])
            if nat_result["success"] and nat_result["stdout"].strip():
                self.logger.warning("NAT rules still exist after cleanup")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to verify cleanup: {e}")
            return False

    def _force_cleanup_rules(self, wg_network: str):
        self.logger.info("Attempting force cleanup of routing rules")
        for attempt in range(3):
            self._run_command(["sh", "-c",
                               f"ip rule del from {wg_network} to {wg_network} table main priority {PEER_TRAFFIC_PRIORITY} 2>/dev/null || true"])
            self._run_command(["sh", "-c",
                               f"ip rule del from {wg_network} table {MULTIHOP_TABLE_NAME} priority {MULTIHOP_TRAFFIC_PRIORITY} 2>/dev/null || true"])
            self._run_command(
                ["sh", "-c", f"ip rule del from {wg_network} to {wg_network} table main 2>/dev/null || true"])
            self._run_command(["sh", "-c", f"ip rule del from {wg_network} table multihop 2>/dev/null || true"])
            time.sleep(0.1)
