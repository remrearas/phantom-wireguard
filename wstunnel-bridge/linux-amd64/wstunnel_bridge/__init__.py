"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge — Python bindings for wstunnel via native FFI bridge.
Replaces subprocess-based wstunnel management.
"""

__version__ = "2.0.0"

from ._ffi import get_lib, set_log_callback, get_version
from .types import WstunnelError, LogLevel, ErrorCode
from .client import WstunnelClient
from .server import WstunnelServer
from .db import WstunnelDB
from .state import WstunnelState

__all__ = [
    "get_lib",
    "set_log_callback",
    "get_version",
    "WstunnelError",
    "LogLevel",
    "ErrorCode",
    "WstunnelClient",
    "WstunnelServer",
    "WstunnelDB",
    "WstunnelState",
]