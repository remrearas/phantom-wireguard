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

Application factory and Uvicorn runner over Unix Domain Socket.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from phantom_daemon import __version__
from phantom_daemon.base import (
    StartupError,
    WalletError,
    WalletFullError,
    load_env,
    load_secrets,
    open_firewall,
    open_wallet,
    open_wireguard,
)
from phantom_daemon.modules import setup_routers

log = logging.getLogger("phantom-daemon")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Daemon startup/shutdown lifecycle."""
    try:
        # Phase 1: secrets
        server_keys = load_secrets()

        # Phase 2: environment + wallet
        env = load_env()
        wallet = open_wallet(db_dir=env.db_dir)

        # Phase 3a: WireGuard bridge
        wg = open_wireguard(state_dir=env.state_dir, mtu=env.mtu)
        wg.fast_sync(wallet=wallet, server_keys=server_keys, env=env)
        wg.up()

        # Phase 3a+: OS-level interface setup
        wg.apply_interface(
            ipv4_subnet=wallet.get_config("ipv4_subnet"),
            ipv6_subnet=wallet.get_config("ipv6_subnet"),
        )

        # Phase 3b: Firewall bridge
        fw = open_firewall(state_dir=env.state_dir)
        if not fw.list_groups():
            fw.bootstrap(env=env, wallet=wallet)
        fw.start()

        app.state.server_keys = server_keys
        app.state.env = env
        app.state.wallet = wallet
        app.state.wg = wg
        app.state.fw = fw
    except StartupError as exc:
        log.critical("Startup failed: %s", exc)
        sys.exit(1)

    yield

    fw.stop()
    fw.close()
    wg.down()
    wg.close()
    wallet.close()


def create_app(
    lifespan_func: Optional[object] = lifespan,
) -> FastAPI:
    app = FastAPI(
        title="phantom-daemon",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan_func,
    )
    setup_routers(app)
    _register_error_handlers(app)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers — all errors return ApiErr envelope."""

    @app.exception_handler(HTTPException)
    async def _http_error(_request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "error": exc.detail},
        )

    @app.exception_handler(WalletFullError)
    async def _wallet_full(_request, exc):
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": str(exc)},
        )

    @app.exception_handler(WalletError)
    async def _wallet_error(_request, exc):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_request, exc):
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": str(exc)},
        )


def main() -> None:
    socket_path = "/var/run/phantom-daemon.sock"
    if len(sys.argv) > 1:
        socket_path = sys.argv[1]

    app = create_app()
    uvicorn.run(app, uds=socket_path, log_level="info")


if __name__ == "__main__":
    main()
