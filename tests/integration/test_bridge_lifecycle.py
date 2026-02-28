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

Bridge lifecycle integration tests.

Test steps:
  1. Init fresh DB → status needs_setup
  2. Setup server config → status ready
  3. Start device → status running
  4. Stop/restart → ready ↔ running
  5. Crash recovery → reopen DB preserves state
"""

import os
import tempfile
import uuid

import pytest

from wireguard_go_bridge import get_bridge_version, get_wireguard_go_version
from wireguard_go_bridge.client import BridgeClient


@pytest.mark.docker
class TestLibrary:

    def test_version(self):
        assert get_bridge_version() == "2.0.0"

    def test_wireguard_go_version(self):
        assert get_wireguard_go_version() != "unknown"


@pytest.mark.docker
class TestInitAndSetup:

    def test_fresh_db_needs_setup(self, new_bridge_factory):
        bridge, db_path = new_bridge_factory()
        status = bridge.get_status()
        assert status["status"] == "needs_setup"
        assert status["has_device"] is True
        assert status["has_config"] is False
        assert os.path.exists(db_path)

    def test_setup_transitions_to_ready(self, new_bridge_factory):
        bridge, _ = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:51820", network="10.50.0.0/24")
        status = bridge.get_status()
        assert status["status"] == "ready"
        assert status["has_config"] is True

    def test_start_transitions_to_running(self, new_bridge_factory):
        bridge, _ = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:51821")
        bridge.start()
        status = bridge.get_status()
        assert status["status"] == "running"

        info = bridge.get_device_info()
        assert len(info.public_key) == 64
        bridge.stop()

    def test_stop_and_restart(self, new_bridge_factory):
        bridge, _ = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:51822")
        bridge.start()
        assert bridge.get_status()["status"] == "running"

        bridge.stop()
        assert bridge.get_status()["status"] == "ready"

        bridge.start()
        assert bridge.get_status()["status"] == "running"
        bridge.stop()


@pytest.mark.docker
class TestCrashRecovery:

    def test_reopen_existing_db(self):
        uid = uuid.uuid4().hex[:8]
        db_path = os.path.join(tempfile.gettempdir(), f"crash_{uid}.db")
        ifname = f"wg-cr-{uid[:4]}"

        # First run
        bridge = BridgeClient(db_path, ifname, 51830)
        bridge.setup(endpoint="10.0.0.1:51830", network="10.51.0.0/24")
        bridge.start()
        client = bridge.add_client()
        pub_key = client.public_key
        bridge.close()

        # Second run — same DB, different interface name (TUN cleanup safe)
        bridge2 = BridgeClient(db_path, f"wg-cr2-{uid[:4]}", 51830)
        try:
            status = bridge2.get_status()
            assert status["status"] == "ready"
            assert status["peer_count"] == 1

            bridge2.start()
            recovered = bridge2.get_client(pub_key)
            assert recovered.public_key == pub_key
            bridge2.stop()
        finally:
            bridge2.close()
            os.remove(db_path)


@pytest.mark.docker
class TestServerConfig:

    def test_config_persists(self):
        uid = uuid.uuid4().hex[:8]
        db_path = os.path.join(tempfile.gettempdir(), f"cfg_{uid}.db")

        bridge = BridgeClient(db_path, f"wg-cp-{uid[:4]}", 51835)
        bridge.setup(endpoint="vpn.example.com:51835", network="10.52.0.0/24",
                     dns_primary="8.8.8.8", mtu=1400)
        cfg = bridge.get_server_config()
        assert cfg.endpoint == "vpn.example.com:51835"
        assert cfg.mtu == 1400
        bridge.close()

        bridge2 = BridgeClient(db_path, f"wg-cp2-{uid[:4]}", 51835)
        try:
            cfg2 = bridge2.get_server_config()
            assert cfg2.endpoint == "vpn.example.com:51835"
            assert cfg2.mtu == 1400
        finally:
            bridge2.close()
            os.remove(db_path)

    def test_update_dns(self, new_bridge_factory):
        bridge, _ = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:51836", dns_primary="1.1.1.1")

        cfg = bridge.get_server_config()
        cfg.dns_primary = "9.9.9.9"
        bridge.set_server_config(cfg)

        updated = bridge.get_server_config()
        assert updated.dns_primary == "9.9.9.9"
