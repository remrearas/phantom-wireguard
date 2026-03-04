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

Client CRUD endpoints: assign, list, get, revoke.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from phantom_daemon.base.errors import WalletError
from phantom_daemon.modules.core._errors import ErrorResponse


# ── Models ───────────────────────────────────────────────────────


class AssignClientRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


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


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["clients"])


@router.post(
    "",
    response_model=ClientRecord,
    status_code=201,
    responses={409: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def assign_client(body: AssignClientRequest, request: Request) -> ClientRecord:
    wallet = request.app.state.wallet
    wg = request.app.state.wg
    env = request.app.state.env

    result = wallet.assign_client(body.name)
    try:
        wg.add_peer(result, env.keepalive)
    except Exception:
        wallet.revoke_client(body.name)
        raise
    return ClientRecord(**result)


@router.get("", response_model=ClientListResponse)
async def list_clients(request: Request) -> ClientListResponse:
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
    return ClientListResponse(clients=summaries, total=len(summaries))


@router.get(
    "/{name}",
    response_model=ClientRecord,
    responses={404: {"model": ErrorResponse}},
)
async def get_client(name: str, request: Request) -> ClientRecord:
    wallet = request.app.state.wallet
    result = wallet.get_client(name)
    if result is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientRecord(**result)


@router.delete(
    "/{name}",
    responses={400: {"model": ErrorResponse}},
)
async def revoke_client(name: str, request: Request) -> dict:
    wallet = request.app.state.wallet
    wg = request.app.state.wg
    env = request.app.state.env

    client = wallet.get_client(name)
    if client is None:
        raise WalletError(f"Client not found: {name}")

    wg.remove_peer(client["public_key_hex"])
    try:
        wallet.revoke_client(name)
    except Exception:
        wg.add_peer(client, env.keepalive)
        raise
    return {"status": "revoked"}
