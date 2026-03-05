"""Tests for phantom_daemon.base.services.firewall — real bridge, real wallet, no mocks."""

from __future__ import annotations

from pathlib import Path

import pytest

from phantom_daemon.base.errors import FirewallError
from phantom_daemon.base.services.firewall.service import (
    CORE_PRESET_NAME,
    FirewallService,
    _read_core_preset,
    _resolve_core_preset,
    open_firewall,
)


# ── TestResolvePreset (pure — no FFI) ────────────────────────────


class TestResolvePreset:
    def test_read_core_preset(self):
        """core.yaml is loadable and has expected structure."""
        spec = _read_core_preset()
        assert spec["name"] == CORE_PRESET_NAME
        assert spec["priority"] == 50
        assert len(spec["rules"]) == 5

    def test_resolve_injects_listen_port(self, test_env):
        """rules[0] (input/udp) gets listen_port from env."""
        spec = _resolve_core_preset(test_env.env, test_env.wallet)
        assert spec["rules"][0]["dport"] == test_env.env.listen_port

    def test_resolve_injects_interface(self, test_env):
        """rules[2]/[3] (forward) get WG_INTERFACE_NAME."""
        from phantom_daemon.base.services.wireguard import WG_INTERFACE_NAME

        spec = _resolve_core_preset(test_env.env, test_env.wallet)
        assert spec["rules"][2]["in_iface"] == WG_INTERFACE_NAME
        assert spec["rules"][3]["out_iface"] == WG_INTERFACE_NAME


# ── TestOpenFirewall ─────────────────────────────────────────────


class TestOpenFirewall:
    def test_missing_state_dir(self):
        with pytest.raises(FirewallError, match="State directory"):
            open_firewall(state_dir="/nonexistent/path/to/nowhere")

    def test_creates_service(self, test_env):
        d = test_env.sub("open-svc")
        svc = open_firewall(state_dir=d)
        assert isinstance(svc, FirewallService)
        svc.close()

    def test_db_created(self, test_env):
        d = test_env.sub("open-db")
        svc = open_firewall(state_dir=d)
        assert (Path(d) / "firewall.db").exists()
        svc.close()


# ── TestBootstrap ────────────────────────────────────────────────


class TestBootstrap:
    def test_creates_core_group(self, test_env):
        d = test_env.sub("boot-core")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            groups = svc.list_groups()
            names = [g.name for g in groups]
            assert CORE_PRESET_NAME in names

    def test_core_group_type(self, test_env):
        d = test_env.sub("boot-type")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.group_type == "system"

    def test_core_has_five_rules(self, test_env):
        d = test_env.sub("boot-rules")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            assert len(rules) == 5

    def test_listen_port_injected(self, test_env):
        d = test_env.sub("boot-port")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            udp_rules = [r for r in rules if r.proto == "udp"]
            assert len(udp_rules) == 1
            assert udp_rules[0].dport == test_env.env.listen_port

    def test_interface_injected(self, test_env):
        from phantom_daemon.base.services.wireguard import WG_INTERFACE_NAME

        d = test_env.sub("boot-iface")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            fwd_in = [r for r in rules if r.in_iface == WG_INTERFACE_NAME]
            assert len(fwd_in) == 1


# ── TestLifecycle ────────────────────────────────────────────────


class TestLifecycle:
    def test_start_stop(self, test_env):
        d = test_env.sub("lifecycle")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            svc.start()
            assert svc.get_state() == "started"
            svc.stop()
            assert svc.get_state() == "stopped"

    def test_context_manager(self, test_env):
        d = test_env.sub("ctx-mgr")
        with open_firewall(state_dir=d) as svc:
            assert isinstance(svc, FirewallService)
        # close called implicitly — no error

    def test_recover_from_db(self, test_env):
        """Second open on same DB recovers groups without bootstrap."""
        d = test_env.sub("recover")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)

        with open_firewall(state_dir=d) as svc2:
            groups = svc2.list_groups()
            assert len(groups) >= 1
            assert any(g.name == CORE_PRESET_NAME for g in groups)


# ── TestPresetOperations ─────────────────────────────────────────


class TestPresetOperations:
    def test_apply_custom_preset(self, test_env):
        d = test_env.sub("preset-apply")
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

    def test_remove_preset(self, test_env):
        d = test_env.sub("preset-rm")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            svc.remove_preset(CORE_PRESET_NAME)
            names = [g.name for g in svc.list_groups()]
            assert CORE_PRESET_NAME not in names

    def test_disable_enable_preset(self, test_env):
        d = test_env.sub("preset-toggle")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            svc.disable_preset(CORE_PRESET_NAME)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.enabled is False

            svc.enable_preset(CORE_PRESET_NAME)
            group = svc.get_group(CORE_PRESET_NAME)
            assert group.enabled is True

    def test_apply_preserves_existing(self, test_env):
        d = test_env.sub("preset-preserve")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
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
    def test_list_firewall_rules(self, test_env):
        d = test_env.sub("read-fw-rules")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            rules = svc.list_firewall_rules()
            assert len(rules) == 5
            chains = {r.chain for r in rules}
            assert "input" in chains
            assert "postrouting" in chains

    def test_list_firewall_rules_filtered(self, test_env):
        d = test_env.sub("read-fw-filtered")
        with open_firewall(state_dir=d) as svc:
            svc.bootstrap(env=test_env.env, wallet=test_env.wallet)
            rules = svc.list_firewall_rules(CORE_PRESET_NAME)
            assert len(rules) == 5
