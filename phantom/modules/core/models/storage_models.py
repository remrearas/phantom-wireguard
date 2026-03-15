"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Storage Data Models

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import Dict, Any

from phantom.models.base import BaseModel


@dataclass
class ClientDatastoreInfo(BaseModel):
    clients: Dict[str, Any]
    ip_assignments: Dict[str, str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clients": self.clients,
            "ip_assignments": self.ip_assignments,
            "metadata": self.metadata
        }


@dataclass
class ActiveConnectionsMap(BaseModel):
    connections: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return self.connections
