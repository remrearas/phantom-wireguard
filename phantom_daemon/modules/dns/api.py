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

DNS configuration endpoints: read and update per address family.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from phantom_daemon.modules._envelope import ApiErr, ApiOk


# ── Models ───────────────────────────────────────────────────────


class DnsFamilyRequest(BaseModel):
    family: Literal["v4", "v6"]


class DnsRecord(BaseModel):
    family: str
    primary: str
    secondary: str


class ChangeDnsRequest(BaseModel):
    family: Literal["v4", "v6"]
    primary: str
    secondary: str


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["dns"])


@router.post("/get", response_model=ApiOk[DnsRecord])
async def get_dns(body: DnsFamilyRequest, request: Request):
    wallet = request.app.state.wallet
    dns = wallet.get_dns(body.family)
    return ApiOk(data=DnsRecord(family=body.family, **dns))


@router.post(
    "/change",
    response_model=ApiOk[DnsRecord],
    responses={400: {"model": ApiErr}},
)
async def change_dns(body: ChangeDnsRequest, request: Request):
    wallet = request.app.state.wallet
    wallet.change_dns(body.family, body.primary, body.secondary)
    dns = wallet.get_dns(body.family)
    return ApiOk(data=DnsRecord(family=body.family, **dns))
