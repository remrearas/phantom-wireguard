"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: DataStore Manager - İstemci verilerini kalıcı olarak depolama ve yönetme
    ========================================================================
    
    Bu sınıf, TinyDB veritabanı üzerinden tüm istemci verilerini ve IP tahsislerini
    yönetir.
    
    Ana Sorumluluklar:
        - İstemci verilerini TinyDB'de saklama ve yönetme
        - IP adresi tahsisi ve takibi
        - Subnet değişiklikleri için IP yeniden haritalama
        - Veritabanı bütünlüğü ve tutarlılığı
        
    TinyDB Veritabanı Yapısı:
        Dosya: self.data_dir / "clients.db"
        
        clients tablosu örneği:
        {
          "_default": {
            "1": {
              "name": "john-laptop",
              "ip": "10.8.0.2",
              "private_key": "aBcD1234...",
              "public_key": "xYz5678...",
              "preshared_key": "PreShared123...",
              "created": "2025-01-30T10:15:00",
              "enabled": true
            },
            "2": {
              "name": "alice-phone",
              "ip": "10.8.0.3",
              "private_key": "eFgH5678...",
              "public_key": "MnO9012...",
              "preshared_key": "PreShared456...",
              "created": "2025-01-30T11:30:00",
              "enabled": true
            }
          }
        }
        
        ip_assignments tablosu örneği:
        {
          "_default": {
            "1": {
              "ip": "10.8.0.2",
              "client_name": "john-laptop",
              "assigned_at": "2025-01-30T10:15:00"
            },
            "2": {
              "ip": "10.8.0.3",
              "client_name": "alice-phone",
              "assigned_at": "2025-01-30T11:30:00"
            }
          }
        }

EN: DataStore Manager - Store and manage all client data persistently
    ================================================================
    
    This class manages all client data and IP allocations through TinyDB database.
    
    Main Responsibilities:
        - Store and manage client data in TinyDB
        - IP address allocation and tracking
        - IP remapping for subnet changes
        - Database integrity and consistency
        
    TinyDB Database Structure:
        File: self.data_dir / "clients.db"
        
        clients table example:
        {
          "_default": {
            "1": {
              "name": "john-laptop",
              "ip": "10.8.0.2",
              "private_key": "aBcD1234...",
              "public_key": "xYz5678...",
              "preshared_key": "PreShared123...",
              "created": "2025-01-30T10:15:00",
              "enabled": true
            },
            "2": {
              "name": "alice-phone",
              "ip": "10.8.0.3",
              "private_key": "eFgH5678...",
              "public_key": "MnO9012...",
              "preshared_key": "PreShared456...",
              "created": "2025-01-30T11:30:00",
              "enabled": true
            }
          }
        }
        
        ip_assignments table example:
        {
          "_default": {
            "1": {
              "ip": "10.8.0.2",
              "client_name": "john-laptop",
              "assigned_at": "2025-01-30T10:15:00"
            },
            "2": {
              "ip": "10.8.0.3",
              "client_name": "alice-phone",
              "assigned_at": "2025-01-30T11:30:00"
            }
          }
        }

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from tinydb import TinyDB, Query
import ipaddress

from phantom.api.exceptions import ClientNotFoundError
from ..models import WireGuardClient
from .default_constants import (
    DEFAULT_WG_NETWORK,
    CLIENTS_TABLE_NAME,
    IP_ASSIGNMENTS_TABLE_NAME
)


class DataStore:
    """TinyDB-based storage manager for client data and IP allocations.

    Uses TinyDB as the data source for managing WireGuard client data
    and IP address allocations.

    Core Functions:
        - Client CRUD operations
        - Automatic IP allocation and release
        - IP remapping for subnet changes
        - Database consistency control

    Performance:
        - Fast TinyDB queries
        - Single data source, no synchronization issues
        - Optimized memory usage
    """

    def __init__(self, db_path: Path, data_dir: Path, subnet: str = DEFAULT_WG_NETWORK):
        self.db_path = db_path
        self.data_dir = data_dir
        self.subnet = subnet
        self.network = ipaddress.IPv4Network(subnet)

        # Initialize database and tables
        self._initialize_database()

    def _initialize_database(self) -> None:
        self.db = TinyDB(self.db_path)
        self.clients_table = self.db.table(CLIENTS_TABLE_NAME)
        self.ip_table = self.db.table(IP_ASSIGNMENTS_TABLE_NAME)

    def store_new_client(self, client: WireGuardClient) -> None:
        # Convert to dict for storage
        client_dict = client.to_dict()

        # Store in clients table
        self.clients_table.insert(client_dict)

        # Track IP allocation
        self.ip_table.insert({
            'ip': client.ip,
            'client_name': client.name,
            'assigned_at': client.created.isoformat()
        })

    def remove_existing_client(self, client_name: str) -> None:
        client_query = Query()

        # Get client data for IP cleanup
        client = self.clients_table.get(client_query.name == client_name)  # type: ignore
        if client:
            # Remove IP allocation
            ip_query = Query()
            self.ip_table.remove(ip_query.client_name == client_name)  # type: ignore

            # Remove client
            self.clients_table.remove(client_query.name == client_name)  # type: ignore

    def ensure_client_does_not_exist(self, client_name: str) -> None:
        client_query = Query()
        if self.clients_table.search(client_query.name == client_name):  # type: ignore
            raise ValueError(f"Client '{client_name}' already exists")

    def find_client_by_name(self, client_name: str) -> Optional[WireGuardClient]:
        client_query = Query()
        result = self.clients_table.get(client_query.name == client_name)  # type: ignore
        return WireGuardClient.from_dict(dict(result)) if result else None

    def get_all_clients(self) -> List[WireGuardClient]:
        return [WireGuardClient.from_dict(dict(client)) for client in self.clients_table.all()]

    def allocate_next_available_ip(self) -> str:
        # Get allocated IPs
        allocated_ips = {record['ip'] for record in self.ip_table.all()}

        # Add server IP to allocated set
        server_ip = str(self.network.network_address + 1)
        allocated_ips.add(server_ip)

        # Find first available IP
        for ip in self.network.hosts():
            ip_str = str(ip)
            if ip_str not in allocated_ips:
                return ip_str

        raise ValueError("No available IP addresses in the subnet")

    def update_client_ip_address(self, client_name: str, new_ip: str) -> None:
        client_query = Query()
        ip_query = Query()

        self.clients_table.update({'ip': new_ip}, client_query.name == client_name)  # type: ignore

        self.ip_table.update({
            'ip': new_ip,
            'assigned_at': datetime.now().isoformat()
        }, ip_query.client_name == client_name)  # type: ignore

    def check_if_client_exists(self, client_name: str) -> bool:
        client_query = Query()
        return bool(self.clients_table.search(client_query.name == client_name))  # type: ignore

    def update_network_configuration(self, new_subnet: str) -> None:
        self.subnet = new_subnet
        self.network = ipaddress.IPv4Network(new_subnet)

    def get_ip_allocations(self) -> List[Dict[str, Any]]:
        return [dict(record) for record in self.ip_table.all()]

    def update_all_client_ips(self, ip_mapping: Dict[str, str]) -> None:
        client_query = Query()
        ip_query = Query()

        for client_name, new_ip in ip_mapping.items():
            # Update client IP
            self.clients_table.update({'ip': new_ip}, client_query.name == client_name)  # type: ignore

            self.ip_table.update({
                'ip': new_ip,
                'assigned_at': datetime.now().isoformat()
            }, ip_query.client_name == client_name)  # type: ignore

    def create_ip_mapping_for_subnet_change(self, old_network: ipaddress.IPv4Network,
                                            new_network: ipaddress.IPv4Network) -> Dict[str, str]:
        # old_network kept for API compatibility
        _ = old_network
        ip_mapping = {}
        clients = self.get_all_clients()

        # Sort clients by IP for consistent mapping
        sorted_clients = sorted(clients, key=lambda c: ipaddress.IPv4Address(c.ip))

        # Allocate new IPs (skip server .1)
        new_hosts = list(new_network.hosts())[1:]

        for i, client in enumerate(sorted_clients):
            if i < len(new_hosts):
                ip_mapping[client.name] = str(new_hosts[i])
            else:
                raise ValueError(f"New subnet too small for {len(sorted_clients)} clients")

        return ip_mapping

    def update_client_ip(self, client_name: str, new_ip: str) -> None:
        # Verify client exists
        client = self.find_client_by_name(client_name)
        if not client:
            raise ClientNotFoundError(f"Client '{client_name}' not found")

        old_ip = client.ip

        self.clients_table.update(
            {"ip": new_ip},
            Query().name == client_name  # type: ignore
        )

        # Update IP allocation table
        self.ip_table.remove(Query().ip == old_ip)  # type: ignore

        # Add new IP allocation
        self.ip_table.insert({
            "ip": new_ip,
            "client_name": client_name,
            "assigned_at": datetime.now().isoformat()
        })

    def close(self) -> None:
        if hasattr(self, 'db'):
            self.db.close()
