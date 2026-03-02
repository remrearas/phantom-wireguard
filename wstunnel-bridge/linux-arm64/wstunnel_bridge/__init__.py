"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge — Python bindings for wstunnel server via native FFI bridge.
"""

__version__ = "2.1.0"

from ._ffi import get_lib, set_log_callback, get_version
from .types import (
    BridgeError,
    ServerStartError,
    ServerNotRunningError,
    AlreadyRunningError,
    ConfigError,
    LogLevel,
    check_error,
)
from .models import ServerConfig
from .bridge import WstunnelBridge
from .db import WstunnelDB

__all__ = [
    "get_lib",
    "set_log_callback",
    "get_version",
    "BridgeError",
    "ServerStartError",
    "ServerNotRunningError",
    "AlreadyRunningError",
    "ConfigError",
    "LogLevel",
    "check_error",
    "ServerConfig",
    "WstunnelBridge",
    "WstunnelDB",
]
