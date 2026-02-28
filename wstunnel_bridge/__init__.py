"""
wstunnel_bridge — Python bindings for wstunnel via native FFI bridge.
Replaces subprocess-based wstunnel management.
"""

from ._ffi import get_lib, set_log_callback, get_version
from .types import WstunnelError, LogLevel, ErrorCode
from .client import WstunnelClient
from .server import WstunnelServer

__all__ = [
    "get_lib",
    "set_log_callback",
    "get_version",
    "WstunnelError",
    "LogLevel",
    "ErrorCode",
    "WstunnelClient",
    "WstunnelServer",
]