"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: FirewallOperations - Güvenlik duvarı kural yönetimi yardımcı modülü
    =====================================================================

    Ağ geçişleri sırasında UFW ve iptables kural güncellemelerini yönetir,
    NAT kuralları ve port yönlendirme işlemlerini içerir.

    Ana Sorumluluklar:
        - Kurtarma için mevcut güvenlik duvarı kurallarını yedekle
        - Alt ağ değiştiğinde UFW kurallarını güncelle
        - Ağ çevirisi için iptables NAT kurallarını güncelle
        - Güvenlik için SSH port erişim kurallarını yönet
        - Giden trafik için MASQUERADE kurallarını güncelle

EN: FirewallOperations - Helper module for firewall rule management
    =====================================================================

    Handles UFW and iptables rule updates during network migrations,
    including NAT rules and port forwarding operations.

    Main Responsibilities:
        - Backup current firewall rules for recovery
        - Update UFW rules when subnet changes
        - Update iptables NAT rules for network translation
        - Manage SSH port access rules for security
        - Update MASQUERADE rules for outbound traffic

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import ipaddress
import subprocess
from typing import Dict, Any, Callable, Optional
from phantom.modules.core.lib.default_constants import (
    DEFAULT_SSH_PORT
)


class _FirewallOperations:
    """
    Internal helper class for firewall rule management during network migrations.

    Responsibilities:
        - Capture current firewall rules for backup purposes
        - Update UFW rules when network subnet changes
        - Update iptables NAT rules for proper routing
        - Maintain firewall consistency throughout migration process
    """

    def __init__(self, run_command: Callable, wg_interface: str,
                 detect_ssh_port: Optional[Callable] = None,
                 analyze_interface: Optional[Callable] = None):
        """
        Initialize firewall operations helper
        
        Args:
            run_command: Command execution function
            wg_interface: WireGuard interface name (e.g., 'wg0')
            detect_ssh_port: Optional callback to detect SSH port
            analyze_interface: Optional callback to analyze main network interface
        """
        self._run_command = run_command
        self.wg_interface = wg_interface
        self._detect_ssh_port = detect_ssh_port or self._default_ssh_port
        self._analyze_main_network_interface = analyze_interface or self._default_interface

    @staticmethod
    def _default_ssh_port() -> str:
        """Default SSH port detection - returns standard port"""
        return DEFAULT_SSH_PORT

    @staticmethod
    def _default_interface() -> Dict[str, Any]:
        """Default interface detection - returns unknown"""
        return {"interface": "eth0"}  # Common default

    def capture_current_firewall_rules(self) -> Dict[str, Any]:
        """
        Capture current firewall rules for backup purposes
        
        Returns:
            Dictionary containing UFW and iptables rules
        """
        rules = {
            "ufw": {},
            "iptables": {}
        }

        try:
            # Get UFW status
            ufw_result = self._run_command(["ufw", "status", "numbered"])
            if ufw_result["returncode"] == 0:
                rules["ufw"]["status"] = ufw_result["stdout"]

            # Get iptables rules
            iptables_result = self._run_command(["iptables", "-t", "nat", "-L", "-n", "-v"])
            if iptables_result["returncode"] == 0:
                rules["iptables"]["nat"] = iptables_result["stdout"]
        except (OSError, ValueError, KeyError):
            pass

        return rules

    def update_firewall_rules_for_new_subnet(self, old_network: ipaddress.IPv4Network,
                                             new_network: ipaddress.IPv4Network) -> None:
        """
        Update all firewall rules for new subnet
        
        Args:
            old_network: Current network configuration
            new_network: Target network configuration
        """
        # Update UFW rules
        self.update_ufw_rules_for_subnet(old_network, new_network)

        # Update iptables NAT rules
        self.update_iptables_nat_for_subnet(old_network, new_network)

    def update_ufw_rules_for_subnet(self, old_network: ipaddress.IPv4Network,
                                    new_network: ipaddress.IPv4Network) -> None:
        """
        Update UFW firewall rules for subnet change
        
        Args:
            old_network: Current network configuration
            new_network: Target network configuration
        """
        try:
            # Detect actual SSH port
            ssh_port = self._detect_ssh_port()

            # Remove old subnet rule
            self._run_command([
                "ufw", "delete", "allow", "from", str(old_network),
                "to", "any", "port", ssh_port
            ])

            # Add new subnet rule
            self._run_command([
                "ufw", "allow", "from", str(new_network),
                "to", "any", "port", ssh_port
            ])

            # Update WireGuard subnet access if needed
            self._run_command([
                "ufw", "delete", "allow", "from", str(old_network)
            ])
            self._run_command([
                "ufw", "allow", "from", str(new_network)
            ])

        except (OSError, ValueError, subprocess.CalledProcessError):
            # Continue without failing - firewall rules can be restored manually if needed
            pass

    def update_iptables_nat_for_subnet(self, old_network: ipaddress.IPv4Network,
                                       new_network: ipaddress.IPv4Network) -> None:
        """
        Update iptables NAT rules for subnet change
        
        Args:
            old_network: Current network configuration
            new_network: Target network configuration
        """
        try:
            # Get main interface
            main_interface = self._analyze_main_network_interface()
            if main_interface["interface"] != "unknown":
                interface = main_interface["interface"]

                # Remove old NAT rule
                self._run_command([
                    "iptables", "-t", "nat", "-D", "POSTROUTING",
                    "-s", str(old_network), "-o", interface, "-j", "MASQUERADE"
                ])

                # Add new NAT rule
                self._run_command([
                    "iptables", "-t", "nat", "-A", "POSTROUTING",
                    "-s", str(new_network), "-o", interface, "-j", "MASQUERADE"
                ])

                # Save iptables rules persistently if netfilter-persistent is installed
                # Continue without failing if the command is not available
                self._run_command(["netfilter-persistent", "save"])

        except (OSError, ValueError, subprocess.CalledProcessError):
            # Continue without failing - NAT rules can be restored manually if needed
            pass
