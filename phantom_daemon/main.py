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

import sys

import uvicorn
from fastapi import FastAPI

from phantom_daemon import __version__
from phantom_daemon.modules import setup_routers


def create_app() -> FastAPI:
    app = FastAPI(
        title="phantom-daemon",
        version=__version__,
        docs_url=None,
        redoc_url=None,
    )
    setup_routers(app)
    return app


def main() -> None:
    socket_path = "/var/run/phantom-daemon.sock"
    if len(sys.argv) > 1:
        socket_path = sys.argv[1]

    app = create_app()
    uvicorn.run(app, uds=socket_path, log_level="info")


if __name__ == "__main__":
    main()
