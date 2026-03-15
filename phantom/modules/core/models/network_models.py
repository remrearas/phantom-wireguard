"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Network Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from phantom.models.base import BaseModel


@dataclass
class TransferStats(BaseModel):
    received: str  # e.g., "1.5 GiB"
    sent: str  # e.g., "2.3 GiB"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "received": self.received,
            "sent": self.sent
        }


@dataclass
class PeerInfo(BaseModel):
    public_key: str
    allowed_ips: str
    latest_handshake: Optional[str] = None
    endpoint: Optional[str] = None
    transfer: Optional[TransferStats] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "public_key": self.public_key,
            "allowed_ips": self.allowed_ips
        }
        if self.latest_handshake:
            result["latest_handshake"] = self.latest_handshake
        if self.endpoint:
            result["endpoint"] = self.endpoint
        if self.transfer:
            result["transfer"] = self.transfer.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        return cls(
            public_key=data["public_key"],
            allowed_ips=data["allowed_ips"],
            latest_handshake=data.get("latest_handshake"),
            endpoint=data.get("endpoint"),
            transfer=TransferStats(**data["transfer"]) if "transfer" in data else None
        )


@dataclass
class NetworkInfo(BaseModel):
    subnet: str
    server_ip: str
    total_ips: int
    used_ips: int
    available_ips: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subnet": self.subnet,
            "server_ip": self.server_ip,
            "total_ips": self.total_ips,
            "used_ips": self.used_ips,
            "available_ips": self.available_ips
        }


@dataclass
class SubnetChangeValidation(BaseModel):
    valid: bool
    current_subnet: str
    new_subnet: str
    ip_mapping: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "valid": self.valid,
            "current_subnet": self.current_subnet,
            "new_subnet": self.new_subnet,
            "ip_mapping": self.ip_mapping
        }
        if self.errors:
            result["errors"] = self.errors
        if self.warnings:
            result["warnings"] = self.warnings
        return result


@dataclass
class NetworkAnalysis(BaseModel):
    current_subnet: str
    subnet_size: int
    clients: Dict[str, Any]
    server_ip: str
    can_change: bool
    blockers: Dict[str, Any]
    main_interface: Dict[str, Any]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_subnet": self.current_subnet,
            "subnet_size": self.subnet_size,
            "clients": self.clients,
            "server_ip": self.server_ip,
            "can_change": self.can_change,
            "blockers": self.blockers,
            "main_interface": self.main_interface,
            "warnings": self.warnings
        }


@dataclass
class NetworkValidationResult(BaseModel):
    valid: bool
    new_subnet: str
    current_subnet: str
    checks: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    ip_mapping_preview: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "valid": self.valid,
            "new_subnet": self.new_subnet,
            "current_subnet": self.current_subnet,
            "checks": self.checks,
            "warnings": self.warnings,
            "errors": self.errors
        }
        if self.ip_mapping_preview:
            result["ip_mapping_preview"] = self.ip_mapping_preview
        return result


@dataclass
class NetworkMigrationResult(BaseModel):
    success: bool
    old_subnet: str
    new_subnet: str
    clients_updated: int
    backup_id: str
    ip_mapping: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "old_subnet": self.old_subnet,
            "new_subnet": self.new_subnet,
            "clients_updated": self.clients_updated,
            "backup_id": self.backup_id,
            "ip_mapping": self.ip_mapping
        }


@dataclass
class MainInterfaceInfo(BaseModel):
    interface: str
    ip: str
    network: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface,
            "ip": self.ip,
            "network": self.network
        }
