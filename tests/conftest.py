"""Shared fixtures for phantom-daemon tests.

Transport modes:
    default   → ASGI in-process (TestClient, no socket)
    --uds     → real HTTP over UDS (httpx, running daemon required)

Both modes return an httpx-compatible client — tests stay identical.
"""

from __future__ import annotations

from typing import Generator

import httpx
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from phantom_daemon.main import create_app

UDS_DEFAULT = "/var/run/phantom/daemon.sock"


# ── CLI flags ────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--uds",
        default=None,
        help=f"Run tests over UDS against a running daemon (default path: {UDS_DEFAULT})",
    )


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture()
def app() -> FastAPI:
    return create_app(lifespan_func=None)


@pytest.fixture()
def client(request: pytest.FixtureRequest, app: FastAPI) -> Generator[httpx.Client]:
    """Transport-agnostic HTTP client.

    ASGI mode → TestClient(app)           — in-process, instant
    UDS mode  → httpx over Unix socket    — real HTTP, real daemon
    """
    uds_path = request.config.getoption("--uds")
    if uds_path is not None:
        uds_path = uds_path or UDS_DEFAULT
        transport = httpx.HTTPTransport(uds=uds_path)
        with httpx.Client(transport=transport, base_url="http://daemon") as c:
            yield c
    else:
        with TestClient(app) as c:
            yield c
