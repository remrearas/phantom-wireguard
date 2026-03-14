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

Health-check endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from phantom_daemon.modules._envelope import ApiOk


class HelloResponse(BaseModel):
    message: str
    version: str


router = APIRouter(tags=["hello"])


@router.get("", response_model=ApiOk[HelloResponse])
async def hello():
    from phantom_daemon import __version__

    return ApiOk(data=HelloResponse(
        message="phantom-daemon is running",
        version=__version__,
    ))


@router.get("/openapi", include_in_schema=False)
async def openapi_schema(request: Request):
    return JSONResponse(content=request.app.openapi())
