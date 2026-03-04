"""Tests for phantom_daemon.base.services.firewall — real bridge, real wallet, no mocks."""

from __future__ import annotations

import functools
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from phantom_daemon.base.env import DaemonEnv
from phantom_daemon.base.errors import FirewallError
from phantom_daemon.base.services.firewall.service import (
    CORE_PRESET_NAME,
    FirewallService,
    _read_core_preset,
    _resolve_core_preset,
    open_firewall,
)
from phantom_daemon.base.wallet import open_wallet

# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)

_DB_DIR = "/var/lib/phantom/db/tests"
_STATE_DIR = "/var/lib/phantom/state/db/tests"


# ── Session fixtures ─────────────────────────────────────────────

_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


@pytest.fixture(scope="session")
def session_state_dir():
    """Timestamp-isolated state directory for this test session."""
    d = Path(_STATE_DIR) / f"fw-{_ts}"
    d.mkdir(parents=True, exist_ok=True)
    print(f"\n  FW State Dir: {d}")
    yield str(d)
    print(f"\n  State preserved: {d}")


@pytest.fixture(scope="session")
def env(session_state_dir):
    """Real DaemonEnv with test paths."""
    return DaemonEnv(
        db_dir=_DB_DIR,
        state_dir=session_state_dir,
        listen_port=51820,
        mtu=1420,
        keepalive=25,
        endpoint_v4="",
        endpoint_v6="",
    )


@pytest.fixture(scope="session")
def wallet():
    """Real wallet database, timestamp-isolated."""
    os.makedirs(_DB_DIR, exist_ok=True)
    db_name = f"fw-{_ts}.db"
    db_path = os.path.join(_DB_DIR, db_name)
    print(f"\n  FW Wallet DB: {db_path}")
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


# ── TestResolvePreset (pure — no FFI) ────────────────────────────


class TestResolvePreset:
    def test_read_core_preset(self):
        """core.yaml is loadable and has expected structure."""
        spec = _read_core_preset()
        assert spec["name"] == CORE_PRESET_NAME
        assert spec["priority"] == 50
        assert len(spec["rules"]) == 5

    def test_resolve_injects_listen_port(self, env, wallet):
        """rules[0] (input/udp) gets listen_port from env."""
        spec = _resolve_core_preset(env, wallet)
        assert spec["rules"][0]["dport"] == env.listen_port

    def test_resolve_injects_interface(self, env, wallet):
        """rules[2]/[3] (forward) get WG_INTERFACE_NAME."""
        from phantom_daemon.base.services.wireguard import WG_INTERFACE_NAME

        spec = _resolve_core_preset(env, wallet)
        assert spec["rules"][2]["in_iface"] == WG_INTERFACE_NAME
        assert spec["rules"][3]["out_iface"] == WG_INTERFACE_NAME


# ── TestOpenFirewall ─────────────────────────────────────────────


class TestOpenFirewall:
    def test_missing_state_dir(self):
        with pytest.raises(FirewallError, match="State directory"):
            open_firewall(state_dir="/nonexistent/path/to/nowhere")

    def test_creates_service(self, session_state_dir):
        d = _sub(session_state_dir, "open-svc")
        svc = open_firewall(state_dir=d)
        assert isinstance(svc, FirewallService)
        svc.close()

    def test_db_created(self, session_state_dir):
        d = _sub(session_state_dir, "open-db")
        svc = open_firewall(state_dir=d)
        assert (Path(d) / "firewall.db").exists()
        svc.close()


# ── TestBootstrap ────────────────────────────────────────────────


class TestBootstrap:
    def test_creates_core_group(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "boot-core")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            groups = svc.list_groups()
            names = [g.name for g in groups]
            assert CORE_PRESET_NAME in names

    def test_core_group_type(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "boot-type")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.group_type == "system"

    def test_core_has_five_rules(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "boot-rules")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            assert len(rules) == 5

    def test_listen_port_injected(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "boot-port")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            udp_rules = [r for r in rules if r.proto == "udp"]
            assert len(udp_rules) == 1
            assert udp_rules[0].dport == env.listen_port

    def test_interface_injected(self, session_state_dir, env, wallet):
        from phantom_daemon.base.services.wireguard import WG_INTERFACE_NAME

        d = _sub(session_state_dir, "boot-iface")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            fwd_in = [r for r in rules if r.in_iface == WG_INTERFACE_NAME]
            assert len(fwd_in) == 1


# ── TestLifecycle ────────────────────────────────────────────────


class TestLifecycle:
    def test_start_stop(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "lifecycle")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            svc.start()
            assert svc.get_state() == "started"
            svc.stop()
            assert svc.get_state() == "stopped"

    def test_context_manager(self, session_state_dir):
        d = _sub(session_state_dir, "ctx-mgr")
        with open_firewall(state_dir=d) as svc:
            assert isinstance(svc, FirewallService)
        # close called implicitly — no error

    def test_recover_from_db(self, session_state_dir, env, wallet):
        """Second open on same DB recovers groups without bootstrap."""
        d = _sub(session_state_dir, "recover")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)

        with open_firewall(state_dir=d) as svc2:
            groups = svc2.list_groups()
            assert len(groups) >= 1
            assert any(g.name == CORE_PRESET_NAME for g in groups)


# ── TestPresetOperations ─────────────────────────────────────────


class TestPresetOperations:
    def test_apply_custom_preset(self, session_state_dir):
        d = _sub(session_state_dir, "preset-apply")
        spec = {
            "name": "test-custom",
            "priority": 90,
            "type": "custom",
            "metadata": {"description": "test"},
            "rules": [
                {
                    "chain": "input",
                    "action": "drop",
                    "proto": "tcp",
                    "dport": 9999,
                },
            ],
        }
        with open_firewall(state_dir=d) as svc:
            group = svc.apply_preset(spec)
            assert group.name == "test-custom"

    def test_remove_preset(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "preset-rm")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            svc.remove_preset(CORE_PRESET_NAME)
            names = [g.name for g in svc.list_groups()]
            assert CORE_PRESET_NAME not in names

    def test_disable_enable_preset(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "preset-toggle")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            svc.disable_preset(CORE_PRESET_NAME)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.enabled is False

            svc.enable_preset(CORE_PRESET_NAME)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.enabled is True

    def test_apply_preserves_existing(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "preset-preserve")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            extra = {
                "name": "extra",
                "priority": 90,
                "type": "custom",
                "metadata": {"description": "extra"},
                "rules": [
                    {
                        "chain": "input",
                        "action": "drop",
                        "proto": "tcp",
                        "dport": 8888,
                    },
                ],
            }
            svc.apply_preset(extra)
            names = [g.name for g in svc.list_groups()]
            assert CORE_PRESET_NAME in names
            assert "extra" in names


# ── TestReadOperations ───────────────────────────────────────────


class TestReadOperations:
    def test_list_firewall_rules(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "read-fw-rules")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            rules = svc.list_firewall_rules()
            assert len(rules) == 5
            chains = {r.chain for r in rules}
            assert "input" in chains
            assert "postrouting" in chains

    def test_list_firewall_rules_filtered(self, session_state_dir, env, wallet):
        d = _sub(session_state_dir, "read-fw-filtered")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=env, wallet=wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            assert len(rules) == 5
