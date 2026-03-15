"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: SubnetOperations - Alt ağ doğrulama ve analizi yardımcı modülü
    =====================================================================

    NetworkAdmin için alt ağ doğrulama, RFC1918 kontrolü, boyut analizi,
    çakışma tespiti ve kapasite doğrulaması gerçekleştirir.

    Ana Sorumluluklar:
        - Alt ağların RFC1918 özel IP aralıklarında olduğunu doğrula
        - VPN işlemi için alt ağ boyutu yeterliliğini kontrol et
        - Mevcut ağ yapılandırmalarıyla çakışmaları tespit et
        - İstemci bağlantıları için yeterli kapasiteyi doğrula
        - Alt ağ değişiklik işlemleri için uyarılar oluştur

EN: SubnetOperations - Helper module for subnet validation and analysis
    =====================================================================

    Performs subnet validation, RFC1918 checking, size analysis,
    conflict detection and capacity verification for NetworkAdmin.

    Main Responsibilities:
        - Validate subnets are within RFC1918 private IP ranges
        - Check subnet size adequacy for VPN operation
        - Detect conflicts with existing network configurations
        - Verify sufficient capacity for client connections
        - Generate warnings for subnet change operations

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import ipaddress
from typing import Dict, Any, List


class _SubnetOperations:
    """
    Internal helper class for subnet validation and analysis.

    Responsibilities:
        - Validate RFC1918 private IP range compliance
        - Check subnet size adequacy for operations
        - Detect network conflicts with existing configurations
        - Verify client capacity requirements
        - Generate warnings for subnet change operations
    """

    # Network constants shared with NetworkAdmin
    RFC1918_SUBNETS = [
        ipaddress.IPv4Network('10.0.0.0/8'),
        ipaddress.IPv4Network('172.16.0.0/12'),
        ipaddress.IPv4Network('192.168.0.0/16')
    ]

    MIN_SUBNET_SIZE = 8  # Minimum 8 usable IPs required
    CAPACITY_BUFFER = 1.2  # Require 20% growth buffer
    MAX_SUBNET_PREFIX = 29

    def __init__(self, config: Dict[str, Any], run_command, common_tools):
        """
        Initialize subnet operations helper
        
        Args:
            config: Main configuration dictionary
            run_command: Command execution function
            common_tools: CommonTools instance
        """
        self.config = config
        self._run_command = run_command
        self.common_tools = common_tools

    def ensure_subnet_size_is_adequate(self, network: ipaddress.IPv4Network) -> Dict[str, Any]:
        """Check if subnet size is adequate for VPN operation."""
        usable_ips = network.num_addresses - 2  # Network and broadcast addresses are not usable

        if network.prefixlen > self.MAX_SUBNET_PREFIX:  # Fewer than 8 total addresses
            return {
                "valid": False,
                "error": f"Subnet too small. Minimum /{self.MAX_SUBNET_PREFIX} required (8 addresses), got /{network.prefixlen}"
            }

        if usable_ips < self.MIN_SUBNET_SIZE:
            return {
                "valid": False,
                "error": f"Subnet must have at least {self.MIN_SUBNET_SIZE} usable IPs, got {usable_ips}"
            }

        return {
            "valid": True,
            "usable_ips": usable_ips,
            "prefixlen": network.prefixlen
        }

    def ensure_subnet_is_private(self, network: ipaddress.IPv4Network) -> Dict[str, Any]:
        """Validate that subnet is within RFC1918 private ranges."""
        for private_range in self.RFC1918_SUBNETS:
            if network.subnet_of(private_range):
                return {
                    "valid": True,
                    "private_range": str(private_range)
                }

        return {
            "valid": False,
            "error": f"Subnet {network} is not within RFC1918 private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)"
        }

    def ensure_no_network_conflicts(self, network: ipaddress.IPv4Network) -> Dict[str, Any]:
        """Check for conflicts with existing network configurations."""
        try:
            # Retrieve all network interfaces from system
            result = self._run_command(["ip", "addr", "show"])
            if result["returncode"] == 0:
                conflicts = []

                for line in result["stdout"].split('\n'):
                    if 'inet ' in line and not line.strip().startswith('inet6'):
                        try:
                            ip_part = line.strip().split()[1]
                            existing_network = ipaddress.IPv4Network(ip_part, strict=False)

                            # Check if networks overlap
                            if network.overlaps(existing_network):
                                interface = "unknown"
                                # Extract interface name from output context
                                lines = result["stdout"].split('\n')
                                for i, l in enumerate(lines):
                                    if line == l and i > 0:
                                        # Search backwards for interface declaration
                                        for j in range(i - 1, max(0, i - 5), -1):
                                            if lines[j].strip() and not lines[j].startswith(' '):
                                                interface_parts = lines[j].split(':')
                                                if len(interface_parts) > 1:
                                                    interface = interface_parts[1].strip().split()[0]
                                                    break

                                conflicts.append({
                                    "interface": interface,
                                    "network": str(existing_network)
                                })
                        except ValueError:
                            continue

                if conflicts:
                    conflict_list = [f"{c['interface']}: {c['network']}" for c in conflicts]
                    return {
                        "valid": False,
                        "error": f"Network conflicts detected with: {', '.join(conflict_list)}",
                        "conflicts": conflicts
                    }
        except (ValueError, KeyError, AttributeError, OSError):
            # Continue if system check fails (permission issues, etc.)
            pass

        return {
            "valid": True,
            "conflicts": []
        }

    def ensure_sufficient_capacity_for_clients(self, network: ipaddress.IPv4Network,
                                               client_count: int) -> Dict[str, Any]:
        """
        Ensure new subnet has enough capacity for existing clients plus growth.

        Note: 20% growth buffer is mandatory for future expansion.
        """
        usable_ips = network.num_addresses - 2  # Network and broadcast addresses are not usable
        required_ips = int(client_count * self.CAPACITY_BUFFER) + 1  # Include server IP

        if usable_ips < required_ips:
            return {
                "valid": False,
                "error": f"Insufficient capacity. Need {required_ips} IPs "
                         f"({client_count} clients + 20% buffer), but subnet has {usable_ips}"
            }

        return {
            "valid": True,
            "usable_ips": usable_ips,
            "required_ips": required_ips,
            "utilization_after": round((client_count / usable_ips) * 100, 2)
        }

    @staticmethod
    def generate_subnet_change_warnings(client_count: int, active_count: int) -> List[str]:
        """Generate warnings for subnet change operation."""
        warnings = []

        if active_count > 0:
            warnings.append(f"{active_count} active client connections will be temporarily disconnected")

        if client_count > 10:
            warnings.append(f"All {client_count} client configurations will be automatically updated")

        warnings.extend([
            "WireGuard service will be restarted",
            "Firewall rules will be updated",
            "Brief network interruption expected (usually under 10 seconds)"
        ])

        return warnings
