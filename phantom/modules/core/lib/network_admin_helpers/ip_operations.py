"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: IPOperations - IP adresi yönetimi yardımcı modülü
    =====================================================================

    Ağ geçişleri sırasında IP adresi yeniden eşleme, hesaplama ve
    veritabanı güncellemelerini gerçekleştirir.

    Ana Sorumluluklar:
        - Yürütmeden önce IP adresi yeniden eşlemesini önizle
        - Geçişler için tam IP eşlemesini hesapla
        - İstemci veritabanını yeni IP adresleriyle güncelle
        - Yeni alt ağlar için sunucu IP adreslerini hesapla
        - Ağ değişiklikleri sırasında IP aralıklarını dönüştür

EN: IPOperations - Helper module for IP address management
    =====================================================================

    Performs IP address remapping, calculation and database updates
    during network migrations.

    Main Responsibilities:
        - Preview IP address remapping before execution
        - Calculate complete IP mapping for migrations
        - Update client database with new IP addresses
        - Calculate server IP addresses for new subnets
        - Transform IP ranges during network changes

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import ipaddress
from typing import Dict, Any


class _IPOperations:
    """
    Internal helper class for IP address management during migrations.

    Responsibilities:
        - Calculate complete IP remapping for network migrations
        - Preview IP changes before execution
        - Update client database with new IP addresses
        - Maintain IP allocation consistency across changes
    """

    def __init__(self, data_store, config: Dict[str, Any]):
        """
        Initialize IP operations helper
        
        Args:
            data_store: DataStore instance for client data
            config: Main configuration dictionary
        """
        self.data_store = data_store
        self.config = config

    def preview_ip_remapping(self, old_network: ipaddress.IPv4Network,
                             new_network: ipaddress.IPv4Network,
                             current_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview IP address remapping for subnet change
        
        Args:
            old_network: Current network configuration
            new_network: Target network configuration
            current_info: Current network information
        
        Returns:
            Dictionary with mapping preview
        """
        # Parameter retained for compatibility but not used in current implementation
        _ = current_info

        # Get all clients
        clients = self.data_store.get_all_clients()

        # Create mapping preview
        mapping = {
            "server": {
                "old": str(old_network.network_address + 1),
                "new": str(new_network.network_address + 1)
            }
        }

        # Map clients sequentially
        new_ip_counter = 2  # Start from .2 (after server)
        for client in sorted(clients, key=lambda c: ipaddress.IPv4Address(c.ip)):
            old_ip = client.ip
            new_ip = str(new_network.network_address + new_ip_counter)
            mapping[client.name] = {
                "old": old_ip,
                "new": new_ip
            }
            new_ip_counter += 1

        return {
            "total_mappings": len(mapping),
            "mappings": mapping
        }

    def calculate_complete_ip_remapping(self, old_network: ipaddress.IPv4Network,
                                        new_network: ipaddress.IPv4Network) -> Dict[str, str]:
        """
        Calculate complete IP remapping for network migration
        
        Args:
            old_network: Current network configuration
            new_network: Target network configuration
        
        Returns:
            Dictionary mapping old IPs to new IPs
        """
        # Server always gets the first usable IP (.1 in the subnet)
        ip_mapping = {
            str(old_network.network_address + 1): str(new_network.network_address + 1)
        }

        # Get all clients sorted by IP
        clients = self.data_store.get_all_clients()
        sorted_clients = sorted(clients, key=lambda c: ipaddress.IPv4Address(c.ip))

        # Assign new IPs sequentially to maintain order
        new_ip_counter = 2  # Start from .2
        for client in sorted_clients:
            old_ip = client.ip
            new_ip = str(new_network.network_address + new_ip_counter)
            ip_mapping[old_ip] = new_ip
            new_ip_counter += 1

        return ip_mapping

    def update_client_database_with_new_ips(self, ip_mapping: Dict[str, str]) -> None:
        """
        Update client database with new IP addresses
        
        Args:
            ip_mapping: Dictionary mapping old IPs to new IPs
        """
        clients = self.data_store.get_all_clients()

        for client in clients:
            old_ip = client.ip
            new_ip = ip_mapping.get(old_ip)

            if new_ip and new_ip != old_ip:
                # Persist the new IP address to the database
                self.data_store.update_client_ip(client.name, new_ip)
