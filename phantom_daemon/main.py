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
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from phantom_daemon import __version__
from phantom_daemon.base import (
    StartupError,
    WalletError,
    WalletFullError,
    load_env,
    load_secrets,
    open_wallet,
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

        app.state.server_keys = server_keys
        app.state.env = env
        app.state.wallet = wallet
    except StartupError as exc:
        log.critical("Startup failed: %s", exc)
        sys.exit(1)

    yield

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
    """Register global exception handlers for wallet errors."""

    @app.exception_handler(WalletFullError)
    async def _wallet_full(request, exc):  # noqa: ARG001
        return JSONResponse(
            status_code=409,
            content={"error": "pool_exhausted", "detail": str(exc)},
        )

    @app.exception_handler(WalletError)
    async def _wallet_error(request, exc):  # noqa: ARG001
        return JSONResponse(
            status_code=400,
            content={"error": "wallet_error", "detail": str(exc)},
        )


def main() -> None:
    socket_path = "/var/run/phantom-daemon.sock"
    if len(sys.argv) > 1:
        socket_path = sys.argv[1]

    app = create_app()
    uvicorn.run(app, uds=socket_path, log_level="info")


if __name__ == "__main__":
    main()
