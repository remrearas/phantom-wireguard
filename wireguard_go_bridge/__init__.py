"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

wireguard_go_bridge v2 — Python bindings for wireguard-go-bridge.
bridge-db backed WireGuard management with SQLite persistence.
"""

from .types import WireGuardError, LogLevel, ErrorCode
from .client import (
    BridgeClient,
    ClientInfo,
    ClientList,
    DeviceInfo,
    ServerConfig,
    MultihopTunnel,
)
from ._ffi import get_lib, get_bridge_version, get_wireguard_go_version

__all__ = [
    # High-level API (primary)
    "BridgeClient",
    "ClientInfo",
    "ClientList",
    "DeviceInfo",
    "ServerConfig",
    "MultihopTunnel",
    # Types
    "WireGuardError",
    "LogLevel",
    "ErrorCode",
    # Utility
    "get_lib",
    "get_bridge_version",
    "get_wireguard_go_version",
]
