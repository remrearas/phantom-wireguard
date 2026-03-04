"""Fixtures for wallet-backed API integration tests.

Each pytest session creates a fresh wallet database.
The database is preserved after the session for inspection.

Run with -s to see the DB path:
    pytest tests/modules/core/ -s
"""

from __future__ import annotations

import functools
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from phantom_daemon.base.env import DaemonEnv
from phantom_daemon.base.secrets.secrets import ServerKeys
from phantom_daemon.base.wallet import Wallet, open_wallet
from phantom_daemon.base.services.wireguard.service import open_wireguard
from phantom_daemon.main import create_app
from wireguard_go_bridge.keys import generate_private_key, derive_public_key

# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)

_DB_DIR = "/var/lib/phantom/db/tests"
_STATE_DIR = "/var/lib/phantom/state/db/tests"

_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


@pytest.fixture(scope="session")
def wallet():
    """Session-scoped wallet with a fresh database."""
    os.makedirs(_DB_DIR, exist_ok=True)
    db_name = f"api-{_ts}.db"
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


@pytest.fixture(scope="session")
def env():
    """DaemonEnv with test paths."""
    state_dir = os.path.join(_STATE_DIR, f"api-{_ts}")
    os.makedirs(state_dir, exist_ok=True)
    print(f"\n  API State Dir: {state_dir}")
    return DaemonEnv(
        db_dir=_DB_DIR,
        state_dir=state_dir,
        listen_port=51820,
        mtu=1420,
        keepalive=25,
        endpoint_v4="",
        endpoint_v6="",
    )


@pytest.fixture(scope="session")
def wg(env):
    """Session-scoped WireGuard service for API tests."""
    tag = hashlib.md5(_ts.encode()).hexdigest()[:6]
    svc = open_wireguard(state_dir=env.state_dir, mtu=env.mtu, ifname=f"wg_t_{tag}")
    yield svc
    svc.down()
    svc.close()


@pytest.fixture(scope="session")
def server_keys():
    """Session-scoped server key pair for config export tests."""
    priv = generate_private_key()
    pub = derive_public_key(priv)
    return ServerKeys(private_key_hex=priv, public_key_hex=pub)


@pytest.fixture()
def client(wallet, wg, env, server_keys):
    """ASGI test client with wallet + wg + env + server_keys on app.state."""
    app = create_app(lifespan_func=None)
    app.state.wallet = wallet
    app.state.wg = wg
    app.state.env = env
    app.state.server_keys = server_keys
    with TestClient(app) as c:
        yield c
