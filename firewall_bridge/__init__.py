"""
firewall_bridge — Python bindings for nftables and routing via native FFI bridge.
Replaces subprocess-based ufw/iptables/ip-rule management.
"""

from ._ffi import get_lib
from .types import FirewallBridgeError, ErrorCode, AddressFamily
from .firewall import FirewallManager
from .routing import RoutingManager

__all__ = [
    "get_lib",
    "FirewallBridgeError",
    "ErrorCode",
    "AddressFamily",
    "FirewallManager",
    "RoutingManager",
]