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

Dataclass models for firewall-bridge v2.
"""

from dataclasses import dataclass, field, fields


def _to_dataclass(cls, data: dict):
    """Convert dict to dataclass, ignoring unknown keys."""
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class RuleGroup:
    id: int = 0
    name: str = ""
    group_type: str = "custom"
    enabled: bool = True
    priority: int = 100
    metadata: str = "{}"
    created_at: int = 0
    updated_at: int = 0


@dataclass
class FirewallRule:
    id: int = 0
    group_id: int = 0
    chain: str = ""
    rule_type: str = ""
    family: int = 2
    proto: str = ""
    dport: int = 0
    sport: int = 0
    source: str = ""
    destination: str = ""
    in_iface: str = ""
    out_iface: str = ""
    state_match: str = ""
    comment: str = ""
    position: int = 0
    applied: bool = False
    nft_handle: int = 0
    created_at: int = 0


@dataclass
class RoutingRule:
    id: int = 0
    group_id: int = 0
    rule_type: str = ""
    from_network: str = ""
    to_network: str = ""
    table_name: str = ""
    table_id: int = 0
    priority: int = 0
    destination: str = ""
    device: str = ""
    fwmark: int = 0
    applied: bool = False
    created_at: int = 0


@dataclass
class FirewallStatus:
    status: str = "uninitialized"
    enabled_groups: int = 0
    firewall_rules: dict = field(default_factory=lambda: {"total": 0, "applied": 0})
    routing_rules: dict = field(default_factory=lambda: {"total": 0, "applied": 0})
    last_error: str = ""


@dataclass
class VerifyResult:
    in_sync: bool = True
    firewall: dict = field(default_factory=dict)
    routing: dict = field(default_factory=dict)
