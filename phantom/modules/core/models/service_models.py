"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Service Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from phantom.models.base import BaseModel


@dataclass
class ServiceStatus(BaseModel):
    running: bool
    service_name: str
    started_at: Optional[str] = None
    pid: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "running": self.running,
            "service_name": self.service_name
        }
        if self.started_at:
            result["started_at"] = self.started_at
        if self.pid:
            result["pid"] = self.pid
        return result


@dataclass
class ClientStatistics(BaseModel):
    total_configured: int
    enabled_clients: int
    disabled_clients: int
    active_connections: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_configured": self.total_configured,
            "enabled_clients": self.enabled_clients,
            "disabled_clients": self.disabled_clients,
            "active_connections": self.active_connections
        }


@dataclass
class ServerConfig(BaseModel):
    interface: str
    config_file: str
    port: int
    network: str
    dns: List[str]
    config_exists: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface,
            "config_file": self.config_file,
            "port": self.port,
            "network": self.network,
            "dns": self.dns,
            "config_exists": self.config_exists
        }


@dataclass
class SystemInfo(BaseModel):
    install_dir: str
    config_dir: str
    data_dir: str
    firewall: Dict[str, str]
    wireguard_module: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "install_dir": self.install_dir,
            "config_dir": self.config_dir,
            "data_dir": self.data_dir,
            "firewall": self.firewall,
            "wireguard_module": self.wireguard_module
        }


@dataclass
class FirewallConfiguration(BaseModel):
    ufw: Dict[str, Any]
    iptables: Dict[str, Any]
    nat: Dict[str, Any]
    ports: Dict[str, Any]
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ufw": self.ufw,
            "iptables": self.iptables,
            "nat": self.nat,
            "ports": self.ports,
            "status": self.status
        }


@dataclass
class InterfaceStatistics(BaseModel):
    active: bool
    interface: str
    peers: List[Dict[str, Any]]
    public_key: Optional[str] = None
    port: Optional[int] = None
    rx_bytes: Optional[int] = None
    tx_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "active": self.active,
            "interface": self.interface,
            "peers": self.peers
        }
        if self.public_key:
            result["public_key"] = self.public_key
        if self.port:
            result["port"] = self.port
        if self.rx_bytes is not None:
            result["rx_bytes"] = self.rx_bytes
        if self.tx_bytes is not None:
            result["tx_bytes"] = self.tx_bytes
        return result


@dataclass
class ServiceLogs(BaseModel):
    logs: List[str]
    count: int
    service: str
    lines_requested: int
    source: Optional[str] = None
    file: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "logs": self.logs,
            "count": self.count,
            "service": self.service,
            "lines_requested": self.lines_requested
        }
        if self.source:
            result["source"] = self.source
        if self.file:
            result["file"] = self.file
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class RestartResult(BaseModel):
    restarted: bool
    service_active: bool
    interface_up: bool
    service: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "restarted": self.restarted,
            "service_active": self.service_active,
            "interface_up": self.interface_up,
            "service": self.service,
            "message": self.message
        }


@dataclass
class ServiceHealth(BaseModel):
    service: ServiceStatus
    interface: InterfaceStatistics
    clients: ClientStatistics
    configuration: ServerConfig
    system: SystemInfo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service.to_dict(),
            "interface": self.interface.to_dict(),
            "clients": self.clients.to_dict(),
            "configuration": self.configuration.to_dict(),
            "system": self.system.to_dict()
        }
