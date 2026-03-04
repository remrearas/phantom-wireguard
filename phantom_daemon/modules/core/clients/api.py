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

Client CRUD endpoints: assign, list, get, revoke, config export.
"""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from phantom_daemon.base.errors import WalletError
from phantom_daemon.base.services.wireguard.config import build_client_config
from phantom_daemon.modules._envelope import ApiErr, ApiOk


# ── Models ───────────────────────────────────────────────────────


class ClientNameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class ConfigExportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    version: Literal["v4", "v6", "hybrid"]


class ClientRecord(BaseModel):
    id: str
    name: str
    ipv4_address: str
    ipv6_address: str
    private_key_hex: str
    public_key_hex: str
    preshared_key_hex: str
    created_at: str
    updated_at: str


class ClientSummary(BaseModel):
    id: str
    name: str
    ipv4_address: str
    ipv6_address: str
    public_key_hex: str
    created_at: str
    updated_at: str


class ClientListResponse(BaseModel):
    clients: list[ClientSummary]
    total: int


class RevokeResponse(BaseModel):
    status: str


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["clients"])


@router.post(
    "/assign",
    response_model=ApiOk[ClientRecord],
    status_code=201,
    responses={400: {"model": ApiErr}, 409: {"model": ApiErr}},
)
async def assign_client(body: ClientNameRequest, request: Request):
    wallet = request.app.state.wallet
    wg = request.app.state.wg
    env = request.app.state.env

    result = wallet.assign_client(body.name)
    try:
        wg.add_peer(result, env.keepalive)
    except Exception:
        wallet.revoke_client(body.name)
        raise
    return ApiOk(data=ClientRecord(**result))


@router.get("/list", response_model=ApiOk[ClientListResponse])
async def list_clients(request: Request):
    wallet = request.app.state.wallet
    clients = wallet.list_clients()
    summaries = [
        ClientSummary(
            id=c["id"],
            name=c["name"],
            ipv4_address=c["ipv4_address"],
            ipv6_address=c["ipv6_address"],
            public_key_hex=c["public_key_hex"],
            created_at=c["created_at"],
            updated_at=c["updated_at"],
        )
        for c in clients
    ]
    return ApiOk(data=ClientListResponse(clients=summaries, total=len(summaries)))


@router.post(
    "/get",
    response_model=ApiOk[ClientRecord],
    responses={404: {"model": ApiErr}},
)
async def get_client(body: ClientNameRequest, request: Request):
    wallet = request.app.state.wallet
    result = wallet.get_client(body.name)
    if result is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return ApiOk(data=ClientRecord(**result))


@router.post(
    "/config",
    response_model=ApiOk[str],
    responses={400: {"model": ApiErr}, 404: {"model": ApiErr}},
)
async def export_config(body: ConfigExportRequest, request: Request):
    wallet = request.app.state.wallet
    env = request.app.state.env
    server_keys = request.app.state.server_keys

    client = wallet.get_client(body.name)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Endpoint validation
    if body.version in ("v4", "hybrid") and not env.endpoint_v4:
        raise HTTPException(status_code=400, detail="endpoint_v4 is not configured")
    if body.version in ("v6", "hybrid") and not env.endpoint_v6:
        raise HTTPException(status_code=400, detail="endpoint_v6 is not configured")

    # Resolve endpoint for config
    if body.version in ("v4", "hybrid"):
        endpoint = f"{env.endpoint_v4}:{env.listen_port}"
    else:
        endpoint = f"{env.endpoint_v6}:{env.listen_port}"

    dns_v4 = wallet.get_dns("v4")
    dns_v6 = wallet.get_dns("v6")

    conf = build_client_config(
        version=body.version,
        client_private_key_hex=client["private_key_hex"],
        client_ipv4=client["ipv4_address"],
        client_ipv6=client["ipv6_address"],
        server_public_key_hex=server_keys.public_key_hex,
        preshared_key_hex=client["preshared_key_hex"],
        dns_v4=dns_v4,
        dns_v6=dns_v6,
        endpoint=endpoint,
        keepalive=env.keepalive,
        mtu=env.mtu,
    )
    b64 = base64.b64encode(conf.encode()).decode()
    return ApiOk(data=b64)


@router.post(
    "/revoke",
    response_model=ApiOk[RevokeResponse],
    responses={400: {"model": ApiErr}},
)
async def revoke_client(body: ClientNameRequest, request: Request):
    wallet = request.app.state.wallet
    wg = request.app.state.wg
    env = request.app.state.env

    client = wallet.get_client(body.name)
    if client is None:
        raise WalletError(f"Client not found: {body.name}")

    wg.remove_peer(client["public_key_hex"])
    try:
        wallet.revoke_client(body.name)
    except Exception:
        wg.add_peer(client, env.keepalive)
        raise
    return ApiOk(data=RevokeResponse(status="revoked"))
