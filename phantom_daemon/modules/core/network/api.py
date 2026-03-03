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

Network status, CIDR change, and pool validation endpoints.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from phantom_daemon.modules.core._errors import ErrorResponse


# ── Models ───────────────────────────────────────────────────────


class PoolStats(BaseModel):
    total: int
    assigned: int
    free: int


class DnsDetail(BaseModel):
    primary: str
    secondary: str


class NetworkStatus(BaseModel):
    ipv4_subnet: str
    ipv6_subnet: str
    dns_v4: DnsDetail
    dns_v6: DnsDetail
    pool: PoolStats


class ChangeCidrRequest(BaseModel):
    prefix: int = Field(ge=16, le=30)


class ChangeCidrResponse(BaseModel):
    ipv4_subnet: str
    ipv6_subnet: str
    pool: PoolStats


class ValidatePoolResponse(BaseModel):
    valid: bool
    errors: list[str]


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["network"])


@router.get("", response_model=NetworkStatus)
async def network_status(request: Request) -> NetworkStatus:
    wallet = request.app.state.wallet
    config = wallet.get_all_config()
    dns_v4 = json.loads(config["dns_v4"])
    dns_v6 = json.loads(config["dns_v6"])
    return NetworkStatus(
        ipv4_subnet=config["ipv4_subnet"],
        ipv6_subnet=config["ipv6_subnet"],
        dns_v4=DnsDetail(**dns_v4),
        dns_v6=DnsDetail(**dns_v6),
        pool=PoolStats(
            total=wallet.count_users(),
            assigned=wallet.count_assigned(),
            free=wallet.count_free(),
        ),
    )


@router.put(
    "/cidr",
    response_model=ChangeCidrResponse,
    responses={400: {"model": ErrorResponse}},
)
async def change_cidr(body: ChangeCidrRequest, request: Request) -> ChangeCidrResponse:
    wallet = request.app.state.wallet
    wallet.change_cidr(body.prefix)
    config = wallet.get_all_config()
    return ChangeCidrResponse(
        ipv4_subnet=config["ipv4_subnet"],
        ipv6_subnet=config["ipv6_subnet"],
        pool=PoolStats(
            total=wallet.count_users(),
            assigned=wallet.count_assigned(),
            free=wallet.count_free(),
        ),
    )


@router.get("/validate", response_model=ValidatePoolResponse)
async def validate_pool(request: Request) -> ValidatePoolResponse:
    wallet = request.app.state.wallet
    errors = wallet.validate_pool()
    return ValidatePoolResponse(valid=len(errors) == 0, errors=errors)
