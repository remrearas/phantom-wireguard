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

firewall_bridge v2 — Stateful nftables + netlink routing bridge.
"""

from ._ffi import get_lib, get_version
from .types import FirewallBridgeError, ErrorCode, AddressFamily
from .models import RuleGroup, FirewallRule, RoutingRule, FirewallStatus, VerifyResult
from .client import FirewallClient

__all__ = [
    "FirewallClient",
    "RuleGroup", "FirewallRule", "RoutingRule", "FirewallStatus", "VerifyResult",
    "FirewallBridgeError", "ErrorCode", "AddressFamily",
    "get_lib", "get_version",
]