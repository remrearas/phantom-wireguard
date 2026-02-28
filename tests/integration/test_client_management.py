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

Client management integration tests.

Test steps:
  1. Add client → auto IP allocation, unique keys
  2. Query client → get, list, pagination
  3. Remove client → IP freed and reused
  4. Toggle client → disable/enable preserves record
  5. Export config → valid WireGuard config with base64 keys
"""

import pytest

from wireguard_go_bridge.types import WireGuardError


@pytest.mark.docker
class TestClientAdd:

    def test_auto_ip_allocation(self, new_bridge):
        client = new_bridge.add_client()
        assert client.id > 0
        assert client.allowed_ip.startswith("10.100.0.")
        assert client.allowed_ip.endswith("/32")
        assert len(client.public_key) == 64
        assert len(client.private_key) == 64
        assert len(client.preshared_key) == 64
        assert client.enabled is True

    def test_unique_keys(self, new_bridge):
        c1 = new_bridge.add_client()
        c2 = new_bridge.add_client()
        assert c1.public_key != c2.public_key
        assert c1.private_key != c2.private_key
        assert c1.allowed_ip != c2.allowed_ip

    def test_sequential_ips(self, new_bridge):
        c1 = new_bridge.add_client()
        c2 = new_bridge.add_client()
        ip1 = int(c1.allowed_ip.split(".")[3].split("/")[0])
        ip2 = int(c2.allowed_ip.split(".")[3].split("/")[0])
        assert ip1 == 2
        assert ip2 == 3


@pytest.mark.docker
class TestClientQuery:

    def test_get_client(self, new_bridge):
        client = new_bridge.add_client()
        fetched = new_bridge.get_client(client.public_key)
        assert fetched.public_key == client.public_key
        assert fetched.allowed_ip == client.allowed_ip

    def test_list(self, new_bridge):
        new_bridge.add_client()
        new_bridge.add_client()
        new_bridge.add_client()
        cl = new_bridge.list_clients(page=1, limit=100)
        assert cl.total == 3

    def test_pagination(self, new_bridge):
        for _ in range(7):
            new_bridge.add_client()

        p1 = new_bridge.list_clients(page=1, limit=3)
        assert len(p1.clients) == 3
        assert p1.total == 7

        p3 = new_bridge.list_clients(page=3, limit=3)
        assert len(p3.clients) == 1


@pytest.mark.docker
class TestClientRemove:

    def test_remove(self, new_bridge):
        client = new_bridge.add_client()
        new_bridge.remove_client(client.public_key)
        assert new_bridge.list_clients().total == 0

    def test_remove_frees_ip(self, new_bridge):
        _c1 = new_bridge.add_client()
        c2 = new_bridge.add_client()
        _c3 = new_bridge.add_client()
        freed_ip = c2.allowed_ip

        new_bridge.remove_client(c2.public_key)
        c4 = new_bridge.add_client()
        assert c4.allowed_ip == freed_ip

    def test_remove_nonexistent(self, new_bridge):
        with pytest.raises(WireGuardError):
            new_bridge.remove_client("0" * 64)


@pytest.mark.docker
class TestClientToggle:

    def test_disable_and_enable(self, new_bridge):
        client = new_bridge.add_client()

        new_bridge.disable_client(client.public_key)
        c = new_bridge.get_client(client.public_key)
        assert c.enabled is False

        new_bridge.enable_client(client.public_key)
        c = new_bridge.get_client(client.public_key)
        assert c.enabled is True

    def test_disabled_stays_in_list(self, new_bridge):
        client = new_bridge.add_client()
        new_bridge.disable_client(client.public_key)
        assert new_bridge.list_clients().total == 1


@pytest.mark.docker
class TestConfigExport:

    def test_valid_config(self, new_bridge):
        client = new_bridge.add_client()
        config = new_bridge.export_client_config(client.public_key)

        assert "[Interface]" in config
        assert "[Peer]" in config
        assert "PrivateKey = " in config
        assert "DNS = " in config
        assert "MTU = " in config
        assert "PublicKey = " in config
        assert "PresharedKey = " in config
        assert "AllowedIPs = " in config
        assert "PersistentKeepalive = 25" in config

    def test_keys_are_base64(self, new_bridge):
        client = new_bridge.add_client()
        config = new_bridge.export_client_config(client.public_key)

        for line in config.strip().split("\n"):
            if line.startswith("PrivateKey = "):
                assert len(line.split(" = ")[1]) == 44
            if line.startswith("PublicKey = "):
                assert len(line.split(" = ")[1]) == 44

    def test_dns_update_affects_export(self, new_bridge):
        client = new_bridge.add_client()
        config1 = new_bridge.export_client_config(client.public_key)
        assert "1.1.1.1" in config1

        cfg = new_bridge.get_server_config()
        cfg.dns_primary = "9.9.9.9"
        new_bridge.set_server_config(cfg)

        config2 = new_bridge.export_client_config(client.public_key)
        assert "9.9.9.9" in config2
