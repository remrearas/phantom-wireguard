"""
phantom_wg_bridge — Python bindings for wireguard-go-bridge (libphantom_wg.so)

Native FFI bridge providing direct access to wireguard-go internals
without subprocess calls or config file I/O.
"""

from .types import WireGuardError, LogLevel, ErrorCode
from .device import WireGuardDevice
from .keys import WireGuardKeys
from .crypto import WireGuardCrypto
from ._ffi import get_bridge_version, get_wireguard_go_version, set_log_callback

__all__ = [
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