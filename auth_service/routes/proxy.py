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

Authenticated reverse proxy to daemon UDS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from auth_service.crypto.jwt import TokenPayload
from auth_service.middleware.auth import require_auth

router = APIRouter(prefix="/api", tags=["proxy"])


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy(
    path: str,
    request: Request,
    _payload: TokenPayload = Depends(require_auth),
):
    """Forward authenticated request to daemon over UDS."""
    client = request.app.state.proxy_client
    target_url = f"http://daemon/api/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body()

    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ("host", "authorization", "content-length", "transfer-encoding"):
            headers[key] = value

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body if body else None,
            headers=headers,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": f"Daemon unreachable: {exc}"},
        )

    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        data = response.json()
    else:
        data = {"ok": True, "data": response.text}

    return JSONResponse(
        status_code=response.status_code,
        content=data,
        headers={
            k: v
            for k, v in response.headers.items()
            if k.lower() not in ("content-length", "transfer-encoding", "content-encoding")
        },
    )
