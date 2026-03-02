"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge types — Server-only exception hierarchy.
"""

from enum import IntEnum


class LogLevel(IntEnum):
    ERROR = 0
    WARN = 1
    INFO = 2
    DEBUG = 3
    TRACE = 4


class BridgeError(Exception):
    """Base exception for wstunnel bridge operations."""


class ServerStartError(BridgeError):
    """Server failed to start."""


class ServerNotRunningError(BridgeError):
    """Server is not running."""


class AlreadyRunningError(BridgeError):
    """Server is already running."""


class ConfigError(BridgeError):
    """Invalid or missing configuration."""


_ERROR_MAP: dict[int, type[BridgeError]] = {
    -1: AlreadyRunningError,    # ALREADY_RUNNING
    -2: ConfigError,            # INVALID_PARAM
    -3: BridgeError,            # RUNTIME
    -4: ServerStartError,       # START_FAILED
    -5: ServerNotRunningError,  # NOT_RUNNING
    -6: ConfigError,            # CONFIG_NULL
}


def check_error(result: int) -> None:
    """Raise mapped BridgeError if result is non-zero."""
    if result == 0:
        return
    cls = _ERROR_MAP.get(result, BridgeError)
    raise cls(f"FFI error code {result}")
