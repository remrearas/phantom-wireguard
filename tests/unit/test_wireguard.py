"""Tests for phantom_daemon.base.services.wireguard — real bridge, real wallet, no mocks."""

from __future__ import annotations

import functools
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from phantom_daemon.base.errors import WireGuardError
from phantom_daemon.base.env import DaemonEnv
from phantom_daemon.base.secrets.secrets import ServerKeys
from phantom_daemon.base.wallet import open_wallet
from phantom_daemon.base.services.wireguard.ipc import parse_ipc_peers
from phantom_daemon.base.services.wireguard.service import (
    WireGuardService,
    _ensure_device_db,
    open_wireguard,
)
from wireguard_go_bridge import generate_private_key, derive_public_key

# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)

_DB_DIR = "/var/lib/phantom/db/tests"
_STATE_DIR = "/var/lib/phantom/state/db/tests"


# ── Session fixtures ─────────────────────────────────────────────

_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
_tag = hashlib.md5(f"wg-{_ts}".encode()).hexdigest()[:5]
_counter = 0


def _ifname() -> str:
    """Generate a unique interface name per test (IFNAMSIZ=16 safe)."""
    global _counter
    _counter += 1
    return f"wg_u_{_tag}{_counter:x}"


@pytest.fixture(scope="session")
def session_state_dir():
    """Timestamp-isolated state directory for this test session."""
    d = Path(_STATE_DIR) / f"wg-{_ts}"
    d.mkdir(parents=True, exist_ok=True)
    print(f"\n  WG State Dir: {d}")
    yield str(d)
    print(f"\n  State preserved: {d}")


@pytest.fixture(scope="session")
def server_keys():
    """Real Curve25519 server keys via Go bridge."""
    priv = generate_private_key()
    pub = derive_public_key(priv)
    return ServerKeys(private_key_hex=priv, public_key_hex=pub)


@pytest.fixture(scope="session")
def env(session_state_dir):
    """Real DaemonEnv with test paths (port 51821 to avoid API fixture conflict)."""
    return DaemonEnv(
        db_dir=_DB_DIR,
        state_dir=session_state_dir,
        listen_port=51822,
        mtu=1420,
        keepalive=25,
        endpoint_v4="",
        endpoint_v6="",
    )


@pytest.fixture(scope="session")
def wallet():
    """Real wallet database, timestamp-isolated."""
    os.makedirs(_DB_DIR, exist_ok=True)
    db_name = f"wg-{_ts}.db"
    db_path = os.path.join(_DB_DIR, db_name)
    print(f"\n  WG Wallet DB: {db_path}")
    w = open_wallet(db_dir=_DB_DIR, db_name=db_name)
    yield w
    print(f"\n  DB preserved: {db_path}")
    w.close()


# ── Helper ───────────────────────────────────────────────────────


def _sub(session_state_dir: str, name: str) -> str:
    """Create and return an isolated sub-directory under session state dir."""
    sub = Path(session_state_dir) / name
    sub.mkdir(parents=True, exist_ok=True)
    return str(sub)


# ── TestEnsureDeviceDb ───────────────────────────────────────────


class TestEnsureDeviceDb:
    def test_creates_db(self, session_state_dir):
        db_path = _ensure_device_db(_sub(session_state_dir, "ensure-create"))
        assert db_path.exists()
        assert db_path.name == "device.db"

    def test_idempotent(self, session_state_dir):
        d = _sub(session_state_dir, "ensure-idem")
        p1 = _ensure_device_db(d)
        p2 = _ensure_device_db(d)
        assert p1 == p2

    def test_schema_applied(self, session_state_dir):
        db_path = _ensure_device_db(_sub(session_state_dir, "ensure-schema"))
        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = {t[0] for t in tables}
        assert "ipc_state" in table_names

    def test_missing_dir_raises(self):
        with pytest.raises(WireGuardError, match="State directory"):
            _ensure_device_db("/nonexistent/path/to/nowhere")


# ── TestOpenWireguard ────────────────────────────────────────────


class TestOpenWireguard:
    def test_missing_state_dir(self):
        with pytest.raises(WireGuardError, match="State directory"):
            open_wireguard(state_dir="/nonexistent", mtu=1420)

    def test_creates_service(self, session_state_dir):
        d = _sub(session_state_dir, "open-svc")
        svc = open_wireguard(state_dir=d, mtu=1420, ifname=_ifname())
        assert isinstance(svc, WireGuardService)
        svc.close()

    def test_device_db_created(self, session_state_dir):
        d = _sub(session_state_dir, "open-db")
        ifn = _ifname()
        svc = open_wireguard(state_dir=d, mtu=1420, ifname=ifn)
        assert (Path(d) / "wireguard" / ifn / "device.db").exists()
        svc.close()


# ── TestLifecycle ────────────────────────────────────────────────


class TestLifecycle:
    def test_up_down(self, session_state_dir):
        d = _sub(session_state_dir, "lifecycle")
        svc = open_wireguard(state_dir=d, mtu=1420, ifname=_ifname())
        svc.up()
        svc.down()
        svc.close()

    def test_context_manager(self, session_state_dir):
        d = _sub(session_state_dir, "ctx-mgr")
        with open_wireguard(state_dir=d, mtu=1420, ifname=_ifname()) as svc:
            svc.up()
            svc.down()


# ── TestFastSync ─────────────────────────────────────────────────


class TestFastSync:
    def test_empty_wallet_sync(self, session_state_dir, wallet, server_keys, env):
        """Empty wallet → IPC gets server config only, zero peers."""
        d = _sub(session_state_dir, "sync-empty")
        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            w_count, i_count = svc.fast_sync(wallet, server_keys, env)
            assert w_count == 0
            assert i_count == 0

    def test_wallet_with_clients_sync(self, session_state_dir, wallet, server_keys, env):
        """Assign clients → fast_sync → IPC has those peers."""
        d = _sub(session_state_dir, "sync-clients")

        c1 = wallet.assign_client("wg_sync_alpha")
        c2 = wallet.assign_client("wg_sync_beta")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            w_count, i_count = svc.fast_sync(wallet, server_keys, env)
            assert w_count >= 2
            assert i_count == 0

            ipc_out = svc._bridge.ipc_get()
            ipc_peers = parse_ipc_peers(ipc_out)
            assert c1["public_key_hex"] in ipc_peers
            assert c2["public_key_hex"] in ipc_peers

    def test_double_sync_idempotent(self, session_state_dir, wallet, server_keys, env):
        """Two consecutive fast_sync calls produce the same IPC state."""
        d = _sub(session_state_dir, "sync-double")
        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            w1, _ = svc.fast_sync(wallet, server_keys, env)
            w2, i2 = svc.fast_sync(wallet, server_keys, env)
            assert w1 == w2
            assert i2 == w1

    def test_revoke_removes_from_ipc(self, session_state_dir, wallet, server_keys, env):
        """Revoke a client → fast_sync → peer disappears from IPC."""
        d = _sub(session_state_dir, "sync-revoke")

        c3 = wallet.assign_client("wg_sync_gamma")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)
            ipc_before = parse_ipc_peers(svc._bridge.ipc_get())
            assert c3["public_key_hex"] in ipc_before

            wallet.revoke_client("wg_sync_gamma")
            svc.fast_sync(wallet, server_keys, env)

            ipc_after = parse_ipc_peers(svc._bridge.ipc_get())
            assert c3["public_key_hex"] not in ipc_after


# ── TestAddPeer ─────────────────────────────────────────────────


class TestAddPeer:
    def test_add_single_peer(self, session_state_dir, wallet, server_keys, env):
        """add_peer → peer appears in IPC."""
        d = _sub(session_state_dir, "add-single")
        _c = wallet.assign_client("wg_add_alpha")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)
            peers_before = parse_ipc_peers(svc._bridge.ipc_get())

            c_new = wallet.assign_client("wg_add_beta")
            svc.add_peer(c_new, env.keepalive)

            peers_after = parse_ipc_peers(svc._bridge.ipc_get())
            assert c_new["public_key_hex"] in peers_after
            assert len(peers_after) == len(peers_before) + 1

    def test_add_preserves_existing(self, session_state_dir, wallet, server_keys, env):
        """add_peer does not disturb existing peers."""
        d = _sub(session_state_dir, "add-preserve")
        c1 = wallet.assign_client("wg_add_gamma")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)

            c2 = wallet.assign_client("wg_add_delta")
            svc.add_peer(c2, env.keepalive)

            peers = parse_ipc_peers(svc._bridge.ipc_get())
            assert c1["public_key_hex"] in peers
            assert c2["public_key_hex"] in peers


# ── TestRemovePeer ──────────────────────────────────────────────


class TestRemovePeer:
    def test_remove_single_peer(self, session_state_dir, wallet, server_keys, env):
        """remove_peer → peer disappears from IPC."""
        d = _sub(session_state_dir, "rm-single")
        c = wallet.assign_client("wg_rm_alpha")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)
            assert c["public_key_hex"] in parse_ipc_peers(svc._bridge.ipc_get())

            svc.remove_peer(c["public_key_hex"])
            assert c["public_key_hex"] not in parse_ipc_peers(svc._bridge.ipc_get())

    def test_remove_preserves_others(self, session_state_dir, wallet, server_keys, env):
        """remove_peer only removes the target, others stay."""
        d = _sub(session_state_dir, "rm-preserve")
        c1 = wallet.assign_client("wg_rm_beta")
        c2 = wallet.assign_client("wg_rm_gamma")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)

            svc.remove_peer(c1["public_key_hex"])
            peers = parse_ipc_peers(svc._bridge.ipc_get())
            assert c1["public_key_hex"] not in peers
            assert c2["public_key_hex"] in peers

    def test_add_then_remove(self, session_state_dir, wallet, server_keys, env):
        """Runtime add → remove cycle without fast_sync."""
        d = _sub(session_state_dir, "add-rm-cycle")

        with open_wireguard(state_dir=d, mtu=env.mtu, ifname=_ifname()) as svc:
            svc.fast_sync(wallet, server_keys, env)
            peers_baseline = parse_ipc_peers(svc._bridge.ipc_get())

            c = wallet.assign_client("wg_rm_delta")
            svc.add_peer(c, env.keepalive)
            assert c["public_key_hex"] in parse_ipc_peers(svc._bridge.ipc_get())

            svc.remove_peer(c["public_key_hex"])
            peers_final = parse_ipc_peers(svc._bridge.ipc_get())
            assert c["public_key_hex"] not in peers_final
            assert len(peers_final) == len(peers_baseline)
