"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Client Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

from phantom.models.base import BaseModel


@dataclass
class WireGuardClient(BaseModel):
    name: str
    ip: str
    private_key: str
    public_key: str
    preshared_key: str
    created: datetime
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ip": self.ip,
            "private_key": self.private_key,
            "public_key": self.public_key,
            "preshared_key": self.preshared_key,
            "created": self.created.isoformat(),  # ISO format for JSON
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WireGuardClient':
        return cls(
            name=data["name"],
            ip=data["ip"],
            private_key=data["private_key"],
            public_key=data["public_key"],
            preshared_key=data["preshared_key"],
            created=datetime.fromisoformat(data["created"]),
            enabled=data.get("enabled", True)
        )


@dataclass
class ClientAddResult(BaseModel):
    client: WireGuardClient
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client": {
                "name": self.client.name,
                "ip": self.client.ip,
                "public_key": self.client.public_key,
                "created": self.client.created.isoformat(),
                "enabled": self.client.enabled
            },
            "message": self.message
        }


@dataclass
class ClientInfo(BaseModel):
    name: str
    ip: str
    enabled: bool
    created: str
    connected: bool
    connection: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "ip": self.ip,
            "enabled": self.enabled,
            "created": self.created,
            "connected": self.connected
        }
        if self.connection:
            result["connection"] = self.connection  # type: ignore
        return result


@dataclass
class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    showing_from: int
    showing_to: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "showing_from": self.showing_from,
            "showing_to": self.showing_to
        }


@dataclass
class ClientListResult(BaseModel):
    clients: List[ClientInfo]
    total: int
    pagination: PaginationInfo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clients": [c.to_dict() for c in self.clients],
            "total": self.total,
            "pagination": self.pagination.to_dict()
        }


@dataclass
class ClientRemoveResult(BaseModel):
    removed: bool
    client_name: str
    client_ip: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "removed": self.removed,
            "client_name": self.client_name,
            "client_ip": self.client_ip,
        }


@dataclass
class ClientExportResult(BaseModel):
    client: WireGuardClient
    config: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client": {
                "name": self.client.name,
                "ip": self.client.ip,
                "created": self.client.created.isoformat(),
                "enabled": self.client.enabled,
                "private_key": self.client.private_key,
                "public_key": self.client.public_key,
                "preshared_key": self.client.preshared_key
            },
            "config": self.config
        }


@dataclass
class LatestClientsResult(BaseModel):
    latest_clients: List[ClientInfo]
    count: int
    total_clients: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latest_clients": [c.to_dict() for c in self.latest_clients],
            "count": self.count,
            "total_clients": self.total_clients
        }
