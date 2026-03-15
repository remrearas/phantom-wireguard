"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Utility Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from phantom.models.base import BaseModel


@dataclass
class SuccessResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "success": self.success,
            "data": self.data
        }
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class ErrorResponse(BaseModel):
    success: bool
    error: str
    code: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "code": self.code
        }


@dataclass
class TransferData(BaseModel):
    received: str
    sent: str
    received_bytes: int
    sent_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "received": self.received,
            "sent": self.sent,
            "received_bytes": self.received_bytes,
            "sent_bytes": self.sent_bytes
        }


@dataclass
class WireGuardShowData(BaseModel):
    interface: Dict[str, Any]
    peers: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface,
            "peers": self.peers
        }
