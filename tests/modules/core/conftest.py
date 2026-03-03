"""Fixtures for wallet-backed API integration tests.

Each pytest session creates a fresh wallet database.
The database is preserved after the session for inspection.

Run with -s to see the DB path:
    pytest tests/modules/core/ -s
"""

from __future__ import annotations

import functools
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from phantom_daemon.base.wallet import Wallet, open_wallet
from phantom_daemon.main import create_app

# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)

_DB_DIR = "/var/lib/phantom/db/tests"


@pytest.fixture(scope="session")
def wallet():
    """Session-scoped wallet with a fresh database."""
    os.makedirs(_DB_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    db_name = f"api-{ts}.db"
    db_path = os.path.join(_DB_DIR, db_name)
    print(f"\n  API Test DB: {db_path}")
    # Create DB with schema + defaults, then reopen with
    # check_same_thread=False so Starlette TestClient (separate thread)
    # can share the same connection for endpoint handling.
    w = open_wallet(db_dir=_DB_DIR, db_name=db_name)
    w.close()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    w = Wallet(conn, Path(db_path))
    yield w
    print(f"\n  DB preserved: {db_path}")
    w.close()


@pytest.fixture()
def client(wallet):
    """ASGI test client with wallet on app.state."""
    app = create_app(lifespan_func=None)
    app.state.wallet = wallet
    with TestClient(app) as c:
        yield c
