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

Firewall read-only endpoints: groups, rules, routing, nftables table.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from phantom_daemon.modules.core._errors import ErrorResponse


# ── Models ───────────────────────────────────────────────────────


class GroupRecord(BaseModel):
    id: int
    name: str
    group_type: str
    enabled: bool
    priority: int
    metadata: dict
    created_at: int
    updated_at: int


class FirewallRuleRecord(BaseModel):
    id: int
    group_id: int
    chain: str
    action: str
    family: int
    proto: str
    dport: int
    source: str
    destination: str
    in_iface: str
    out_iface: str
    state_match: str
    comment: str
    position: int
    applied: bool
    nft_handle: int
    created_at: int


class RoutingRuleRecord(BaseModel):
    id: int
    group_id: int
    rule_type: str
    from_network: str
    to_network: str
    table_name: str
    table_id: int
    priority: int
    destination: str
    device: str
    applied: bool
    created_at: int


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["firewall"])


@router.get("/groups", response_model=list[GroupRecord])
async def list_groups(request: Request) -> list[GroupRecord]:
    fw = request.app.state.fw
    return [GroupRecord(**vars(g)) for g in fw.list_groups()]


@router.get(
    "/groups/{name}",
    response_model=GroupRecord,
    responses={404: {"model": ErrorResponse}},
)
async def get_group(name: str, request: Request) -> GroupRecord:
    from firewall_bridge import GroupNotFoundError

    fw = request.app.state.fw
    try:
        g = fw.get_group(name)
    except GroupNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Group not found: {name}")
    return GroupRecord(**vars(g))


@router.get("/rules", response_model=list[FirewallRuleRecord])
async def list_firewall_rules(
    request: Request, group: Optional[str] = None,
) -> list[FirewallRuleRecord]:
    fw = request.app.state.fw
    return [FirewallRuleRecord(**vars(r)) for r in fw.list_firewall_rules(group)]


@router.get("/routing", response_model=list[RoutingRuleRecord])
async def list_routing_rules(
    request: Request, group: Optional[str] = None,
) -> list[RoutingRuleRecord]:
    fw = request.app.state.fw
    return [RoutingRuleRecord(**vars(r)) for r in fw.list_routing_rules(group)]


@router.get("/table")
async def list_table(request: Request) -> dict:
    import json

    fw = request.app.state.fw
    raw = fw.list_table()
    return json.loads(raw) if raw else {}
