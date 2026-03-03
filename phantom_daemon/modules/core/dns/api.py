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

from phantom_daemon.modules.core._errors import ErrorResponse


# ── Models ───────────────────────────────────────────────────────


class DnsRecord(BaseModel):
    family: str
    primary: str
    secondary: str


class ChangeDnsRequest(BaseModel):
    primary: str
    secondary: str


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["dns"])


@router.get("/{family}", response_model=DnsRecord)
async def get_dns(family: Literal["v4", "v6"], request: Request) -> DnsRecord:
    wallet = request.app.state.wallet
    dns = wallet.get_dns(family)
    return DnsRecord(family=family, **dns)


@router.put(
    "/{family}",
    response_model=DnsRecord,
    responses={400: {"model": ErrorResponse}},
)
async def change_dns(
    family: Literal["v4", "v6"],
    body: ChangeDnsRequest,
    request: Request,
) -> DnsRecord:
    wallet = request.app.state.wallet
    wallet.change_dns(family, body.primary, body.secondary)
    dns = wallet.get_dns(family)
    return DnsRecord(family=family, **dns)
