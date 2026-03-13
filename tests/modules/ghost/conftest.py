"""Fixtures for ghost module integration tests.

Firewall uses a stub — the real nft context is held by the running
daemon process (global static in Rust FFI), so a second init panics.
The stub records apply/remove calls without touching nftables.

Run with -s to see paths:
    pytest tests/modules/ghost/ -s
"""

from __future__ import annotations

import functools
import hashlib
import os
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from phantom_daemon.base.env import DaemonEnv
from phantom_daemon.base.secrets.secrets import ServerKeys
from phantom_daemon.base.exit_store import ExitStore, open_exit_store
from phantom_daemon.base.wallet import Wallet, open_wallet
from phantom_daemon.base.services.wireguard.service import WireGuardService, open_wireguard
from phantom_daemon.main import create_app
from wireguard_go_bridge.keys import generate_private_key, derive_public_key

# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)

_DB_DIR = "/var/lib/phantom/db/tests"
_STATE_DIR = "/var/lib/phantom/state/db/tests"


# ── Firewall stub ───────────────────────────────────────────────


@dataclass
class FirewallStub:
    """No-op firewall for tests — records preset calls."""

    presets: list[str] = field(default_factory=list)

    def apply_preset(self, preset, **_kw):
        self.presets.append(str(preset))

    def remove_preset(self, name: str):
        self.presets = [p for p in self.presets if name not in p]


# ── Environment ─────────────────────────────────────────────────


@dataclass
class GhostTestEnvironment:
    """Self-contained ghost test session environment."""

    wallet: Wallet
    env: DaemonEnv
    wg: WireGuardService
    server_keys: ServerKeys
    exit_store: ExitStore
    fw: FirewallStub


@pytest.fixture(scope="session")
def test_env():
    """Session-scoped environment — wallet, env, wg, server_keys, fw stub."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    port = random.randint(51800, 51899)

    # Wallet
    os.makedirs(_DB_DIR, exist_ok=True)
    db_name = f"ghost-{ts}.db"
    db_path = os.path.join(_DB_DIR, db_name)
    print(f"\n  Ghost Test DB: {db_path}")
    w = open_wallet(db_dir=_DB_DIR, db_name=db_name)
    w.close()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    wallet = Wallet(conn, Path(db_path))

    # Env
    state_dir = os.path.join(_STATE_DIR, f"ghost-{ts}")
    os.makedirs(state_dir, exist_ok=True)
    print(f"\n  Ghost State Dir: {state_dir}")
    print(f"\n  Ghost Listen Port: {port}")
    env = DaemonEnv(
        db_dir=_DB_DIR,
        state_dir=state_dir,
        listen_port=port,
        mtu=1420,
        keepalive=25,
        endpoint_v4="",
        endpoint_v6="",
    )

    # WireGuard
    tag = hashlib.md5(ts.encode()).hexdigest()[:6]
    wg = open_wireguard(state_dir=env.state_dir, mtu=env.mtu, ifname=f"wg_g_{tag}")

    # Server keys
    priv = generate_private_key()
    pub = derive_public_key(priv)
    server_keys = ServerKeys(private_key_hex=priv, public_key_hex=pub)

    # Exit store
    exit_db_name = f"exit-ghost-{ts}.db"
    es = open_exit_store(db_dir=_DB_DIR, db_name=exit_db_name)
    es.close()
    exit_db_path = os.path.join(_DB_DIR, exit_db_name)
    exit_conn = sqlite3.connect(exit_db_path, check_same_thread=False)
    exit_store = ExitStore(exit_conn, Path(exit_db_path))

    yield GhostTestEnvironment(
        wallet=wallet, env=env, wg=wg, server_keys=server_keys,
        exit_store=exit_store, fw=FirewallStub(),
    )

    wg.down()
    wg.close()
    exit_store.close()
    print(f"\n  Ghost DB preserved: {db_path}")
    wallet.close()


@pytest.fixture()
def client(test_env):
    """ASGI test client with full environment on app.state."""
    app = create_app(lifespan_func=None)
    app.state.wallet = test_env.wallet
    app.state.wg = test_env.wg
    app.state.env = test_env.env
    app.state.server_keys = test_env.server_keys
    app.state.exit_store = test_env.exit_store
    app.state.fw = test_env.fw
    app.state.wg_exit = None
    app.state.wstunnel = None
    with TestClient(app) as c:
        yield c