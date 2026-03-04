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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from phantom_daemon.modules._envelope import ApiErr, ApiOk


# ── Models ───────────────────────────────────────────────────────


class GroupNameRequest(BaseModel):
    name: str


class GroupFilterRequest(BaseModel):
    group: Optional[str] = None


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


@router.get("/groups/list", response_model=ApiOk[list[GroupRecord]])
async def list_groups(request: Request):
    fw = request.app.state.fw
    return ApiOk(data=[GroupRecord(**vars(g)) for g in fw.list_groups()])


@router.post(
    "/groups/get",
    response_model=ApiOk[GroupRecord],
    responses={404: {"model": ApiErr}},
)
async def get_group(body: GroupNameRequest, request: Request):
    from firewall_bridge import GroupNotFoundError

    fw = request.app.state.fw
    try:
        g = fw.get_group(body.name)
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail=f"Group not found: {body.name}")
    return ApiOk(data=GroupRecord(**vars(g)))


@router.post("/rules/list", response_model=ApiOk[list[FirewallRuleRecord]])
async def list_firewall_rules(body: GroupFilterRequest, request: Request):
    fw = request.app.state.fw
    return ApiOk(data=[FirewallRuleRecord(**vars(r)) for r in fw.list_firewall_rules(body.group)])


@router.post("/routing/list", response_model=ApiOk[list[RoutingRuleRecord]])
async def list_routing_rules(body: GroupFilterRequest, request: Request):
    fw = request.app.state.fw
    return ApiOk(data=[RoutingRuleRecord(**vars(r)) for r in fw.list_routing_rules(body.group)])


@router.get("/table", response_model=ApiOk[dict])
async def list_table(request: Request):
    import json

    fw = request.app.state.fw
    raw = fw.list_table()
    return ApiOk(data=json.loads(raw) if raw else {})
