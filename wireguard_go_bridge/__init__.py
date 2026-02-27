"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
wireguard_go_bridge — Python bindings for wireguard-go-bridge (wireguard_go_bridge.so)

Native FFI bridge providing direct access to wireguard-go internals
without subprocess calls or config file I/O.
"""

from .types import WireGuardError, LogLevel, ErrorCode
from .device import WireGuardDevice
from .keys import WireGuardKeys
from .crypto import WireGuardCrypto
from ._ffi import get_lib, get_bridge_version, get_wireguard_go_version, set_log_callback

__all__ = [
    "get_lib",
    "WireGuardDevice",
    "WireGuardKeys",
    "WireGuardCrypto",
    "WireGuardError",
    "LogLevel",
    "ErrorCode",
    "get_bridge_version",
    "get_wireguard_go_version",
    "set_log_callback",
]