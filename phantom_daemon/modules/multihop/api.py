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

Multihop exit tunnel endpoints: import, remove, list, enable, disable, status.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from phantom_daemon.base.errors import DaemonHTTPException
from phantom_daemon.base.exit_store import parse_wireguard_config
from phantom_daemon.base.services.firewall.service import (
    MULTIHOP_PRESET_NAME,
    resolve_multihop_preset,
)
from phantom_daemon.base.services.wireguard import WG_INTERFACE_NAME_EXIT
from phantom_daemon.base.services.wireguard.ipc import build_exit_config
from phantom_daemon.base.services.wireguard.service import open_wireguard
from phantom_daemon.modules._envelope import ApiErr, ApiOk


# ── Models ───────────────────────────────────────────────────────


class ImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    config: str = Field(min_length=1)


class ExitNameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class ExitSummary(BaseModel):
    id: str
    name: str
    endpoint: str
    address: str
    public_key_hex: str
    allowed_ips: str
    keepalive: int


class ExitListResponse(BaseModel):
    exits: list[ExitSummary]
    total: int
    enabled: bool
    active: str


class MultihopStatus(BaseModel):
    enabled: bool
    active: str
    exit: ExitSummary | None


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["multihop"])


@router.post(
    "/import",
    response_model=ApiOk[ExitSummary],
    status_code=201,
    responses={400: {"model": ApiErr}},
)
async def import_exit(body: ImportRequest, request: Request):
    """Import a WireGuard .conf as an exit configuration."""
    exit_store = request.app.state.exit_store

    try:
        parsed = parse_wireguard_config(body.config)
    except ValueError as exc:
        raise DaemonHTTPException(400, "INVALID_EXIT_CONFIG", str(exc))

    result = exit_store.add_exit(
        name=body.name,
        endpoint=parsed.endpoint,
        address=parsed.address,
        private_key_hex=parsed.private_key_hex,
        public_key_hex=parsed.public_key_hex,
        preshared_key_hex=parsed.preshared_key_hex,
        allowed_ips=parsed.allowed_ips,
        keepalive=parsed.keepalive,
    )
    return ApiOk(data=ExitSummary(
        id=result["id"],
        name=result["name"],
        endpoint=result["endpoint"],
        address=result["address"],
        public_key_hex=result["public_key_hex"],
        allowed_ips=result["allowed_ips"],
        keepalive=result["keepalive"],
    ))


@router.post(
    "/remove",
    response_model=ApiOk[dict],
    responses={400: {"model": ApiErr}},
)
async def remove_exit(body: ExitNameRequest, request: Request):
    """Remove an exit configuration. Must not be active."""
    exit_store = request.app.state.exit_store
    exit_store.remove_exit(body.name)
    return ApiOk(data={"status": "removed", "code": "EXIT_REMOVED"})


@router.get("/list", response_model=ApiOk[ExitListResponse])
async def list_exits(request: Request):
    """List all exit configurations and current state."""
    exit_store = request.app.state.exit_store
    exits = exit_store.list_exits()
    summaries = [
        ExitSummary(
            id=e["id"],
            name=e["name"],
            endpoint=e["endpoint"],
            address=e["address"],
            public_key_hex=e["public_key_hex"],
            allowed_ips=e["allowed_ips"],
            keepalive=e["keepalive"],
        )
        for e in exits
    ]
    return ApiOk(data=ExitListResponse(
        exits=summaries,
        total=len(summaries),
        enabled=exit_store.is_enabled(),
        active=exit_store.get_active(),
    ))


@router.post(
    "/enable",
    response_model=ApiOk[dict],
    responses={400: {"model": ApiErr}, 404: {"model": ApiErr}},
)
async def enable_multihop(body: ExitNameRequest, request: Request):
    """Enable multihop with the given exit.

    Three scenarios:
    1. Fresh enable — create device, ipc_set, up, apply interface, firewall preset.
    2. Switch — ipc_set on existing device, update address if changed.
    3. Already active — no-op.
    """
    exit_store = request.app.state.exit_store
    env = request.app.state.env
    wallet = request.app.state.wallet
    fw = request.app.state.fw
    wg_exit = request.app.state.wg_exit

    exit_data = exit_store.get_exit(body.name)
    if exit_data is None:
        raise DaemonHTTPException(404, "EXIT_NOT_FOUND", f"Exit not found: {body.name}")

    active = exit_store.get_active()

    if exit_store.is_enabled() and active == body.name:
        return ApiOk(data={"status": "already_active", "code": "MULTIHOP_ALREADY_ACTIVE"})

    config = build_exit_config(
        private_key_hex=exit_data["private_key_hex"],
        peer_public_key_hex=exit_data["public_key_hex"],
        peer_preshared_key_hex=exit_data["preshared_key_hex"],
        endpoint=exit_data["endpoint"],
        allowed_ips=exit_data["allowed_ips"],
        keepalive=exit_data["keepalive"],
    )

    if wg_exit is None:
        wg_exit = open_wireguard(
            state_dir=env.state_dir, mtu=env.mtu,
            ifname=WG_INTERFACE_NAME_EXIT,
        )
        wg_exit._bridge.ipc_set(config)
        wg_exit.up()
        wg_exit.apply_exit_interface(exit_data["address"])

        ipv4_subnet = wallet.get_config("ipv4_subnet") or ""
        mh_spec = resolve_multihop_preset(ipv4_subnet=ipv4_subnet)
        fw.apply_preset(mh_spec)

        request.app.state.wg_exit = wg_exit
    else:
        wg_exit._bridge.ipc_set(config)

        if active and active != body.name:
            old_data = exit_store.get_exit(active)
            if old_data and old_data["address"] != exit_data["address"]:
                wg_exit.update_exit_address(exit_data["address"])

    exit_store.activate(body.name)
    return ApiOk(data={"status": "enabled", "code": "MULTIHOP_ENABLED"})


@router.post(
    "/disable",
    response_model=ApiOk[dict],
    responses={400: {"model": ApiErr}},
)
async def disable_multihop(request: Request):
    """Disable multihop — tear down exit device and remove firewall preset."""
    exit_store = request.app.state.exit_store
    fw = request.app.state.fw
    wg_exit = request.app.state.wg_exit

    if not exit_store.is_enabled():
        return ApiOk(data={"status": "already_disabled", "code": "MULTIHOP_ALREADY_DISABLED"})

    try:
        fw.remove_preset(MULTIHOP_PRESET_NAME)
    except (RuntimeError, OSError):
        pass

    if wg_exit is not None:
        wg_exit.down()
        wg_exit.close()
        request.app.state.wg_exit = None

    exit_store.deactivate()
    return ApiOk(data={"status": "disabled", "code": "MULTIHOP_DISABLED"})


@router.get("/status", response_model=ApiOk[MultihopStatus])
async def multihop_status(request: Request):
    """Return current multihop state and active exit info."""
    exit_store = request.app.state.exit_store
    enabled = exit_store.is_enabled()
    active = exit_store.get_active()

    exit_summary = None
    if active:
        exit_data = exit_store.get_exit(active)
        if exit_data:
            exit_summary = ExitSummary(
                id=exit_data["id"],
                name=exit_data["name"],
                endpoint=exit_data["endpoint"],
                address=exit_data["address"],
                public_key_hex=exit_data["public_key_hex"],
                allowed_ips=exit_data["allowed_ips"],
                keepalive=exit_data["keepalive"],
            )

    return ApiOk(data=MultihopStatus(
        enabled=enabled,
        active=active,
        exit=exit_summary,
    ))
