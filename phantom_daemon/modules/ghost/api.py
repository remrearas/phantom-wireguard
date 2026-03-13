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

Ghost mode endpoints: enable, disable, status.
wstunnel server over WireGuard — censorship resistance via WebSocket/TLS.
"""

from __future__ import annotations

import base64
import logging
import ssl
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from phantom_daemon.base.errors import DaemonHTTPException
from phantom_daemon.base.services.firewall.service import (
    GHOST_PRESET_NAME,
    resolve_ghost_preset,
)
from phantom_daemon.base.services.wstunnel import open_wstunnel
from phantom_daemon.modules._envelope import ApiErr, ApiOk

log = logging.getLogger("phantom-daemon")

GHOST_BIND_URL = "wss://[::]:443"


# ── Models ───────────────────────────────────────────────────────


class EnableRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)
    tls_certificate: str = Field(min_length=1)
    tls_private_key: str = Field(min_length=1)


class GhostStatus(BaseModel):
    enabled: bool
    running: bool
    bind_url: str
    restrict_to: str
    restrict_path_prefix: str
    tls_configured: bool


# ── Router ───────────────────────────────────────────────────────

router = APIRouter(tags=["ghost"])


@router.post(
    "/enable",
    response_model=ApiOk[dict],
    status_code=201,
    responses={400: {"model": ApiErr}, 409: {"model": ApiErr}},
)
async def enable_ghost(body: EnableRequest, request: Request):
    """Enable ghost mode — start wstunnel server with TLS."""
    if request.app.state.wstunnel is not None:
        raise DaemonHTTPException(409, "GHOST_ALREADY_ACTIVE", "Ghost mode is already active")

    env = request.app.state.env
    fw = request.app.state.fw

    try:
        tls_cert_pem = base64.b64decode(body.tls_certificate).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise DaemonHTTPException(400, "INVALID_TLS_CERTIFICATE", f"Invalid tls_certificate: {exc}")

    try:
        tls_key_pem = base64.b64decode(body.tls_private_key).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise DaemonHTTPException(400, "INVALID_TLS_PRIVATE_KEY", f"Invalid tls_private_key: {exc}")

    restrict_to = f"127.0.0.1:{env.listen_port}"
    restrict_path_prefix = uuid.uuid4().hex

    tls_dir = Path(env.state_dir) / "ghost-tls"
    tls_dir.mkdir(parents=True, exist_ok=True)
    cert_path = tls_dir / "cert.pem"
    key_path = tls_dir / "key.pem"
    cert_path.write_text(tls_cert_pem)
    key_path.write_text(tls_key_pem)

    try:
        _ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        _ctx.load_cert_chain(str(cert_path), str(key_path))
    except ssl.SSLError as exc:
        cert_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)
        raise DaemonHTTPException(400, "TLS_KEYPAIR_MISMATCH", f"Certificate and private key do not match: {exc}")

    ws = open_wstunnel(state_dir=env.state_dir)

    try:
        ws.configure(
            bind_url=GHOST_BIND_URL,
            restrict_to=restrict_to,
            restrict_path_prefix=restrict_path_prefix,
            tls_certificate=str(cert_path),
            tls_private_key=str(key_path),
        )
        ws.start()
    except (RuntimeError, OSError) as exc:
        ws.close()
        raise DaemonHTTPException(400, "WSTUNNEL_START_FAILED", f"Failed to start wstunnel: {exc}")

    ghost_spec = resolve_ghost_preset()
    fw.apply_preset(ghost_spec)

    request.app.state.wstunnel = ws
    log.info("Ghost mode enabled: %s → %s", GHOST_BIND_URL, restrict_to)

    return ApiOk(data={
        "status": "enabled",
        "code": "GHOST_ENABLED",
        "domain": body.domain,
        "protocol": "wss",
        "port": 443,
        "restrict_path_prefix": restrict_path_prefix,
    })


@router.post(
    "/disable",
    response_model=ApiOk[dict],
    responses={400: {"model": ApiErr}},
)
async def disable_ghost(request: Request):
    """Disable ghost mode — stop wstunnel server and remove firewall preset."""
    wstunnel = request.app.state.wstunnel
    fw = request.app.state.fw

    if wstunnel is None:
        return ApiOk(data={"status": "already_disabled", "code": "GHOST_ALREADY_DISABLED"})

    try:
        fw.remove_preset(GHOST_PRESET_NAME)
    except (RuntimeError, OSError):
        pass

    wstunnel.stop()
    wstunnel.close()
    request.app.state.wstunnel = None

    log.info("Ghost mode disabled")
    return ApiOk(data={"status": "disabled", "code": "GHOST_DISABLED"})


@router.get("/status", response_model=ApiOk[GhostStatus])
async def ghost_status(request: Request):
    """Return current ghost mode state."""
    wstunnel = request.app.state.wstunnel

    if wstunnel is None:
        return ApiOk(data=GhostStatus(
            enabled=False,
            running=False,
            bind_url="",
            restrict_to="",
            restrict_path_prefix="",
            tls_configured=False,
        ))

    cfg = wstunnel.get_config()
    return ApiOk(data=GhostStatus(
        enabled=True,
        running=wstunnel.is_running(),
        bind_url=cfg.bind_url,
        restrict_to=cfg.restrict_to,
        restrict_path_prefix=cfg.restrict_path_prefix,
        tls_configured=bool(cfg.tls_certificate),
    ))
