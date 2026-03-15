"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Ghost Type-Safe Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from phantom.models.base import BaseModel


@dataclass
class EnableGhostResult(BaseModel):
    status: str
    server_ip: str
    domain: str
    secret: str
    protocol: str
    port: int
    activated_at: str
    connection_command: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "server_ip": self.server_ip,
            "domain": self.domain,
            "secret": self.secret,
            "protocol": self.protocol,
            "port": self.port,
            "activated_at": self.activated_at,
            "connection_command": self.connection_command
        }


@dataclass
class DisableGhostResult(BaseModel):
    status: str
    message: str
    restored: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
            "message": self.message
        }
        if self.restored is not None:
            result["restored"] = self.restored  # type: ignore
        return result


@dataclass
class GhostServiceInfo(BaseModel):
    wstunnel: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wstunnel": self.wstunnel
        }


@dataclass
class GhostStatusResult(BaseModel):
    status: str
    enabled: bool
    message: Optional[str] = None
    server_ip: Optional[str] = None
    domain: Optional[str] = None
    secret: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[int] = None
    services: Optional[GhostServiceInfo] = None
    activated_at: Optional[str] = None
    connection_command: Optional[str] = None
    client_export_info: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
            "enabled": self.enabled
        }

        if self.message is not None:
            result["message"] = self.message
        if self.server_ip is not None:
            result["server_ip"] = self.server_ip
        if self.domain is not None:
            result["domain"] = self.domain
        if self.secret is not None:
            result["secret"] = self.secret
        if self.protocol is not None:
            result["protocol"] = self.protocol
        if self.port is not None:
            result["port"] = self.port  # type: ignore
        if self.services is not None:
            result["services"] = self.services.to_dict()  # type: ignore
        if self.activated_at is not None:
            result["activated_at"] = self.activated_at
        if self.connection_command is not None:
            result["connection_command"] = self.connection_command
        if self.client_export_info is not None:
            result["client_export_info"] = self.client_export_info

        return result
