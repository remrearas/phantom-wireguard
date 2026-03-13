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

Dataclass models for firewall_bridge — Group, FirewallRule, RoutingRule.

Mutable (frozen=False) — db.py may update fields after SQL operations.
Default values match schema.sql column defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Group:
    id: int = 0
    name: str = ""
    group_type: str = "custom"
    enabled: bool = True
    priority: int = 100
    metadata: dict = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0


@dataclass
class FirewallRule:
    id: int = 0
    group_id: int = 0
    chain: str = ""
    action: str = ""
    family: int = 2
    proto: str = ""
    dport: int = 0
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
    applied: bool = False
    created_at: int = 0
