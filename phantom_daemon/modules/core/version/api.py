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

Bridge version endpoints. Import vendor packages and report versions.
"""

from __future__ import annotations

import importlib

from fastapi import APIRouter
from pydantic import BaseModel

from phantom_daemon import __version__

router = APIRouter(tags=["version"])


# ── Models ───────────────────────────────────────────────────────

class BridgeVersion(BaseModel):
    name: str
    version: str | None
    available: bool
    error: str | None = None


class AllVersionsResponse(BaseModel):
    daemon: str
    bridges: list[BridgeVersion]


# ── Bridge registry ──────────────────────────────────────────────

_BRIDGES = {
    "wireguard-go-bridge": "wireguard_go_bridge",
    "firewall-bridge": "firewall_bridge",
    "wstunnel-bridge": "wstunnel_bridge",
}


def _probe_bridge(slug: str) -> BridgeVersion:
    module_name = _BRIDGES[slug]
    try:
        mod = importlib.import_module(module_name)
        return BridgeVersion(
            name=slug,
            version=getattr(mod, "__version__", None),
            available=True,
        )
    except ImportError as exc:
        return BridgeVersion(
            name=slug,
            version=None,
            available=False,
            error=str(exc),
        )


# ── Endpoints ────────────────────────────────────────────────────

@router.get("", response_model=AllVersionsResponse)
async def all_versions() -> AllVersionsResponse:
    return AllVersionsResponse(
        daemon=__version__,
        bridges=[_probe_bridge(slug) for slug in _BRIDGES],
    )


@router.get("/wireguard-go-bridge", response_model=BridgeVersion)
async def wireguard_go_bridge_version() -> BridgeVersion:
    return _probe_bridge("wireguard-go-bridge")


@router.get("/firewall-bridge", response_model=BridgeVersion)
async def firewall_bridge_version() -> BridgeVersion:
    return _probe_bridge("firewall-bridge")


@router.get("/wstunnel-bridge", response_model=BridgeVersion)
async def wstunnel_bridge_version() -> BridgeVersion:
    return _probe_bridge("wstunnel-bridge")